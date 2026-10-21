from datetime import time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.activity import Activity
from app.core.timeutil import at, local_today, now_utc
from app.modules.cover.models import CoverageCase, CoverOffer
from app.modules.dashboard import schemas
from app.modules.leave.models import LeaveRequest
from app.modules.people.models import Employee
from app.modules.scheduling.models import Shift
from app.modules.scheduling.roster import week_view
from app.modules.scheduling.rules import get_rules


def _count(db: Session, q) -> int:
    return db.scalar(select(func.count()).select_from(q.subquery())) or 0


def summary(db: Session) -> schemas.DashboardSummary:
    rules = get_rules(db)
    today = local_today(rules.tz)
    ws, we = rules.week_of(today)
    now = now_utc()
    week_from = at(ws, time(0), rules.tz)
    live = select(CoverageCase).join(CoverageCase.shift).where(CoverageCase.status.in_(["open", "offered"]))
    return schemas.DashboardSummary(
        open_cases=_count(db, select(CoverageCase.id).where(CoverageCase.status == "open")),
        offered_cases=_count(db, select(CoverageCase.id).where(CoverageCase.status == "offered")),
        urgent_cases=_count(db, live.where(Shift.starts_at > now, Shift.starts_at <= now + timedelta(hours=48))
                            .with_only_columns(CoverageCase.id)),
        filled_this_week=_count(db, select(CoverageCase.id).where(CoverageCase.status == "filled",
                                                                  CoverageCase.filled_at >= week_from)),
        pending_offers=_count(db, select(CoverOffer.id).where(CoverOffer.status == "pending")),
        pending_leave=_count(db, select(LeaveRequest.id).where(LeaveRequest.status == "pending")),
        on_leave_today=_count(db, select(LeaveRequest.employee_id).distinct().where(
            LeaveRequest.status == "approved", LeaveRequest.start_date <= today, LeaveRequest.end_date >= today)),
        staff_count=_count(db, select(Employee.id).where(Employee.active.is_(True), Employee.access == "staff")),
        shifts_this_week=_count(db, select(Shift.id).where(Shift.status == "scheduled",
                                                           Shift.date.between(ws, we))),
        roster_gaps_this_week=week_view(db, today).gaps,
    )


def recent_activity(db: Session, limit: int = 30) -> list[schemas.Activity]:
    rows = db.scalars(select(Activity).order_by(Activity.created_at.desc(), Activity.id.desc()).limit(limit))
    return [schemas.Activity(id=a.id, kind=a.kind, message=a.message, created_at=a.created_at) for a in rows]
