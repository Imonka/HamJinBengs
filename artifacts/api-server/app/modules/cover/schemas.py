"""Cover case, candidate and offer shapes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.schema import Model
from app.modules.people.schemas import EmployeeRef
from app.modules.scheduling.schemas import Shift


CoverageStatus = Literal["open", "offered", "filled", "cancelled"]


OfferStatus = Literal["pending", "accepted", "declined", "withdrawn", "expired"]


class CoverOffer(Model):
    id: int
    case_id: int
    employee: EmployeeRef
    status: OfferStatus
    message: str | None
    created_at: datetime
    responded_at: datetime | None
    response_note: str | None


class LeaveRef(Model):
    id: int
    leave_type: str
    start_date: date
    end_date: date
    reason: str | None


class CoverageCase(Model):
    id: int
    status: CoverageStatus
    shift: Shift
    leave: LeaveRef
    original_employee: EmployeeRef
    replacement_employee: EmployeeRef | None
    offers: list[CoverOffer]
    opened_at: datetime
    filled_at: datetime | None
    urgent: bool
    starts_in_hours: float


class Candidate(Model):
    employee: EmployeeRef
    score: int
    hours_worked_so_far: float
    hours_this_week: float
    hours_after: float
    max_hours_per_week: float
    hours_that_day: float
    max_hours_per_day: float
    days_this_week: int
    max_days_per_week: int
    back_to_back: bool
    rest_hours_before: float | None
    rest_hours_after: float | None
    reasons: list[str]
    warnings: list[str]
    offer_status: OfferStatus | None


class UnavailableCandidate(Model):
    employee: EmployeeRef
    reasons: list[str]


class CandidateList(Model):
    eligible: list[Candidate]
    unavailable: list[UnavailableCandidate]


class SendOffersInput(Model):
    employee_ids: list[int] = Field(min_length=1)
    message: str | None = None


class DeclineOfferInput(Model):
    note: str | None = None


class MyOffer(Model):
    id: int
    status: OfferStatus
    message: str | None
    created_at: datetime
    responded_at: datetime | None
    shift: Shift
    covering_for: str
    case_status: CoverageStatus
    can_accept: bool
    blocked_reason: str | None
    hours_this_week: float
    hours_after: float
    max_hours_per_week: float
