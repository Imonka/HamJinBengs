"""Branch rules, shift patterns, shifts and roster shapes."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from app.core.schema import Model


ShiftStatus = Literal["scheduled", "needs_cover", "covered", "cancelled"]


ShiftSource = Literal["generated", "manual", "cover"]


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
