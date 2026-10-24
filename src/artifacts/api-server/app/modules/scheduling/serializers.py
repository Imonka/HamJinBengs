"""Shift rows -> API shapes."""

from collections.abc import Iterable
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.timeutil import hours_between, to_local
from app.modules.cover.models import CoverageCase
from app.modules.scheduling import schemas
from app.modules.scheduling.models import Shift


def case_ids_for_shifts(db: Session, shift_ids: Iterable[int]) -> dict[int, int]:
    """shift id -> the cover case it belongs to (as the shift needing cover, or as the replacement)."""
    ids = list(shift_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(CoverageCase.id, CoverageCase.shift_id, CoverageCase.replacement_shift_id, CoverageCase.status)
        .where(or_(CoverageCase.shift_id.in_(ids), CoverageCase.replacement_shift_id.in_(ids)))
        .order_by(CoverageCase.id)
    ).all()
    out: dict[int, int] = {}
    for case_id, shift_id, repl_id, status in rows:
        if status != "cancelled" or shift_id not in out:
            out[shift_id] = case_id
        if repl_id:
            out[repl_id] = case_id
    return out


def shift_out(s: Shift, tz: ZoneInfo, case_map: dict[int, int] | None = None) -> schemas.Shift:
    start, end = to_local(s.starts_at, tz), to_local(s.ends_at, tz)
    return schemas.Shift(
        id=s.id,
        date=s.date,
        starts_at=s.starts_at,
        ends_at=s.ends_at,
        start_time=f"{start:%H:%M}",
        end_time=f"{end:%H:%M}",
        hours=hours_between(s.starts_at, s.ends_at),
        role_id=s.role_id,
        role_name=s.role.name,
        employee_id=s.employee_id,
        employee_name=s.employee.name if s.employee else None,
        pattern_id=s.pattern_id,
        pattern_name=s.pattern.name if s.pattern else None,
        status=s.status,  # type: ignore[arg-type]
        source=s.source,  # type: ignore[arg-type]
        cover_case_id=(case_map or {}).get(s.id),
        notes=s.notes,
    )


def shifts_out(db: Session, shifts: list[Shift], tz: ZoneInfo) -> list[schemas.Shift]:
    case_map = case_ids_for_shifts(db, [s.id for s in shifts])
    return [shift_out(s, tz, case_map) for s in shifts]
