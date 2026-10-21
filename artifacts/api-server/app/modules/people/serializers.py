"""People rows -> API shapes that other modules embed (e.g. who an offer went to)."""

from app.modules.people import schemas
from app.modules.people.models import Employee


def employee_ref(e: Employee) -> schemas.EmployeeRef:
    return schemas.EmployeeRef(
        id=e.id, name=e.name, email=e.email, role_id=e.role_id, role_name=e.role.name if e.role else None
    )
