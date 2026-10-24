"""/employees and /roles. Managers can add staff and change work settings (role, limits,
Orbyte ID, active). They cannot change anyone's personal details, PIN or access."""

from fastapi import APIRouter, Response

from app.core.db import DB
from app.modules.accounts.deps import Manager, User
from app.modules.people import detail, roles, schemas, service

router = APIRouter()


# ---------------------------------------------------------------- employees
@router.get("/employees", response_model=list[schemas.Employee], tags=["employees"])
def list_employees(db: DB, _: Manager, roleId: int | None = None, active: bool | None = None,  # noqa: N803
                   search: str | None = None):
    return service.list_employees(db, roleId, active, search)


@router.post("/employees", response_model=schemas.Employee, status_code=201, tags=["employees"])
def create_employee(data: schemas.EmployeeCreateInput, db: DB, _: Manager):
    return service.create_employee(db, data)


@router.post("/employees/import", response_model=schemas.EmployeeImportResult, tags=["employees"])
def import_employees(data: schemas.EmployeeImportInput, db: DB, _: Manager):
    return service.import_employees(db, data.rows)


@router.get("/employees/{employeeId}", response_model=detail.EmployeeDetail, tags=["employees"])
def get_employee(employeeId: int, db: DB, _: Manager):  # noqa: N803
    return detail.employee_detail(db, employeeId)


@router.put("/employees/{employeeId}", response_model=schemas.Employee, tags=["employees"])
def update_employee(employeeId: int, data: schemas.EmployeeUpdateInput, db: DB, _: Manager):  # noqa: N803
    return service.update_employee(db, employeeId, data)


@router.delete("/employees/{employeeId}", status_code=204, tags=["employees"])
def deactivate_employee(employeeId: int, db: DB, manager: Manager):  # noqa: N803
    service.deactivate_employee(db, employeeId, manager)
    return Response(status_code=204)


# ---------------------------------------------------------------- roles
@router.get("/roles", response_model=list[schemas.Role], tags=["roles"])
def list_roles(db: DB, _: User):
    return roles.list_roles(db)


@router.post("/roles", response_model=schemas.Role, status_code=201, tags=["roles"])
def create_role(data: schemas.RoleInput, db: DB, _: Manager):
    return roles.create_role(db, data)


@router.put("/roles/{roleId}", response_model=schemas.Role, tags=["roles"])
def update_role(roleId: int, data: schemas.RoleInput, db: DB, _: Manager):  # noqa: N803
    return roles.update_role(db, roleId, data)


@router.delete("/roles/{roleId}", status_code=204, tags=["roles"])
def delete_role(roleId: int, db: DB, _: Manager):  # noqa: N803
    roles.delete_role(db, roleId)
    return Response(status_code=204)
