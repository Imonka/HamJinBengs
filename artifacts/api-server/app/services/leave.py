"""Leave requests, and turning approved leave into cover cases.

When leave is approved (by hand, by import, or later by Orbyte sync):
  * every future shift the person was rostered for during the leave is marked "needs_cover"
  * a cover case is opened for each one, ready for the manager to pick replacements
  * the person on leave and the managers are notified
"""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .. import schemas
from ..errors import BadRequest, Conflict, NotFound
from ..models import CoverageCase, Employee, LeaveRequest, Shift
from ..timeutil import fmt_window, now_utc
from . import activity
from .leave_sources import LeaveRecord, LeaveSource, normalise_status, parse_date
from .notifications import notify, notify_managers
from .serializers import case_out, leave_out
from .settings import get_rules


def _affected_count(db: Session, lv: LeaveRequest) -> int:
    return db.scalar(
        select(func.count())
        .select_from(Shift)
        .where(
            Shift.employee_id == lv.employee_id,
            Shift.date.between(lv.start_date, lv.end_date),
            Shift.status.in_(["scheduled", "needs_cover", "covered"]),
        )
    ) or 0


def to_out(db: Session, lv: LeaveRequest) -> schemas.Leave:
    return leave_out(lv, _affected_count(db, lv))


def list_leave(db: Session, status: str | None, employee_id: int | None) -> list[schemas.Leave]:
    q = select(LeaveRequest)
    if status:
        q = q.where(LeaveRequest.status == status)
    if employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    rows = db.scalars(q.order_by(LeaveRequest.start_date.desc(), LeaveRequest.id.desc()))
    return [to_out(db, lv) for lv in rows]


def get_leave(db: Session, leave_id: int) -> LeaveRequest:
    lv = db.get(LeaveRequest, leave_id)
    if lv is None:
        raise NotFound("Leave request not found.")
    return lv


def open_cover_for_leave(db: Session, lv: LeaveRequest) -> list[CoverageCase]:
    """Flag the person's upcoming shifts during approved leave and open a cover case for each."""
    tz = get_rules(db).tz
    shifts = db.scalars(
        select(Shift)
        .where(
            Shift.employee_id == lv.employee_id,
            Shift.status == "scheduled",
            Shift.date.between(lv.start_date, lv.end_date),
            Shift.starts_at > now_utc(),
        )
        .order_by(Shift.starts_at)
    ).all()
    cases: list[CoverageCase] = []
    for s in shifts:
        s.status = "needs_cover"
        case = CoverageCase(shift=s, leave=lv, original_employee_id=lv.employee_id, status="open")
        db.add(case)
        cases.append(case)
    db.flush()

    if cases:
        windows = "\n".join(f"• {fmt_window(c.shift.starts_at, c.shift.ends_at, tz)} ({c.shift.role.name})"
                            for c in cases)
        notify(
            db, lv.employee, audience="original", kind="leave_approved",
            subject=f"Your {lv.leave_type.lower()} leave is approved",
            body=f"Your leave is approved. These shifts will be covered by a colleague:\n{windows}",
        )
        notify_managers(
            db, kind="cover_needed",
            subject=f"{len(cases)} shift(s) need cover: {lv.employee.name} on leave",
            body=f"{lv.employee.name} is on {lv.leave_type.lower()} leave. Pick replacements for:\n{windows}",
            case_id=cases[0].id,
        )
        activity.log(db, "cover_opened",
                     f"{len(cases)} cover case(s) opened for {lv.employee.name}'s {lv.leave_type.lower()} leave")
    return cases


def _result(db: Session, lv: LeaveRequest, cases: list[CoverageCase]) -> schemas.LeaveResult:
    tz = get_rules(db).tz
    return schemas.LeaveResult(leave=to_out(db, lv), coverage_cases=[case_out(c, tz) for c in cases])


def _check_dates(start: date, end: date) -> None:
    if end < start:
        raise BadRequest("Leave end date is before the start date.")


def create_leave(db: Session, data: schemas.LeaveInput) -> schemas.LeaveResult:
    employee = db.get(Employee, data.employee_id)
    if employee is None:
        raise NotFound("Employee not found.")
    if not data.leave_type.strip():
        raise BadRequest("Leave type is required.")
    _check_dates(data.start_date, data.end_date)
    if data.external_ref and db.scalar(select(LeaveRequest).where(LeaveRequest.external_ref == data.external_ref)):
        raise Conflict(f'Leave with reference "{data.external_ref}" already exists.')

    lv = LeaveRequest(
        employee_id=employee.id, employee=employee, leave_type=data.leave_type.strip(),
        start_date=data.start_date, end_date=data.end_date, status=data.status, source="manual",
        external_ref=data.external_ref or None, reason=data.reason,
        decided_at=now_utc() if data.status == "approved" else None,
    )
    db.add(lv)
    db.flush()
    activity.log(db, "leave_added", f"{data.status.title()} {lv.leave_type.lower()} leave added for {employee.name}")
    cases = open_cover_for_leave(db, lv) if lv.status == "approved" else []
    db.commit()
    return _result(db, lv, cases)


