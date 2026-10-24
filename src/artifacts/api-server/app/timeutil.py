"""Time helpers. The branch works in local time (Asia/Kuala_Lumpur by default);
the database stores timezone-aware timestamps."""

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def now_utc() -> datetime:
    return datetime.now(UTC)


def local_today(tz: ZoneInfo) -> date:
    return datetime.now(tz).date()


def at(day: date, t: time, tz: ZoneInfo) -> datetime:
    """Branch-local date + time -> aware datetime."""
    return datetime.combine(day, t, tzinfo=tz)


def to_local(dt: datetime, tz: ZoneInfo) -> datetime:
    return dt.astimezone(tz)


def hours_between(start: datetime, end: datetime) -> float:
    return round((end - start).total_seconds() / 3600, 2)


def parse_hhmm(value: str) -> time:
    try:
        hh, mm = value.strip().split(":")
        return time(int(hh), int(mm))
    except (ValueError, AttributeError) as exc:
        raise ValueError(f'"{value}" is not a valid time; use HH:MM') from exc


def fmt_hhmm(t: time) -> str:
    return t.strftime("%H:%M")


def fmt_day(day: date) -> str:
    return f"{WEEKDAY_NAMES[day.weekday()]}, {day.day} {day.strftime('%b')}"


def fmt_window(start: datetime, end: datetime, tz: ZoneInfo) -> str:
    s, e = to_local(start, tz), to_local(end, tz)
    return f"{fmt_day(s.date())}, {s:%H:%M}–{e:%H:%M}"


def week_start(day: date, week_starts_on: int) -> date:
    return day - timedelta(days=(day.weekday() - week_starts_on) % 7)


def date_range(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)
