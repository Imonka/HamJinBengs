"""Database rows -> API response shapes."""

from collections.abc import Iterable
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import schemas
from ..models import CoverageCase, CoverOffer, Employee, LeaveRequest, Notification, Shift
from ..timeutil import hours_between, now_utc, to_local


def employee_ref(e: Employee) -> schemas.EmployeeRef:
    return schemas.EmployeeRef(
        id=e.id, name=e.name, email=e.email, role_id=e.role_id, role_name=e.role.name if e.role else None
    )


def case_ids_for_shifts(db: Session, shift_ids: Iterable[int]) -> dict[int, int]:
    """shift id -> the cover case it belongs to (as the shift needing cover, or as the replacement)."""
    ids = list(shift_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(CoverageCase.id, CoverageCase.shift_id, CoverageCase.replacement_shift_id, CoverageCase.status)
        .where(or_(CoverageCase.shift_id.in_(ids), CoverageCase.replacement_shift_id.in_(ids)))
        .order_by(CoverageCase.id)
    ).all()
    out: dict[int, int] = {}
    for case_id, shift_id, repl_id, status in rows:
        if status != "cancelled" or shift_id not in out:
            out[shift_id] = case_id
        if repl_id:
            out[repl_id] = case_id
    return out


def shift_out(s: Shift, tz: ZoneInfo, case_map: dict[int, int] | None = None) -> schemas.Shift:
    start, end = to_local(s.starts_at, tz), to_local(s.ends_at, tz)
    return schemas.Shift(
        id=s.id,
        date=s.date,
        starts_at=s.starts_at,
        ends_at=s.ends_at,
        start_time=f"{start:%H:%M}",
        end_time=f"{end:%H:%M}",
        hours=hours_between(s.starts_at, s.ends_at),
        role_id=s.role_id,
        role_name=s.role.name,
        employee_id=s.employee_id,
        employee_name=s.employee.name if s.employee else None,
        pattern_id=s.pattern_id,
        pattern_name=s.pattern.name if s.pattern else None,
        status=s.status,  # type: ignore[arg-type]
        source=s.source,  # type: ignore[arg-type]
        cover_case_id=(case_map or {}).get(s.id),
        notes=s.notes,
    )


def shifts_out(db: Session, shifts: list[Shift], tz: ZoneInfo) -> list[schemas.Shift]:
    case_map = case_ids_for_shifts(db, [s.id for s in shifts])
    return [shift_out(s, tz, case_map) for s in shifts]


def offer_out(o: CoverOffer) -> schemas.CoverOffer:
    return schemas.CoverOffer(
        id=o.id,
        case_id=o.case_id,
        employee=employee_ref(o.employee),
        status=o.status,  # type: ignore[arg-type]
        message=o.message,
        created_at=o.created_at,
        responded_at=o.responded_at,
        response_note=o.response_note,
    )


def case_out(c: CoverageCase, tz: ZoneInfo) -> schemas.CoverageCase:
    starts_in = (c.shift.starts_at - now_utc()).total_seconds() / 3600
    return schemas.CoverageCase(
        id=c.id,
        status=c.status,  # type: ignore[arg-type]
        shift=shift_out(c.shift, tz, {c.shift_id: c.id}),
        leave=schemas.LeaveRef(
            id=c.leave.id,
            leave_type=c.leave.leave_type,
            start_date=c.leave.start_date,
            end_date=c.leave.end_date,
            reason=c.leave.reason,
        ),
        original_employee=employee_ref(c.original_employee),
        replacement_employee=employee_ref(c.replacement_employee) if c.replacement_employee else None,
        offers=[offer_out(o) for o in c.offers],
        opened_at=c.opened_at,
        filled_at=c.filled_at,
        urgent=c.status in ("open", "offered") and 0 <= starts_in <= 48,
        starts_in_hours=round(starts_in, 1),
    )


def leave_out(lv: LeaveRequest, affected: int) -> schemas.Leave:
    e = lv.employee
    return schemas.Leave(
        id=lv.id,
        employee_id=lv.employee_id,
        employee_name=e.name,
        role_name=e.role.name if e.role else None,
        leave_type=lv.leave_type,
        start_date=lv.start_date,
        end_date=lv.end_date,
        status=lv.status,  # type: ignore[arg-type]
        source=lv.source,  # type: ignore[arg-type]
        external_ref=lv.external_ref,
        reason=lv.reason,
        created_at=lv.created_at,
        decided_at=lv.decided_at,
        affected_shift_count=affected,
    )


def notification_out(n: Notification) -> schemas.Notification:
    return schemas.Notification(
        id=n.id,
        recipient_employee_id=n.recipient_employee_id,
        recipient_name=n.recipient_name,
        recipient_email=n.recipient_email,
        audience=n.audience,  # type: ignore[arg-type]
        kind=n.kind,
        subject=n.subject,
        body=n.body,
        email_status=n.email_status,  # type: ignore[arg-type]
        read_at=n.read_at,
        case_id=n.case_id,
        offer_id=n.offer_id,
        created_at=n.created_at,
    )
