"""Shift patterns: the repeating shifts and how many people of each role they need.

Example: "Weekday morning", 07:00-15:00, Mon-Fri, needs 1 Cashier + 2 Servers + 2 Chefs.
The roster generator fills these; the roster board shows filled vs required.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import activity
from app.core.errors import BadRequest, NotFound
from app.core.timeutil import fmt_hhmm, parse_hhmm
from app.modules.people.models import Role
from app.modules.scheduling import schemas
from app.modules.scheduling.models import PatternRequirement, ShiftPattern
from app.modules.scheduling.rules import get_settings, validate_days


def _hours(p: ShiftPattern) -> float:
    return round((p.end_time.hour * 60 + p.end_time.minute - p.start_time.hour * 60 - p.start_time.minute) / 60, 2)


def pattern_out(p: ShiftPattern) -> schemas.ShiftPattern:
    reqs = sorted(p.requirements, key=lambda r: r.role.name)
    return schemas.ShiftPattern(
        id=p.id,
        name=p.name,
        start_time=fmt_hhmm(p.start_time),
        end_time=fmt_hhmm(p.end_time),
        hours=_hours(p),
        days=sorted(p.days),
        active=p.active,
        requirements=[
            schemas.PatternRequirement(role_id=r.role_id, role_name=r.role.name, headcount=r.headcount)
            for r in reqs
        ],
    )


def list_patterns(db: Session) -> list[schemas.ShiftPattern]:
    rows = db.scalars(select(ShiftPattern).order_by(ShiftPattern.start_time, ShiftPattern.name))
    return [pattern_out(p) for p in rows]


def _apply(db: Session, p: ShiftPattern, data: schemas.ShiftPatternInput) -> None:
    s = get_settings(db)
    if not data.name.strip():
        raise BadRequest("Pattern name is required.")
    try:
        start, end = parse_hhmm(data.start_time), parse_hhmm(data.end_time)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    if start >= end:
        raise BadRequest("Shift start must be before its end (shifts can't run past midnight).")
    if start < s.open_time or end > s.close_time:
        raise BadRequest(f"Shift must fit within opening hours ({fmt_hhmm(s.open_time)}–{fmt_hhmm(s.close_time)}).")
    hours = (end.hour * 60 + end.minute - start.hour * 60 - start.minute) / 60
    if hours > s.max_hours_per_day:
        raise BadRequest(f"This shift is {hours:g}h, longer than the daily limit of {s.max_hours_per_day:g}h, "
                         "so nobody could be rostered on it.")
    seen: set[int] = set()
    for r in data.requirements:
        if r.role_id in seen:
            raise BadRequest("Each role can only appear once in a pattern.")
        seen.add(r.role_id)
        if db.get(Role, r.role_id) is None:
            raise BadRequest(f"Unknown role id {r.role_id}.")
        if not 0 <= r.headcount <= 50:
            raise BadRequest("Headcount must be between 0 and 50.")

    p.name = data.name.strip()
    p.start_time, p.end_time = start, end
    p.days = validate_days(data.days, "this pattern")
    p.active = data.active
    p.requirements.clear()
    db.flush()
    for r in data.requirements:
        if r.headcount > 0:
            p.requirements.append(PatternRequirement(role_id=r.role_id, headcount=r.headcount))


def create_pattern(db: Session, data: schemas.ShiftPatternInput) -> schemas.ShiftPattern:
    p = ShiftPattern()
    db.add(p)
    _apply(db, p, data)
    activity.log(db, "pattern_added", f"Added shift pattern {p.name}")
    db.commit()
    db.refresh(p)
    return pattern_out(p)


def update_pattern(db: Session, pattern_id: int, data: schemas.ShiftPatternInput) -> schemas.ShiftPattern:
    p = db.get(ShiftPattern, pattern_id)
    if p is None:
        raise NotFound("Shift pattern not found.")
    _apply(db, p, data)
    db.commit()
    db.refresh(p)
    return pattern_out(p)


def delete_pattern(db: Session, pattern_id: int) -> None:
    p = db.get(ShiftPattern, pattern_id)
    if p is None:
        raise NotFound("Shift pattern not found.")
    db.delete(p)  # existing shifts keep their times; they just lose the link (shown under "Other shifts")
    activity.log(db, "pattern_removed", f"Removed shift pattern {p.name}")
    db.commit()
