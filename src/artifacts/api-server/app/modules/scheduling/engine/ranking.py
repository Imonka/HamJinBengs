"""Who could replace someone on leave, best first.

Every person is checked against the same rule list as the roster generator:
  * anyone failing a HARD rule goes to `unavailable` with the reasons
    (on leave, already working, over the weekly hours, wrong role, ...)
  * everyone else is `eligible` and gets a 0-100 score:
        100
        - up to 40 points for how full their week would be (hours after / weekly limit)
        - penalties from SOFT rules (back-to-back -25, pending leave -20, recent covers -5 each)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.modules.scheduling.engine.constraints import Constraint, COVER, evaluate
from app.modules.scheduling.engine.types import CheckContext, ProposedShift, Rules, StaffMember


@dataclass
class RankedCandidate:
    staff: StaffMember
    score: int
    hours_worked_so_far: float
    hours_this_week: float
    hours_after: float
    weekly_limit: float
    hours_that_day: float
    days_this_week: int
    back_to_back: bool
    rest_before: float | None
    rest_after: float | None
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class Unavailable:
    staff: StaffMember
    reasons: list[str]


def _h(x: float) -> str:
    return f"{x:g}"


def check_person(
    rules: Rules,
    shift: ProposedShift,
    person: StaffMember,
    now: datetime,
    constraints: list[Constraint] | None = None,
) -> tuple[CheckContext, list[str], RankedCandidate | None]:
    """Check one person. Returns (context, hard-rule reasons, ranked candidate or None)."""
    ctx = CheckContext(rules, person, shift, now)
    ev = evaluate(ctx, COVER, constraints)
    if not ev.ok:
        return ctx, [f.message for f in ev.hard], None

    load = ctx.hours_after / max(ctx.weekly_limit, 1)
    score = 100 - round(40 * load) - ev.penalty

    reasons = [f"Same role: {shift.role_name}" if shift.role_name else "Same role", "Free for the whole shift"]
    if load <= 0.6:
        reasons.append(f"Light week: {_h(ctx.hours_this_week)}h of {_h(ctx.weekly_limit)}h")
    if ctx.rest_before is None or ctx.rest_before >= 24:
        reasons.append("Well rested")
    if person.recent_covers == 0:
        reasons.append("Hasn't covered a shift in 30 days")

    warnings = [f.message for f in ev.soft]
    if load > 0.9:
        warnings.append(f"Near weekly limit ({_h(ctx.hours_after)}h of {_h(ctx.weekly_limit)}h)")

    candidate = RankedCandidate(
        staff=person,
        score=max(0, min(100, score)),
        hours_worked_so_far=ctx.hours_worked_so_far,
        hours_this_week=ctx.hours_this_week,
        hours_after=ctx.hours_after,
        weekly_limit=ctx.weekly_limit,
        hours_that_day=ctx.hours_that_day,
        days_this_week=ctx.days_this_week,
        back_to_back=ev.has("back_to_back"),
        rest_before=ctx.rest_before,
        rest_after=ctx.rest_after,
        reasons=reasons,
        warnings=warnings,
    )
    return ctx, [], candidate


def rank_candidates(
    rules: Rules,
    shift: ProposedShift,
    pool: list[StaffMember],
    now: datetime,
    constraints: list[Constraint] | None = None,
) -> tuple[list[RankedCandidate], list[Unavailable]]:
    eligible: list[RankedCandidate] = []
    unavailable: list[Unavailable] = []
    for person in pool:
        _, blocked, candidate = check_person(rules, shift, person, now, constraints)
        if candidate is None:
            unavailable.append(Unavailable(person, blocked))
        else:
            eligible.append(candidate)
    eligible.sort(key=lambda c: (-c.score, c.hours_this_week, c.staff.name))
    unavailable.sort(key=lambda u: u.staff.name)
    return eligible, unavailable
