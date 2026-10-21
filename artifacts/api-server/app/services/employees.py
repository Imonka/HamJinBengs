"""Employees. `add_employee()` is the one function every route (form, CSV import, CLI, seed) uses
to create a person, so validation lives in one place."""

import re

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from .. import schemas
from ..errors import AppError, BadRequest, Conflict, NotFound
from ..models import CoverageCase, CoverOffer, Employee, LeaveRequest, Role, Shift
from ..timeutil import local_today, now_utc
from . import activity
from .auth import end_all_sessions, hash_pin
from .roles import find_role_by_name
from .serializers import shifts_out
from .settings import get_rules

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ------------------------------------------------------------------ reading
def _hours_this_week(db: Session, ids: list[int] | None = None) -> dict[int, float]:
    rules = get_rules(db)
    ws, we = rules.week_of(local_today(rules.tz))
    hours = func.sum(func.extract("epoch", Shift.ends_at - Shift.starts_at) / 3600)
    q = (
        select(Shift.employee_id, hours)
        .where(Shift.status == "scheduled", Shift.date.between(ws, we), Shift.employee_id.is_not(None))
        .group_by(Shift.employee_id)
    )
    if ids is not None:
        q = q.where(Shift.employee_id.in_(ids))
    return {eid: round(float(h or 0), 2) for eid, h in db.execute(q).all()}


def _on_leave_today(db: Session) -> set[int]:
    today = local_today(get_rules(db).tz)
    return set(
        db.scalars(
            select(LeaveRequest.employee_id).where(
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= today,
                LeaveRequest.end_date >= today,
            )
        )
    )


def employee_out(e: Employee, hours: float, on_leave: bool) -> schemas.Employee:
    return schemas.Employee(
        id=e.id, name=e.name, email=e.email, phone=e.phone, access=e.access,  # type: ignore[arg-type]
        role_id=e.role_id, role_name=e.role.name if e.role else None, active=e.active,
        max_hours_per_week=e.max_hours_per_week, orbyte_id=e.orbyte_id,
        on_leave_today=on_leave, hours_this_week=hours, created_at=e.created_at,
    )


def to_out(db: Session, e: Employee) -> schemas.Employee:
    return employee_out(e, _hours_this_week(db, [e.id]).get(e.id, 0), e.id in _on_leave_today(db))


def list_employees(db: Session, role_id: int | None, active: bool | None, search: str | None) -> list[schemas.Employee]:
    q = select(Employee)
    if role_id is not None:
        q = q.where(Employee.role_id == role_id)
    if active is not None:
        q = q.where(Employee.active.is_(active))
    if search:
        like = f"%{search.strip()}%"
        q = q.where(or_(Employee.name.ilike(like), Employee.email.ilike(like)))
    rows = db.scalars(q.order_by(Employee.name)).all()
    hours, leave = _hours_this_week(db), _on_leave_today(db)
    return [employee_out(e, hours.get(e.id, 0), e.id in leave) for e in rows]


def get_employee(db: Session, employee_id: int) -> Employee:
    e = db.get(Employee, employee_id)
    if e is None:
        raise NotFound("Employee not found.")
    return e


def employee_detail(db: Session, employee_id: int) -> schemas.EmployeeDetail:
    from .leave import to_out as leave_to_out

    e = get_employee(db, employee_id)
    rules = get_rules(db)
    shifts = db.scalars(
        select(Shift)
        .where(Shift.employee_id == e.id, Shift.date >= local_today(rules.tz), Shift.status != "cancelled")
        .order_by(Shift.starts_at)
        .limit(60)
    ).all()
    leave = db.scalars(
        select(LeaveRequest).where(LeaveRequest.employee_id == e.id).order_by(LeaveRequest.start_date.desc())
    ).all()
    return schemas.EmployeeDetail(
        employee=to_out(db, e),
        upcoming_shifts=shifts_out(db, list(shifts), rules.tz),
        leave=[leave_to_out(db, lv) for lv in leave],
    )


# ------------------------------------------------------------------ validation helpers
def _clean_email(db: Session, email: str, current_id: int | None = None) -> str:
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise BadRequest(f'"{email}" is not a valid email address.')
    other = db.scalar(select(Employee).where(Employee.email == email))
    if other is not None and other.id != current_id:
        raise Conflict(f"{email} is already used by {other.name}.")
    return email


def _clean_orbyte_id(db: Session, orbyte_id: str | None, current_id: int | None = None) -> str | None:
    orbyte_id = (orbyte_id or "").strip() or None
    if orbyte_id:
        other = db.scalar(select(Employee).where(Employee.orbyte_id == orbyte_id))
        if other is not None and other.id != current_id:
            raise Conflict(f"Orbyte ID {orbyte_id} is already used by {other.name}.")
    return orbyte_id


def _clean_limit(value: float | None) -> float | None:
    if value is not None and not 0 < value <= 168:
        raise BadRequest("Personal weekly limit must be between 0 and 168 hours.")
    return value


def _resolve_role(db: Session, role_id: int | None, role_name: str | None) -> int | None:
    if role_id is not None:
        if db.get(Role, role_id) is None:
            raise BadRequest(f"Unknown role id {role_id}.")
        return role_id
    if role_name and role_name.strip():
        role = find_role_by_name(db, role_name)
        if role is None:
            raise BadRequest(f'Unknown role "{role_name}". Add it under Setup → Roles first.')
        return role.id
    return None


