"""Plain data objects the scheduling engine works with.

The engine never touches the database. Services load data from the DB, turn it into
these objects, run the engine, and save the results. That keeps the rules easy to
read, easy to test, and easy to extend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.core.timeutil import hours_between, week_start


@dataclass(frozen=True)
class Rules:
    """The branch's adjustable working-time rules (stored in branch_settings)."""

    timezone: str = "Asia/Kuala_Lumpur"
    open_time: time = time(7, 0)
    close_time: time = time(22, 0)
    max_hours_per_day: float = 8
    max_hours_per_week: float = 40
    max_days_per_week: int = 6
    min_rest_hours: float = 10
    operating_days: frozenset[int] = frozenset(range(7))  # 0 = Monday ... 6 = Sunday
    week_starts_on: int = 0

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def week_of(self, day: date) -> tuple[date, date]:
        start = week_start(day, self.week_starts_on)
        return start, start + timedelta(days=6)


@dataclass(frozen=True)
class Booking:
    """A shift someone is already working (status "scheduled")."""

    day: date
    start: datetime
    end: datetime
    role_id: int
    shift_id: int | None = None

    @property
    def hours(self) -> float:
        return hours_between(self.start, self.end)


@dataclass(frozen=True)
class LeaveBlock:
    start_date: date
    end_date: date
    status: str  # "approved" | "pending"
    leave_type: str = "Leave"

    def covers(self, day: date) -> bool:
        return self.start_date <= day <= self.end_date


@dataclass
class StaffMember:
    """One employee as the engine sees them: who they are and what they're already doing."""

    id: int
    name: str
    role_id: int | None
    role_name: str | None = None
    active: bool = True
    max_hours_per_week: float | None = None  # personal limit; None = branch rule
    bookings: list[Booking] = field(default_factory=list)
    leave: list[LeaveBlock] = field(default_factory=list)
    recent_covers: int = 0
    # Free-form extra data for future rules, e.g. {"unavailable_weekdays": {6}}.
    attributes: dict[str, Any] = field(default_factory=dict)

    def weekly_limit(self, rules: Rules) -> float:
        return self.max_hours_per_week if self.max_hours_per_week is not None else rules.max_hours_per_week


@dataclass(frozen=True)
class ProposedShift:
    """A shift we're thinking of giving to someone."""

    day: date
    start: datetime
    end: datetime
    role_id: int
    role_name: str = ""
    # When editing / covering an existing shift, ignore that shift in the person's own bookings.
    ignore_shift_id: int | None = None

    @property
    def hours(self) -> float:
        return hours_between(self.start, self.end)


@dataclass
class CheckContext:
    """Everything a rule needs to judge "can this person take this shift?".
    The derived numbers (hours this week, rest gaps, ...) are computed here once,
    so every rule reads them the same way."""

    rules: Rules
    staff: StaffMember
    shift: ProposedShift
    now: datetime

    def __post_init__(self) -> None:
        ws, we = self.rules.week_of(self.shift.day)
        self.week_start, self.week_end = ws, we
        self.other_bookings = [
            b for b in self.staff.bookings if b.shift_id is None or b.shift_id != self.shift.ignore_shift_id
        ]
        self.week_bookings = [b for b in self.other_bookings if ws <= b.day <= we]
        self.day_bookings = [b for b in self.other_bookings if b.day == self.shift.day]

    # ---- weekly numbers
    @property
    def hours_this_week(self) -> float:
        return round(sum(b.hours for b in self.week_bookings), 2)

    @property
    def hours_worked_so_far(self) -> float:
        return round(sum(b.hours for b in self.week_bookings if b.end <= self.now), 2)

    @property
    def hours_after(self) -> float:
        return round(self.hours_this_week + self.shift.hours, 2)

    @property
    def weekly_limit(self) -> float:
        return self.staff.weekly_limit(self.rules)

    @property
    def days_this_week(self) -> int:
        return len({b.day for b in self.week_bookings})

    @property
    def days_after(self) -> int:
        return len({b.day for b in self.week_bookings} | {self.shift.day})

    # ---- daily numbers
    @property
    def hours_that_day(self) -> float:
        return round(sum(b.hours for b in self.day_bookings), 2)

    # ---- rest between shifts
    @property
    def previous_booking(self) -> Booking | None:
        before = [b for b in self.other_bookings if b.end <= self.shift.start]
        return max(before, key=lambda b: b.end, default=None)

    @property
    def next_booking(self) -> Booking | None:
        after = [b for b in self.other_bookings if b.start >= self.shift.end]
        return min(after, key=lambda b: b.start, default=None)

    @property
    def rest_before(self) -> float | None:
        prev = self.previous_booking
        return hours_between(prev.end, self.shift.start) if prev else None

    @property
    def rest_after(self) -> float | None:
        nxt = self.next_booking
        return hours_between(self.shift.end, nxt.start) if nxt else None
