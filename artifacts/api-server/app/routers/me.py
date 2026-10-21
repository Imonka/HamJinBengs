"""Employee self-service. Staff can only see their own shifts and messages, and accept or
decline cover offers sent to them. They cannot assign or change shifts."""

from datetime import date, timedelta

from fastapi import APIRouter, Query, Response
from sqlalchemy import select, update

from .. import schemas
from ..deps import DB, User
from ..models import Notification, Shift
from ..services import coverage
from ..services.serializers import notification_out, shifts_out
from ..services.settings import get_rules
from ..timeutil import local_today, now_utc

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/shifts", response_model=list[schemas.Shift])
def my_shifts(db: DB, user: User, date_from: date | None = Query(None, alias="from"),
              date_to: date | None = Query(None, alias="to")):
    rules = get_rules(db)
    start = date_from or local_today(rules.tz)
    end = date_to or start + timedelta(days=14)
    rows = db.scalars(select(Shift).where(Shift.employee_id == user.id, Shift.date.between(start, end),
                                          Shift.status != "cancelled").order_by(Shift.starts_at)).all()
    return shifts_out(db, list(rows), rules.tz)


@router.get("/offers", response_model=list[schemas.MyOffer])
def my_offers(db: DB, user: User, status: schemas.OfferStatus | None = None):
    return coverage.my_offers(db, user, status)


@router.post("/offers/{offerId}/accept", response_model=schemas.MyOffer)
def accept(offerId: int, db: DB, user: User):  # noqa: N803 (matches the API path name)
    return coverage.accept_offer(db, offerId, user)


@router.post("/offers/{offerId}/decline", response_model=schemas.MyOffer)
def decline(offerId: int, db: DB, user: User, data: schemas.DeclineOfferInput | None = None):  # noqa: N803
    return coverage.decline_offer(db, offerId, user, data.note if data else None)


@router.get("/notifications", response_model=list[schemas.Notification])
def my_notifications(db: DB, user: User):
    rows = db.scalars(select(Notification).where(Notification.recipient_employee_id == user.id)
                      .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(100))
    return [notification_out(n) for n in rows]


@router.post("/notifications/read-all", status_code=204)
def read_all(db: DB, user: User):
    db.execute(update(Notification).where(Notification.recipient_employee_id == user.id,
                                          Notification.read_at.is_(None)).values(read_at=now_utc()))
    db.commit()
    return Response(status_code=204)
