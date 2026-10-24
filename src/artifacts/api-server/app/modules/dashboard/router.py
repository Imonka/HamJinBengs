"""/dashboard: the manager's Desk."""

from fastapi import APIRouter

from app.core.db import DB
from app.modules.accounts.deps import Manager
from app.modules.dashboard import schemas, service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=schemas.DashboardSummary)
def get_summary(db: DB, _: Manager):
    return service.summary(db)


@router.get("/activity", response_model=list[schemas.Activity])
def get_activity(db: DB, _: Manager):
    return service.recent_activity(db)
