"""Request/response shapes (camelCase JSON), matching lib/api-spec/openapi.yaml."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Access = Literal["manager", "staff"]
ShiftStatus = Literal["scheduled", "needs_cover", "covered", "cancelled"]
ShiftSource = Literal["generated", "manual", "cover"]
LeaveStatus = Literal["pending", "approved", "rejected"]
CoverageStatus = Literal["open", "offered", "filled", "cancelled"]
OfferStatus = Literal["pending", "accepted", "declined", "withdrawn", "expired"]


class Model(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------- auth
class LoginInput(Model):
    email: str
    pin: str


class CurrentUser(Model):
    id: int
    name: str
    email: str
    access: Access
    role_id: int | None
    role_name: str | None


class LoginResult(Model):
    token: str
    user: CurrentUser


class ChangePinInput(Model):
    current_pin: str
    new_pin: str


class ResetPinInput(Model):
    pin: str


# ---------------------------------------------------------------- settings
class Settings(Model):
    branch_name: str
    timezone: str
    open_time: str
    close_time: str
    max_hours_per_day: float
    max_hours_per_week: float
    max_days_per_week: int
    min_rest_hours: float
    operating_days: list[int]
    week_starts_on: int
    orbyte_connected: bool
    leave_source: Literal["manual", "import", "orbyte"]


class SettingsInput(Model):
    branch_name: str
    open_time: str
    close_time: str
    max_hours_per_day: float
    max_hours_per_week: float
    max_days_per_week: int
    min_rest_hours: float
    operating_days: list[int]
    week_starts_on: int


# ---------------------------------------------------------------- roles / patterns
class Role(Model):
    id: int
    name: str
    color: str
    employee_count: int


class RoleInput(Model):
    name: str
    color: str | None = None


class PatternRequirement(Model):
    role_id: int
    role_name: str
    headcount: int


class PatternRequirementInput(Model):
    role_id: int
    headcount: int


class ShiftPattern(Model):
    id: int
    name: str
    start_time: str
    end_time: str
    hours: float
    days: list[int]
    active: bool
    requirements: list[PatternRequirement]


class ShiftPatternInput(Model):
    name: str
    start_time: str
    end_time: str
    days: list[int]
    active: bool = True
    requirements: list[PatternRequirementInput]


# ---------------------------------------------------------------- employees
class EmployeeRef(Model):
    id: int
    name: str
    email: str
    role_id: int | None
    role_name: str | None


class Employee(Model):
    id: int
    name: str
    email: str
    phone: str | None
    access: Access
    role_id: int | None
    role_name: str | None
    active: bool
    max_hours_per_week: float | None
    orbyte_id: str | None
    on_leave_today: bool
    hours_this_week: float
    created_at: datetime


class EmployeeCreateInput(Model):
    name: str
    email: str
    phone: str | None = None
    access: Access = "staff"
    role_id: int | None = None
    max_hours_per_week: float | None = None
    orbyte_id: str | None = None
    pin: str


class EmployeeUpdateInput(Model):
    name: str
    email: str
    phone: str | None = None
    access: Access | None = None
    role_id: int | None = None
    active: bool | None = None
    max_hours_per_week: float | None = None
    orbyte_id: str | None = None


class EmployeeImportRow(Model):
    name: str
    email: str
    phone: str | None = None
    role_name: str | None = None
    access: Access = "staff"
    max_hours_per_week: float | None = None
    orbyte_id: str | None = None
    pin: str


class EmployeeImportInput(Model):
    rows: list[EmployeeImportRow]


class RowError(Model):
    row: int
    message: str


class EmployeeImportResult(Model):
    created: int
    errors: list[RowError]


# ---------------------------------------------------------------- shifts / roster
class Shift(Model):
    id: int
    date: date
    starts_at: datetime
    ends_at: datetime
    start_time: str
    end_time: str
    hours: float
    role_id: int
    role_name: str
    employee_id: int | None
    employee_name: str | None
    pattern_id: int | None
    pattern_name: str | None
    status: ShiftStatus
    source: ShiftSource
    cover_case_id: int | None
    notes: str | None


class ShiftInput(Model):
    employee_id: int
    role_id: int
    date: date
    start_time: str
    end_time: str
    notes: str | None = None
    override: bool = False


class RosterAssignee(Model):
    shift_id: int
    employee_id: int | None
    employee_name: str | None
    status: ShiftStatus


class RosterSlot(Model):
    pattern_id: int
    pattern_name: str
    start_time: str
    end_time: str
    role_id: int
    role_name: str
    required: int
    assigned: list[RosterAssignee]
    short_by: int


class RosterDay(Model):
    date: date
    weekday: int
    open: bool
    slots: list[RosterSlot]
    other_shifts: list[Shift]


class RosterEmployeeHours(Model):
    employee_id: int
    name: str
    role_name: str | None
    hours: float
    days: int
    max_hours: float


class RosterWeek(Model):
    week_start: date
    week_end: date
    days: list[RosterDay]
    employees: list[RosterEmployeeHours]
    required: int
    filled: int
    gaps: int


class GenerateRosterInput(Model):
    week_start: date
    replace_existing: bool = False


class RosterGap(Model):
    date: date
    pattern_name: str
    role_name: str
    missing: int
    reason: str


class GenerateRosterResult(Model):
    week_start: date
    created: int
    removed: int
    gaps: list[RosterGap]
    employees: list[RosterEmployeeHours]


# ---------------------------------------------------------------- leave
class Leave(Model):
    id: int
    employee_id: int
    employee_name: str
    role_name: str | None
    leave_type: str
    start_date: date
    end_date: date
    status: LeaveStatus
    source: Literal["manual", "import", "orbyte"]
    external_ref: str | None
    reason: str | None
    created_at: datetime
    decided_at: datetime | None
    affected_shift_count: int


class LeaveInput(Model):
    employee_id: int
    leave_type: str
    start_date: date
    end_date: date
    status: Literal["pending", "approved"] = "pending"
    reason: str | None = None
    external_ref: str | None = None


class LeaveImportRow(Model):
    employee_email: str | None = None
    orbyte_id: str | None = None
    leave_type: str
    start_date: str
    end_date: str
    status: str | None = None
    external_ref: str | None = None
    reason: str | None = None


class LeaveImportInput(Model):
    rows: list[LeaveImportRow]


class LeaveImportResult(Model):
    created: int
    skipped: int
    coverage_cases_opened: int
    errors: list[RowError]


# ---------------------------------------------------------------- coverage
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


class LeaveResult(Model):
    leave: Leave
    coverage_cases: list[CoverageCase]


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


class EmployeeDetail(Model):
    employee: Employee
    upcoming_shifts: list[Shift]
    leave: list[Leave]


# ---------------------------------------------------------------- notifications / dashboard
class Notification(Model):
    id: int
    recipient_employee_id: int | None
    recipient_name: str
    recipient_email: str
    audience: Literal["offered", "replacement", "original", "team", "manager"]
    kind: str
    subject: str
    body: str
    email_status: Literal["queued", "sent", "failed"]
    read_at: datetime | None
    case_id: int | None
    offer_id: int | None
    created_at: datetime


class DashboardSummary(Model):
    open_cases: int
    offered_cases: int
    urgent_cases: int
    filled_this_week: int
    pending_offers: int
    pending_leave: int
    on_leave_today: int
    staff_count: int
    shifts_this_week: int
    roster_gaps_this_week: int


class Activity(Model):
    id: int
    kind: str
    message: str
    created_at: datetime


class HealthStatus(Model):
    status: str
