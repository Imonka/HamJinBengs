"""/notifications (manager outbox) and /me/notifications (a person's inbox)."""

from fastapi import APIRouter, Response

from app.core.db import DB
from app.modules.accounts.deps import Manager, User
from app.modules.notifications import schemas, service

router = APIRouter()


@router.get("/notifications", response_model=list[schemas.Notification], tags=["notifications"])
def list_notifications(db: DB, _: Manager):
    return service.outbox(db)


@router.get("/me/notifications", response_model=list[schemas.Notification], tags=["me"])
def my_notifications(db: DB, user: User):
    return service.inbox(db, user.id)


@router.post("/me/notifications/read-all", status_code=204, tags=["me"])
def read_all(db: DB, user: User):
    service.mark_all_read(db, user.id)
    return Response(status_code=204)
