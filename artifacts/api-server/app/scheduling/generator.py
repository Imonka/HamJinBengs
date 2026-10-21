"""Automatic weekly roster.

Input:  the rules, the shift patterns (how many of each role each pattern needs on which
        days), the staff (with what they're already booked for), and how many places
        are already filled.
Output: a list of planned shifts plus any gaps that could not be filled (with the reason).

Method (greedy, fair, explainable):
  for every open day of the week, earliest pattern first, for every role in the pattern,
  for every empty place:
      * ask every person with that role "can you take this?" using the SAME rule list
        used everywhere else (hard rules must pass)
      * among those who can, pick the one with
            1. no warnings first (e.g. not back-to-back),
            2. the lowest share of their weekly limit used so far (spreads hours fairly,
               and part-timers fill up proportionally),
            3. fewest days this week,
            4. a rotating tie-breaker so the same person isn't always first.
      * book them in memory, so the next decision sees it.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from ..timeutil import at
from .constraints import ROSTER, Constraint, evaluate
from .types import Booking, CheckContext, ProposedShift, Rules, StaffMember


@dataclass(frozen=True)
class PatternDemand:
    """'Pattern X needs `headcount` people of role Y on these weekdays.'"""

    pattern_id: int
    pattern_name: str
    start_time: time
    end_time: time
    days: frozenset[int]
    role_id: int
    role_name: str
    headcount: int


@dataclass(frozen=True)
class PlannedShift:
    staff_id: int
    pattern_id: int
    role_id: int
    day: date
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Gap:
    day: date
    pattern_name: str
    role_name: str
    missing: int
    reason: str


@dataclass
class GenerationResult:
    planned: list[PlannedShift] = field(default_factory=list)
    gaps: list[Gap] = field(default_factory=list)


SlotKey = tuple[date, int, int]  # (day, pattern_id, role_id)

_REASON_LABELS = {
    "on_leave": "on leave",
    "overlap": "already working",
    "max_hours_day": "at the daily hour limit",
    "max_hours_week": "at the weekly hour limit",
    "max_days_week": "at the days-per-week limit",
    "opening_hours": "outside opening hours",
    "operating_day": "branch closed",
    "active": "inactive",
    "role": "different role",
}


def _explain(role_name: str, first_findings: list[str]) -> str:
    counts = Counter(first_findings)
    parts = [f"{n} {_REASON_LABELS.get(code, code)}" for code, n in counts.most_common()]
    return f"No {role_name} free: " + ", ".join(parts)


def generate_week(
    rules: Rules,
    week_start: date,
    demands: list[PatternDemand],
    staff: list[StaffMember],
    already_filled: Mapping[SlotKey, int],
    now: datetime,
    constraints: list[Constraint] | None = None,
    include_past: bool = False,
) -> GenerationResult:
    """Plan one week. NOTE: appends planned bookings to the given StaffMember objects."""
    result = GenerationResult()
    tz = rules.tz
    ordered = sorted(demands, key=lambda d: (d.start_time, d.pattern_id, d.role_name))

    for offset in range(7):
        day = week_start + timedelta(days=offset)
        if day.weekday() not in rules.operating_days:
            continue
        for demand in ordered:
            if day.weekday() not in demand.days or demand.headcount <= 0:
                continue
            start, end = at(day, demand.start_time, tz), at(day, demand.end_time, tz)
            if not include_past and start <= now:
                continue
            needed = demand.headcount - already_filled.get((day, demand.pattern_id, demand.role_id), 0)
            proposed = ProposedShift(day, start, end, demand.role_id, demand.role_name)
            pool = [s for s in staff if s.role_id == demand.role_id]

            for filled in range(max(0, needed)):
                best: tuple[tuple, StaffMember] | None = None
                first_findings: list[str] = []
                for person in pool:
                    ctx = CheckContext(rules, person, proposed, now)
                    ev = evaluate(ctx, ROSTER, constraints)
                    if not ev.ok:
                        first_findings.append(ev.hard[0].code)
                        continue
                    key = (
                        ev.penalty,
                        ctx.hours_this_week / max(ctx.weekly_limit, 1),
                        ctx.days_this_week,
                        (day.toordinal() * 7919 + person.id * 104729) % 1009,
                    )
                    if best is None or key < best[0]:
                        best = (key, person)

                if best is None:
                    reason = (
                        _explain(demand.role_name, first_findings)
                        if pool
                        else f"Nobody on the team has the {demand.role_name} role"
                    )
                    result.gaps.append(
                        Gap(day, demand.pattern_name, demand.role_name, needed - filled, reason)
                    )
                    break

                person = best[1]
                person.bookings.append(Booking(day, start, end, demand.role_id))
                result.planned.append(
                    PlannedShift(person.id, demand.pattern_id, demand.role_id, day, start, end)
                )
    return result
