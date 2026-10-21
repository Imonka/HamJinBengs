"""Leave rows -> API shapes."""

from app.modules.leave import schemas
from app.modules.leave.models import LeaveRequest


def leave_out(lv: LeaveRequest, affected: int) -> schemas.Leave:
    e = lv.employee
    return schemas.Leave(
        id=lv.id,
        employee_id=lv.employee_id,
        employee_name=e.name,
        role_name=e.role.name if e.role else None,
        leave_type=lv.leave_type,
        start_date=lv.start_date,
        end_date=lv.end_date,
        status=lv.status,  # type: ignore[arg-type]
        source=lv.source,  # type: ignore[arg-type]
        external_ref=lv.external_ref,
        reason=lv.reason,
        created_at=lv.created_at,
        decided_at=lv.decided_at,
        affected_shift_count=affected,
    )
