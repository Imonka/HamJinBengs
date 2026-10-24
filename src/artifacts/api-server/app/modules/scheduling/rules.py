"""Branch settings: the adjustable working-time rules."""

from sqlalchemy.orm import Session

from app.core.errors import BadRequest
from app.core.timeutil import fmt_hhmm, parse_hhmm
from app.modules.leave.sources import orbyte_connected
from app.modules.scheduling import schemas
from app.modules.scheduling.engine import Rules
from app.modules.scheduling.models import BranchSettings


def get_settings(db: Session) -> BranchSettings:
    row = db.get(BranchSettings, 1)
    if row is None:
        row = BranchSettings(id=1)
        db.add(row)
        db.commit()
    return row


def get_rules(db: Session) -> Rules:
    return rules_from(get_settings(db))


def rules_from(s: BranchSettings) -> Rules:
    return Rules(
        timezone=s.timezone,
        open_time=s.open_time,
        close_time=s.close_time,
        max_hours_per_day=s.max_hours_per_day,
        max_hours_per_week=s.max_hours_per_week,
        max_days_per_week=s.max_days_per_week,
        min_rest_hours=s.min_rest_hours,
        operating_days=frozenset(s.operating_days or []),
        week_starts_on=s.week_starts_on,
    )


def settings_out(s: BranchSettings) -> schemas.Settings:
    return schemas.Settings(
        branch_name=s.branch_name,
        timezone=s.timezone,
        open_time=fmt_hhmm(s.open_time),
        close_time=fmt_hhmm(s.close_time),
        max_hours_per_day=s.max_hours_per_day,
        max_hours_per_week=s.max_hours_per_week,
        max_days_per_week=s.max_days_per_week,
        min_rest_hours=s.min_rest_hours,
        operating_days=sorted(s.operating_days or []),
        week_starts_on=s.week_starts_on,
        orbyte_connected=orbyte_connected(),
        leave_source=s.leave_source,  # type: ignore[arg-type]
    )


def validate_days(days: list[int], what: str) -> list[int]:
    if not days:
        raise BadRequest(f"Pick at least one day for {what}.")
    if any(d not in range(7) for d in days):
        raise BadRequest("Days must be 0 (Monday) to 6 (Sunday).")
    return sorted(set(days))


def update_settings(db: Session, data: schemas.SettingsInput) -> BranchSettings:
    try:
        open_t, close_t = parse_hhmm(data.open_time), parse_hhmm(data.close_time)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    if open_t >= close_t:
        raise BadRequest("Opening time must be before closing time.")
    if not data.branch_name.strip():
        raise BadRequest("Branch name is required.")
    if not 0 < data.max_hours_per_day <= 24:
        raise BadRequest("Max hours per day must be between 0 and 24.")
    if not 0 < data.max_hours_per_week <= 168:
        raise BadRequest("Max hours per week must be between 0 and 168.")
    if not 1 <= data.max_days_per_week <= 7:
        raise BadRequest("Max days per week must be between 1 and 7.")
    if not 0 <= data.min_rest_hours <= 24:
        raise BadRequest("Minimum rest must be between 0 and 24 hours.")
    if data.week_starts_on not in range(7):
        raise BadRequest("Week start must be 0 (Monday) to 6 (Sunday).")

    s = get_settings(db)
    s.branch_name = data.branch_name.strip()
    s.open_time, s.close_time = open_t, close_t
    s.max_hours_per_day = data.max_hours_per_day
    s.max_hours_per_week = data.max_hours_per_week
    s.max_days_per_week = data.max_days_per_week
    s.min_rest_hours = data.min_rest_hours
    s.operating_days = validate_days(data.operating_days, "opening days")
    s.week_starts_on = data.week_starts_on
    db.commit()
    return s
