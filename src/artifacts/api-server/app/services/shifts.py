"""Shifts added or edited by hand by the manager.

Every change is checked against the same scheduling rules as the generator. If a rule is
broken the API answers 409 with the list of problems; the manager can resend with
`override: true` to save anyway (their call).
"""

from datetime import date, time

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..errors import BadRequest, Conflict, NotFound, RuleViolation
from ..models import CoverageCase, Employee, Role, Shift, ShiftPattern
from ..scheduling import MANUAL, CheckContext, ProposedShift, evaluate
from ..timeutil import at, fmt_window, local_today, now_utc, parse_hhmm
from . import activity
from .serializers import shift_out, shifts_out
from .settings import get_rules
from .staffing import load_staff


def list_shifts(db: Session, date_from: date | None, date_to: date | None, employee_id: int | None,
                role_id: int | None, status: str | None) -> list[schemas.Shift]:
    rules = get_rules(db)
    start = date_from or local_today(rules.tz)
    q = select(Shift).where(Shift.date >= start)
    if date_to:
        q = q.where(Shift.date <= date_to)
    if employee_id:
        q = q.where(Shift.employee_id == employee_id)
    if role_id:
        q = q.where(Shift.role_id == role_id)
    if status:
        q = q.where(Shift.status == status)
    rows = db.scalars(q.order_by(Shift.starts_at, Shift.id).limit(2000)).all()
    return shifts_out(db, list(rows), rules.tz)


def _matching_pattern(db: Session, day: date, start: time, end: time, role_id: int) -> int | None:
    """Link a hand-made shift to a pattern when it lines up exactly, so it counts on the roster board."""
    for p in db.scalars(select(ShiftPattern).where(ShiftPattern.active.is_(True))):
        if p.start_time == start and p.end_time == end and day.weekday() in p.days \
                and any(r.role_id == role_id for r in p.requirements):
            return p.id
    return None


def _prepare(db: Session, data: schemas.ShiftInput, ignore_shift_id: int | None):
    rules = get_rules(db)
    employee = db.get(Employee, data.employee_id)
    if employee is None:
        raise BadRequest("Employee not found.")
    role = db.get(Role, data.role_id)
    if role is None:
        raise BadRequest("Role not found.")
    try:
        start_t, end_t = parse_hhmm(data.start_time), parse_hhmm(data.end_time)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    if start_t >= end_t:
        raise BadRequest("Shift start must be before its end.")
    start, end = at(data.date, start_t, rules.tz), at(data.date, end_t, rules.tz)

    proposed = ProposedShift(data.date, start, end, role.id, role.name, ignore_shift_id=ignore_shift_id)
    staff = load_staff(db, rules, data.date, employee_ids=[employee.id], active_only=False)
    ev = evaluate(CheckContext(rules, staff[0], proposed, now_utc()), MANUAL)
    if not ev.ok and not data.override:
        raise RuleViolation(
            f"{employee.name} can't take this shift without breaking the rules.",
            [f.message for f in ev.hard],
        )
    return rules, employee, role, start, end, start_t, end_t, ev


def create_shift(db: Session, data: schemas.ShiftInput) -> schemas.Shift:
    rules, employee, role, start, end, start_t, end_t, ev = _prepare(db, data, None)
    s = Shift(
        employee_id=employee.id, role_id=role.id, date=data.date, starts_at=start, ends_at=end,
        pattern_id=_matching_pattern(db, data.date, start_t, end_t, role.id),
        status="scheduled", source="manual", notes=(data.notes or "").strip() or None,
    )
    db.add(s)
    msg = f"Added {employee.name} as {role.name}, {fmt_window(start, end, rules.tz)}"
    if not ev.ok:
        msg += " (rules overridden: " + "; ".join(f.message for f in ev.hard) + ")"
    activity.log(db, "shift_added", msg)
    db.commit()
    db.refresh(s)
    return shift_out(s, rules.tz)


def _editable(db: Session, shift_id: int) -> Shift:
    s = db.get(Shift, shift_id)
    if s is None:
        raise NotFound("Shift not found.")
    linked = db.scalar(select(CoverageCase.id).where(
        or_(CoverageCase.shift_id == s.id, CoverageCase.replacement_shift_id == s.id)).limit(1))
    if linked is not None:
        raise Conflict("This shift is part of a cover case. Manage it from the Cover page.")
    return s


def update_shift(db: Session, shift_id: int, data: schemas.ShiftInput) -> schemas.Shift:
    s = _editable(db, shift_id)
    rules, employee, role, start, end, start_t, end_t, ev = _prepare(db, data, s.id)
    s.employee_id, s.role_id, s.date, s.starts_at, s.ends_at = employee.id, role.id, data.date, start, end
    s.pattern_id = _matching_pattern(db, data.date, start_t, end_t, role.id)
    s.notes = (data.notes or "").strip() or None
    if s.source == "generated":
        s.source = "manual"  # so "regenerate" won't wipe the manager's edit
    activity.log(db, "shift_changed", f"Changed shift: {employee.name}, {fmt_window(start, end, rules.tz)}")
    db.commit()
    db.refresh(s)
    return shift_out(s, rules.tz)


def delete_shift(db: Session, shift_id: int) -> None:
    s = _editable(db, shift_id)
    rules = get_rules(db)
    who = s.employee.name if s.employee else "unassigned"
    activity.log(db, "shift_removed", f"Removed shift: {who}, {fmt_window(s.starts_at, s.ends_at, rules.tz)}")
    db.delete(s)
    db.commit()
