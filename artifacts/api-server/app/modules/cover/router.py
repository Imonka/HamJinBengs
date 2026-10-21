"""/coverage (manager: cases, candidates, offers) and /me/offers (staff: accept or decline).
Staff can only answer offers sent to them; they cannot assign or change shifts."""

from fastapi import APIRouter

from app.core.db import DB
from app.modules.accounts.deps import Manager, User
from app.modules.cover import schemas, service

router = APIRouter()


# ---------------------------------------------------------------- manager
@router.get("/coverage", response_model=list[schemas.CoverageCase], tags=["coverage"])
def list_coverage(db: DB, _: Manager, status: schemas.CoverageStatus | None = None, unfilled: bool = False):
    return service.list_cases(db, status, unfilled)


@router.get("/coverage/{caseId}", response_model=schemas.CoverageCase, tags=["coverage"])
def get_coverage(caseId: int, db: DB, _: Manager):  # noqa: N803
    return service.case_detail(db, caseId)


@router.get("/coverage/{caseId}/candidates", response_model=schemas.CandidateList, tags=["coverage"])
def get_candidates(caseId: int, db: DB, _: Manager):  # noqa: N803
    return service.candidates(db, caseId)


@router.post("/coverage/{caseId}/offers", response_model=schemas.CoverageCase, tags=["coverage"])
def send_offers(caseId: int, data: schemas.SendOffersInput, db: DB, manager: Manager):  # noqa: N803
    return service.send_offers(db, caseId, data, manager)


@router.post("/coverage/{caseId}/offers/{offerId}/withdraw", response_model=schemas.CoverageCase,
             tags=["coverage"])
def withdraw_offer(caseId: int, offerId: int, db: DB, _: Manager):  # noqa: N803
    return service.withdraw_offer(db, caseId, offerId)


@router.post("/coverage/{caseId}/cancel", response_model=schemas.CoverageCase, tags=["coverage"])
def cancel_coverage(caseId: int, db: DB, _: Manager):  # noqa: N803
    return service.cancel_case(db, caseId)


# ---------------------------------------------------------------- staff
@router.get("/me/offers", response_model=list[schemas.MyOffer], tags=["me"])
def my_offers(db: DB, user: User, status: schemas.OfferStatus | None = None):
    return service.my_offers(db, user, status)


@router.post("/me/offers/{offerId}/accept", response_model=schemas.MyOffer, tags=["me"])
def accept(offerId: int, db: DB, user: User):  # noqa: N803 (matches the API path name)
    return service.accept_offer(db, offerId, user)


@router.post("/me/offers/{offerId}/decline", response_model=schemas.MyOffer, tags=["me"])
def decline(offerId: int, db: DB, user: User, data: schemas.DeclineOfferInput | None = None):  # noqa: N803
    return service.decline_offer(db, offerId, user, data.note if data else None)
