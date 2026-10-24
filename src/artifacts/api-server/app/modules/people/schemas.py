"""People and job-role shapes."""

from __future__ import annotations

from datetime import datetime

from app.core.schema import Model, RowError, StrictInput
from app.modules.accounts.schemas import Access


class Role(Model):
    id: int
    name: str
    color: str
    employee_count: int


class RoleInput(Model):
    name: str
    color: str | None = None


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


class EmployeeCreateInput(StrictInput):
    """New accounts made in the app are always staff. Manager access is granted from the server CLI."""

    name: str
    email: str
    phone: str | None = None
    role_id: int | None = None
    max_hours_per_week: float | None = None
    orbyte_id: str | None = None
    pin: str


class EmployeeUpdateInput(StrictInput):
    """What a manager may change on someone else's account: work settings only.
    Name, email, phone and PIN belong to the person themselves; access is CLI-only."""

    role_id: int | None
    active: bool
    max_hours_per_week: float | None
    orbyte_id: str | None


class EmployeeImportRow(StrictInput):
    name: str
    email: str
    phone: str | None = None
    role_name: str | None = None
    max_hours_per_week: float | None = None
    orbyte_id: str | None = None
    pin: str


class EmployeeImportInput(Model):
    rows: list[EmployeeImportRow]


class EmployeeImportResult(Model):
    created: int
    errors: list[RowError]
