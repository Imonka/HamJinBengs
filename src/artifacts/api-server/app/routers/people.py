"""Employees (manager only)."""

from fastapi import APIRouter, Response

from .. import schemas
from ..deps import DB, Manager
from ..services import employees

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[schemas.Employee])
def list_employees(db: DB, _: Manager, roleId: int | None = None, active: bool | None = None,  # noqa: N803
                   search: str | None = None):
    return employees.list_employees(db, roleId, active, search)


@router.post("", response_model=schemas.Employee, status_code=201)
def create_employee(data: schemas.EmployeeCreateInput, db: DB, _: Manager):
    return employees.create_employee(db, data)


@router.post("/import", response_model=schemas.EmployeeImportResult)
def import_employees(data: schemas.EmployeeImportInput, db: DB, _: Manager):
    return employees.import_employees(db, data.rows)


@router.get("/{employeeId}", response_model=schemas.EmployeeDetail)
def get_employee(employeeId: int, db: DB, _: Manager):  # noqa: N803
    return employees.employee_detail(db, employeeId)


@router.put("/{employeeId}", response_model=schemas.Employee)
def update_employee(employeeId: int, data: schemas.EmployeeUpdateInput, db: DB, _: Manager):  # noqa: N803
    return employees.update_employee(db, employeeId, data)


@router.delete("/{employeeId}", status_code=204)
def deactivate_employee(employeeId: int, db: DB, manager: Manager):  # noqa: N803
    employees.deactivate_employee(db, employeeId, manager)
    return Response(status_code=204)


@router.put("/{employeeId}/pin", status_code=204)
def reset_pin(employeeId: int, data: schemas.ResetPinInput, db: DB, _: Manager):  # noqa: N803
    employees.reset_pin(db, employeeId, data.pin)
    return Response(status_code=204)
