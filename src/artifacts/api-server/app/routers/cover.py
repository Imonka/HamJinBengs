"""Leave, cover cases, offers, notifications and the dashboard (manager only)."""

from fastapi import APIRouter
from sqlalchemy import select

from .. import schemas
from ..deps import DB, Manager
from ..models import Notification
from ..services import coverage, dashboard, leave
from ..services.serializers import notification_out

router = APIRouter()


# ---------------------------------------------------------------- leave
@router.get("/leave", response_model=list[schemas.Leave], tags=["leave"])
def list_leave(db: DB, _: Manager, status: schemas.LeaveStatus | None = None,
               employeeId: int | None = None):  # noqa: N803
    return leave.list_leave(db, status, employeeId)


@router.post("/leave", response_model=schemas.LeaveResult, status_code=201, tags=["leave"])
def create_leave(data: schemas.LeaveInput, db: DB, _: Manager):
    return leave.create_leave(db, data)


@router.post("/leave/import", response_model=schemas.LeaveImportResult, tags=["leave"])
def import_leave(data: schemas.LeaveImportInput, db: DB, _: Manager):
    return leave.import_rows(db, data.rows)


@router.post("/leave/{leaveId}/approve", response_model=schemas.LeaveResult, tags=["leave"])
def approve_leave(leaveId: int, db: DB, _: Manager):  # noqa: N803
    return leave.approve(db, leaveId)


@router.post("/leave/{leaveId}/reject", response_model=schemas.Leave, tags=["leave"])
def reject_leave(leaveId: int, db: DB, _: Manager):  # noqa: N803
    return leave.reject(db, leaveId)


# ---------------------------------------------------------------- coverage
@router.get("/coverage", response_model=list[schemas.CoverageCase], tags=["coverage"])
def list_coverage(db: DB, _: Manager, status: schemas.CoverageStatus | None = None):
    return coverage.list_cases(db, status)


@router.get("/coverage/{caseId}", response_model=schemas.CoverageCase, tags=["coverage"])
def get_coverage(caseId: int, db: DB, _: Manager):  # noqa: N803
    return coverage.case_detail(db, caseId)


@router.get("/coverage/{caseId}/candidates", response_model=schemas.CandidateList, tags=["coverage"])
def get_candidates(caseId: int, db: DB, _: Manager):  # noqa: N803
    return coverage.candidates(db, caseId)


@router.post("/coverage/{caseId}/offers", response_model=schemas.CoverageCase, tags=["coverage"])
def send_offers(caseId: int, data: schemas.SendOffersInput, db: DB, manager: Manager):  # noqa: N803
    return coverage.send_offers(db, caseId, data, manager)


@router.post("/coverage/{caseId}/offers/{offerId}/withdraw", response_model=schemas.CoverageCase,
             tags=["coverage"])
def withdraw_offer(caseId: int, offerId: int, db: DB, _: Manager):  # noqa: N803
    return coverage.withdraw_offer(db, caseId, offerId)


@router.post("/coverage/{caseId}/cancel", response_model=schemas.CoverageCase, tags=["coverage"])
def cancel_coverage(caseId: int, db: DB, _: Manager):  # noqa: N803
    return coverage.cancel_case(db, caseId)


# ---------------------------------------------------------------- notifications / dashboard
@router.get("/notifications", response_model=list[schemas.Notification], tags=["notifications"])
def list_notifications(db: DB, _: Manager):
    rows = db.scalars(select(Notification).order_by(Notification.created_at.desc(), Notification.id.desc())
                      .limit(300))
    return [notification_out(n) for n in rows]


@router.get("/dashboard/summary", response_model=schemas.DashboardSummary, tags=["dashboard"])
def get_summary(db: DB, _: Manager):
    return dashboard.summary(db)


@router.get("/dashboard/activity", response_model=list[schemas.Activity], tags=["dashboard"])
def get_activity(db: DB, _: Manager):
    return dashboard.recent_activity(db)