def approve(db: Session, leave_id: int) -> schemas.LeaveResult:
    lv = get_leave(db, leave_id)
    if lv.status != "pending":
        raise Conflict(f"This leave is already {lv.status}.")
    lv.status, lv.decided_at = "approved", now_utc()
    activity.log(db, "leave_approved", f"Approved {lv.employee.name}'s {lv.leave_type.lower()} leave")
    cases = open_cover_for_leave(db, lv)
    db.commit()
    return _result(db, lv, cases)


def reject(db: Session, leave_id: int) -> schemas.Leave:
    lv = get_leave(db, leave_id)
    if lv.status != "pending":
        raise Conflict(f"This leave is already {lv.status}.")
    lv.status, lv.decided_at = "rejected", now_utc()
    notify(db, lv.employee, audience="original", kind="leave_rejected",
           subject=f"Your {lv.leave_type.lower()} leave was not approved",
           body=f"Your leave from {lv.start_date:%d %b} to {lv.end_date:%d %b} was not approved. "
                "Your shifts stay as rostered.")
    activity.log(db, "leave_rejected", f"Rejected {lv.employee.name}'s {lv.leave_type.lower()} leave")
    db.commit()
    return to_out(db, lv)


# ------------------------------------------------------------------ import / sync
def ingest_leave_records(db: Session, records: list[LeaveRecord | Exception], source: str) -> schemas.LeaveImportResult:
    """The single entry point for leave from outside (CSV import today, Orbyte sync later).
    `records` may contain Exceptions for rows that couldn't be parsed; they're reported per row."""
    created = skipped = opened = 0
    errors: list[schemas.RowError] = []
    for i, rec in enumerate(records, start=1):
        if isinstance(rec, Exception):
            errors.append(schemas.RowError(row=i, message=str(rec)))
            continue
        employee = None
        if rec.orbyte_id:
            employee = db.scalar(select(Employee).where(Employee.orbyte_id == rec.orbyte_id.strip()))
        if employee is None and rec.employee_email:
            employee = db.scalar(select(Employee).where(Employee.email == rec.employee_email.strip().lower()))
        if employee is None:
            errors.append(schemas.RowError(row=i, message="No employee matches this Orbyte ID / email"))
            continue
        if rec.end_date < rec.start_date:
            errors.append(schemas.RowError(row=i, message="End date is before start date"))
            continue
        if rec.status == "rejected":
            skipped += 1
            continue
        dup = (
            db.scalar(select(LeaveRequest).where(LeaveRequest.external_ref == rec.external_ref))
            if rec.external_ref
            else db.scalar(select(LeaveRequest).where(
                LeaveRequest.employee_id == employee.id,
                LeaveRequest.start_date == rec.start_date,
                LeaveRequest.end_date == rec.end_date,
                LeaveRequest.leave_type == rec.leave_type,
            ))
        )
        if dup is not None:
            # Already known. If it has since been approved in Orbyte, approve it here too.
            if dup.status == "pending" and rec.status == "approved":
                dup.status, dup.decided_at = "approved", now_utc()
                opened += len(open_cover_for_leave(db, dup))
            else:
                skipped += 1
            continue

        lv = LeaveRequest(
            employee_id=employee.id, employee=employee, leave_type=rec.leave_type, start_date=rec.start_date,
            end_date=rec.end_date, status=rec.status, source=source, external_ref=rec.external_ref,
            reason=rec.reason, decided_at=now_utc() if rec.status == "approved" else None,
        )
        db.add(lv)
        db.flush()
        created += 1
        if lv.status == "approved":
            opened += len(open_cover_for_leave(db, lv))

    if created:
        activity.log(db, "leave_imported", f"Imported {created} leave record(s) from {source}")
    db.commit()
    return schemas.LeaveImportResult(created=created, skipped=skipped, coverage_cases_opened=opened, errors=errors)


def import_rows(db: Session, rows: list[schemas.LeaveImportRow]) -> schemas.LeaveImportResult:
    records: list[LeaveRecord | Exception] = []
    for r in rows:
        try:
            if not (r.employee_email or r.orbyte_id):
                raise ValueError("Each row needs an employee email or Orbyte ID")
            if not r.leave_type.strip():
                raise ValueError("Leave type is missing")
            records.append(LeaveRecord(
                leave_type=r.leave_type.strip(), start_date=parse_date(r.start_date),
                end_date=parse_date(r.end_date), status=normalise_status(r.status),
                employee_email=r.employee_email, orbyte_id=r.orbyte_id,
                external_ref=(r.external_ref or "").strip() or None, reason=r.reason,
            ))
        except ValueError as exc:
            records.append(exc)
    return ingest_leave_records(db, records, source="import")


def sync_from(db: Session, source: LeaveSource) -> schemas.LeaveImportResult:
    """For a future live connection (see leave_sources.py)."""
    from .settings import get_settings

    settings = get_settings(db)
    result = ingest_leave_records(db, list(source.fetch(settings.orbyte_last_sync_at)), source=source.name)
    settings.orbyte_last_sync_at = now_utc()
    db.commit()
    return result
