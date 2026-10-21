"""Cover case and offer rows -> API shapes."""

from zoneinfo import ZoneInfo

from app.core.timeutil import now_utc
from app.modules.cover import schemas
from app.modules.cover.models import CoverageCase, CoverOffer
from app.modules.people.serializers import employee_ref
from app.modules.scheduling.serializers import shift_out


def offer_out(o: CoverOffer) -> schemas.CoverOffer:
    return schemas.CoverOffer(
        id=o.id,
        case_id=o.case_id,
        employee=employee_ref(o.employee),
        status=o.status,  # type: ignore[arg-type]
        message=o.message,
        created_at=o.created_at,
        responded_at=o.responded_at,
        response_note=o.response_note,
    )


def case_out(c: CoverageCase, tz: ZoneInfo) -> schemas.CoverageCase:
    starts_in = (c.shift.starts_at - now_utc()).total_seconds() / 3600
    return schemas.CoverageCase(
        id=c.id,
        status=c.status,  # type: ignore[arg-type]
        shift=shift_out(c.shift, tz, {c.shift_id: c.id}),
        leave=schemas.LeaveRef(
            id=c.leave.id,
            leave_type=c.leave.leave_type,
            start_date=c.leave.start_date,
            end_date=c.leave.end_date,
            reason=c.leave.reason,
        ),
        original_employee=employee_ref(c.original_employee),
        replacement_employee=employee_ref(c.replacement_employee) if c.replacement_employee else None,
        offers=[offer_out(o) for o in c.offers],
        opened_at=c.opened_at,
        filled_at=c.filled_at,
        urgent=c.status in ("open", "offered") and 0 <= starts_in <= 48,
        starts_in_hours=round(starts_in, 1),
    )