# ------------------------------------------------------------------ writing
def add_employee(
    db: Session,
    *,
    name: str,
    email: str,
    pin: str,
    role_id: int | None = None,
    role_name: str | None = None,
    access: str = "staff",
    phone: str | None = None,
    max_hours_per_week: float | None = None,
    orbyte_id: str | None = None,
    commit: bool = True,
) -> Employee:
    """Create one employee. Used by the Team page, CSV import, the CLI and the demo seed."""
    if not (name or "").strip():
        raise BadRequest("Name is required.")
    if access not in ("manager", "staff"):
        raise BadRequest('Access must be "manager" or "staff".')
    e = Employee(
        name=name.strip(),
        email=_clean_email(db, email),
        phone=(phone or "").strip() or None,
        access=access,
        role_id=_resolve_role(db, role_id, role_name),
        max_hours_per_week=_clean_limit(max_hours_per_week),
        orbyte_id=_clean_orbyte_id(db, orbyte_id),
        pin_hash=hash_pin(pin),
        active=True,
    )
    db.add(e)
    db.flush()
    activity.log(db, "employee_added", f"Added {e.name}" + (f" ({e.role.name})" if e.role else ""))
    if commit:
        db.commit()
    return e


def create_employee(db: Session, data: schemas.EmployeeCreateInput) -> schemas.Employee:
    e = add_employee(db, name=data.name, email=data.email, pin=data.pin, role_id=data.role_id,
                     access=data.access, phone=data.phone, max_hours_per_week=data.max_hours_per_week,
                     orbyte_id=data.orbyte_id)
    return to_out(db, e)


def import_employees(db: Session, rows: list[schemas.EmployeeImportRow]) -> schemas.EmployeeImportResult:
    created, errors = 0, []
    for i, r in enumerate(rows, start=1):
        savepoint = db.begin_nested()
        try:
            add_employee(db, name=r.name, email=r.email, pin=r.pin, role_name=r.role_name, access=r.access,
                         phone=r.phone, max_hours_per_week=r.max_hours_per_week, orbyte_id=r.orbyte_id,
                         commit=False)
            savepoint.commit()
            created += 1
        except AppError as exc:
            savepoint.rollback()
            errors.append(schemas.RowError(row=i, message=exc.message))
    db.commit()
    return schemas.EmployeeImportResult(created=created, errors=errors)


def _active_managers(db: Session) -> int:
    return db.scalar(
        select(func.count()).select_from(Employee).where(Employee.access == "manager", Employee.active.is_(True))
    ) or 0


def update_employee(db: Session, employee_id: int, data: schemas.EmployeeUpdateInput) -> schemas.Employee:
    e = get_employee(db, employee_id)
    if not data.name.strip():
        raise BadRequest("Name is required.")
    losing_manager = e.access == "manager" and e.active and (
        (data.access is not None and data.access != "manager") or data.active is False
    )
    if losing_manager and _active_managers(db) <= 1:
        raise Conflict("This is the only manager. Make someone else a manager first.")

    e.name = data.name.strip()
    e.email = _clean_email(db, data.email, e.id)
    e.phone = (data.phone or "").strip() or None
    if data.access is not None:
        e.access = data.access
    if data.role_id != e.role_id:
        e.role_id = _resolve_role(db, data.role_id, None)
    e.max_hours_per_week = _clean_limit(data.max_hours_per_week)
    e.orbyte_id = _clean_orbyte_id(db, data.orbyte_id, e.id)
    if data.active is False and e.active:
        _deactivate(db, e)
    elif data.active is True and not e.active:
        e.active = True
        activity.log(db, "employee_reactivated", f"Reactivated {e.name}")
    db.commit()
    db.refresh(e)
    return to_out(db, e)


def _deactivate(db: Session, e: Employee) -> int:
    """Mark inactive, remove their future rostered shifts (unless tied to a cover case),
    withdraw any pending cover offers and sign them out everywhere."""
    e.active = False
    in_cases = select(CoverageCase.shift_id).union(
        select(CoverageCase.replacement_shift_id).where(CoverageCase.replacement_shift_id.is_not(None))
    )
    removed = db.execute(
        delete(Shift).where(
            Shift.employee_id == e.id,
            Shift.status == "scheduled",
            Shift.starts_at > now_utc(),
            Shift.id.notin_(in_cases),
        )
    ).rowcount
    db.execute(
        update(CoverOffer)
        .where(CoverOffer.employee_id == e.id, CoverOffer.status == "pending")
        .values(status="withdrawn", responded_at=now_utc())
    )
    end_all_sessions(db, e.id)
    activity.log(db, "employee_deactivated", f"Deactivated {e.name}; removed {removed} future shift(s)")
    return removed


def deactivate_employee(db: Session, employee_id: int, actor: Employee) -> None:
    e = get_employee(db, employee_id)
    if not e.active:
        return
    if e.id == actor.id:
        raise Conflict("You can't deactivate your own account.")
    if e.access == "manager" and _active_managers(db) <= 1:
        raise Conflict("This is the only manager. Make someone else a manager first.")
    _deactivate(db, e)
    db.commit()
    # cases left with no pending offers go back to "open"
    from .coverage import reopen_cases_without_offers

    reopen_cases_without_offers(db)
    db.commit()


def reset_pin(db: Session, employee_id: int, pin: str) -> None:
    e = get_employee(db, employee_id)
    e.pin_hash = hash_pin(pin)
    e.failed_logins, e.locked_until = 0, None
    end_all_sessions(db, e.id)
    activity.log(db, "pin_reset", f"Reset PIN for {e.name}")
    db.commit()
