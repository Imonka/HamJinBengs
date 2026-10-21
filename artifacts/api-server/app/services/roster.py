"""The weekly roster: the board view (required vs assigned) and automatic generation."""

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .. import schemas
from ..models import CoverageCase, Employee, Shift, ShiftPattern
from ..scheduling import PatternDemand, generate_week
from ..timeutil import date_range, fmt_hhmm, hours_between, now_utc
from . import activity
from .serializers import shift_out, case_ids_for_shifts
from .settings import get_rules


def _demands(db: Session) -> list[PatternDemand]:
    out = []
    for p in db.scalars(select(ShiftPattern).where(ShiftPattern.active.is_(True))):
        for r in p.requirements:
            out.append(PatternDemand(p.id, p.name, p.start_time, p.end_time, frozenset(p.days),
                                     r.role_id, r.role.name, r.headcount))
    return out


def _hours_table(db: Session, ws: date, we: date, weekly_default: float) -> list[schemas.RosterEmployeeHours]:
    shifts = db.scalars(select(Shift).where(Shift.status == "scheduled", Shift.date.between(ws, we),
                                            Shift.employee_id.is_not(None))).all()
    hours: dict[int, float] = defaultdict(float)
    days: dict[int, set[date]] = defaultdict(set)
    for s in shifts:
        hours[s.employee_id] += hours_between(s.starts_at, s.ends_at)
        days[s.employee_id].add(s.date)
    people = db.scalars(select(Employee).where(Employee.active.is_(True)).order_by(Employee.name)).all()
    return [
        schemas.RosterEmployeeHours(
            employee_id=e.id, name=e.name, role_name=e.role.name if e.role else None,
            hours=round(hours.get(e.id, 0), 2), days=len(days.get(e.id, ())),
            max_hours=e.max_hours_per_week if e.max_hours_per_week is not None else weekly_default,
        )
        for e in people
        if e.role_id is not None or e.id in hours
    ]


def week_view(db: Session, any_day: date) -> schemas.RosterWeek:
    rules = get_rules(db)
    ws, we = rules.week_of(any_day)
    shifts = db.scalars(
        select(Shift).where(Shift.date.between(ws, we), Shift.status.in_(["scheduled", "needs_cover"]))
        .order_by(Shift.starts_at, Shift.id)
    ).all()
    case_map = case_ids_for_shifts(db, [s.id for s in shifts])
    patterns = db.scalars(select(ShiftPattern).where(ShiftPattern.active.is_(True))
                          .order_by(ShiftPattern.start_time, ShiftPattern.name)).all()

    by_slot: dict[tuple[date, int, int], list[Shift]] = defaultdict(list)
    for s in shifts:
        if s.pattern_id is not None:
            by_slot[(s.date, s.pattern_id, s.role_id)].append(s)

    days, total_required, total_filled, total_gaps = [], 0, 0, 0
    for d in date_range(ws, we):
        is_open = d.weekday() in rules.operating_days
        slots, used = [], set()
        for p in patterns:
            if not is_open or d.weekday() not in p.days:
                continue
            for r in sorted(p.requirements, key=lambda r: r.role.name):
                assigned = by_slot.get((d, p.id, r.role_id), [])
                used.update(s.id for s in assigned)
                working = sum(1 for s in assigned if s.status == "scheduled")
                short = max(0, r.headcount - working)
                total_required += r.headcount
                total_filled += min(working, r.headcount)
                total_gaps += short
                slots.append(schemas.RosterSlot(
                    pattern_id=p.id, pattern_name=p.name, start_time=fmt_hhmm(p.start_time),
                    end_time=fmt_hhmm(p.end_time), role_id=r.role_id, role_name=r.role.name,
                    required=r.headcount, short_by=short,
                    assigned=[schemas.RosterAssignee(
                        shift_id=s.id, employee_id=s.employee_id,
                        employee_name=s.employee.name if s.employee else None, status=s.status,  # type: ignore[arg-type]
                    ) for s in assigned],
                ))
        others = [shift_out(s, rules.tz, case_map) for s in shifts if s.date == d and s.id not in used]
        days.append(schemas.RosterDay(date=d, weekday=d.weekday(), open=is_open, slots=slots, other_shifts=others))

    return schemas.RosterWeek(
        week_start=ws, week_end=we, days=days,
        employees=_hours_table(db, ws, we, rules.max_hours_per_week),
        required=total_required, filled=total_filled, gaps=total_gaps,
    )


def generate(db: Session, any_day: date, replace_existing: bool, *, include_past: bool = False,
             now: datetime | None = None) -> schemas.GenerateRosterResult:
    """Fill every empty place in the week's shift patterns.

    replace_existing=True first removes this week's *future*, *automatically generated* shifts
    (hand-made shifts, cover shifts and anything linked to a cover case are always kept),
    then builds them again with the current rules.
    """
    from .staffing import load_staff

    rules = get_rules(db)
    now = now or now_utc()
    ws, we = rules.week_of(any_day)

    removed = 0
    if replace_existing:
        in_cases = select(CoverageCase.shift_id).union(
            select(CoverageCase.replacement_shift_id).where(CoverageCase.replacement_shift_id.is_not(None)))
        q = delete(Shift).where(
            Shift.date.between(ws, we), Shift.source == "generated", Shift.status == "scheduled",
            Shift.id.notin_(in_cases),
        )
        if not include_past:
            q = q.where(Shift.starts_at > now)
        removed = db.execute(q).rowcount
        db.flush()

    filled: dict[tuple[date, int, int], int] = defaultdict(int)
    for s in db.scalars(select(Shift).where(Shift.date.between(ws, we), Shift.pattern_id.is_not(None),
                                            Shift.status.in_(["scheduled", "needs_cover"]))):
        filled[(s.date, s.pattern_id, s.role_id)] += 1

    staff = [p for p in load_staff(db, rules, ws, now=now) if p.role_id is not None]
    result = generate_week(rules, ws, _demands(db), staff, filled, now, include_past=include_past)

    for p in result.planned:
        db.add(Shift(employee_id=p.staff_id, role_id=p.role_id, pattern_id=p.pattern_id, date=p.day,
                     starts_at=p.start, ends_at=p.end, status="scheduled", source="generated"))
    missing = sum(g.missing for g in result.gaps)
    activity.log(db, "roster_generated",
                 f"Generated roster for week of {ws:%d %b}: {len(result.planned)} shift(s) added"
                 + (f", {removed} replaced" if removed else "")
                 + (f", {missing} place(s) still empty" if missing else ""))
    db.commit()

    return schemas.GenerateRosterResult(
        week_start=ws, created=len(result.planned), removed=removed,
        gaps=[schemas.RosterGap(date=g.day, pattern_name=g.pattern_name, role_name=g.role_name,
                                missing=g.missing, reason=g.reason) for g in result.gaps],
        employees=_hours_table(db, ws, we, rules.max_hours_per_week),
    )
