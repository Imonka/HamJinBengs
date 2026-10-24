"""Loads people from the database into the engine's StaffMember objects.

This is the ONE place that decides what the scheduling engine knows about a person.
When you add a new kind of rule (e.g. "never works Sundays"), load its data here into
`StaffMember.attributes` and every part of the system will see it.
"""

from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.timeutil import now_utc
from app.modules.cover.models import CoverageCase
from app.modules.leave.models import LeaveRequest
from app.modules.people.models import Employee
from app.modules.scheduling.engine import Booking, LeaveBlock, Rules, StaffMember
from app.modules.scheduling.models import Shift


def load_staff(
    db: Session,
    rules: Rules,
    day: date,
    *,
    employee_ids: list[int] | None = None,
    role_id: int | None = None,
    active_only: bool = True,
    exclude_ids: list[int] | None = None,
    now: datetime | None = None,
) -> list[StaffMember]:
    """People plus their bookings/leave around the week containing `day`
    (the whole week, plus one day either side for rest-gap checks)."""
    week_start, week_end = rules.week_of(day)
    window_start, window_end = week_start - timedelta(days=1), week_end + timedelta(days=1)

    q = select(Employee)
    if employee_ids is not None:
        q = q.where(Employee.id.in_(employee_ids))
    if role_id is not None:
        q = q.where(Employee.role_id == role_id)
    if active_only:
        q = q.where(Employee.active.is_(True))
    if exclude_ids:
        q = q.where(Employee.id.notin_(exclude_ids))
    employees = list(db.scalars(q.order_by(Employee.name)))
    if not employees:
        return []
    ids = [e.id for e in employees]

    bookings = db.scalars(
        select(Shift).where(
            Shift.employee_id.in_(ids),
            Shift.status == "scheduled",
            Shift.date.between(window_start, window_end),
        )
    )
    leave = db.scalars(
        select(LeaveRequest).where(
            LeaveRequest.employee_id.in_(ids),
            LeaveRequest.status.in_(["approved", "pending"]),
            LeaveRequest.start_date <= window_end,
            LeaveRequest.end_date >= window_start,
        )
    )
    since = (now or now_utc()) - timedelta(days=30)
    covers = Counter(
        dict(
            db.execute(
                select(CoverageCase.replacement_employee_id, func.count())
                .where(
                    and_(
                        CoverageCase.status == "filled",
                        CoverageCase.replacement_employee_id.in_(ids),
                        CoverageCase.filled_at >= since,
                    )
                )
                .group_by(CoverageCase.replacement_employee_id)
            ).all()
        )
    )

    people = {
        e.id: StaffMember(
            id=e.id,
            name=e.name,
            role_id=e.role_id,
            role_name=e.role.name if e.role else None,
            active=e.active,
            max_hours_per_week=e.max_hours_per_week,
            recent_covers=covers.get(e.id, 0),
        )
        for e in employees
    }
    for s in bookings:
        people[s.employee_id].bookings.append(Booking(s.date, s.starts_at, s.ends_at, s.role_id, s.id))
    for lv in leave:
        people[lv.employee_id].leave.append(LeaveBlock(lv.start_date, lv.end_date, lv.status, lv.leave_type))
    return list(people.values())
