"""The person page: one employee plus their upcoming shifts and leave.

This is a view that pulls from other modules, so it lives apart from the core people code
(which other modules depend on) to keep imports one-way."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.schema import Model
from app.modules.leave.schemas import Leave
from app.modules.leave.service import leave_for
from app.modules.people import service
from app.modules.people.schemas import Employee
from app.modules.scheduling.schemas import Shift
from app.modules.scheduling.shifts import upcoming_shifts


class EmployeeDetail(Model):
    employee: Employee
    upcoming_shifts: list[Shift]
    leave: list[Leave]


def employee_detail(db: Session, employee_id: int) -> EmployeeDetail:
    e = service.get_employee(db, employee_id)
    return EmployeeDetail(
        employee=service.to_out(db, e),
        upcoming_shifts=upcoming_shifts(db, e.id),
        leave=leave_for(db, e.id),
    )
