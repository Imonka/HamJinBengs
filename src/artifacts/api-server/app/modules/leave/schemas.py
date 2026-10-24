"""Leave request, import and cover-preview shapes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from app.core.schema import Model, RowError
from app.modules.cover.schemas import Candidate, CoverageCase
from app.modules.scheduling.schemas import Shift


LeaveStatus = Literal["pending", "approved", "rejected"]


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


class LeaveResult(Model):
    leave: Leave
    coverage_cases: list[CoverageCase]


class CoverPreviewShift(Model):
    shift: Shift
    eligible_count: int
    unavailable_count: int
    top_candidates: list[Candidate]


class LeaveCoverPreview(Model):
    leave_id: int
    shifts: list[CoverPreviewShift]
