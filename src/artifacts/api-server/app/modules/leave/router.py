"""/leave: requests, CSV import, approval and the cover preview (manager only)."""

from fastapi import APIRouter

from app.core.db import DB
from app.modules.accounts.deps import Manager
from app.modules.leave import schemas, service

router = APIRouter(prefix="/leave", tags=["leave"])


@router.get("", response_model=list[schemas.Leave])
def list_leave(db: DB, _: Manager, status: schemas.LeaveStatus | None = None,
               employeeId: int | None = None):  # noqa: N803
    return service.list_leave(db, status, employeeId)


@router.post("", response_model=schemas.LeaveResult, status_code=201)
def create_leave(data: schemas.LeaveInput, db: DB, _: Manager):
    return service.create_leave(db, data)


@router.post("/import", response_model=schemas.LeaveImportResult)
def import_leave(data: schemas.LeaveImportInput, db: DB, _: Manager):
    return service.import_rows(db, data.rows)


@router.get("/{leaveId}/cover-preview", response_model=schemas.LeaveCoverPreview)
def leave_cover_preview(leaveId: int, db: DB, _: Manager):  # noqa: N803
    return service.cover_preview(db, leaveId)


@router.post("/{leaveId}/approve", response_model=schemas.LeaveResult)
def approve_leave(leaveId: int, db: DB, _: Manager):  # noqa: N803
    return service.approve(db, leaveId)


@router.post("/{leaveId}/reject", response_model=schemas.Leave)
def reject_leave(leaveId: int, db: DB, _: Manager):  # noqa: N803
    return service.reject(db, leaveId)
