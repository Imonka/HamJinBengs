"""The list of rules the scheduler enforces, and the function that runs them.

HOW TO ADD A NEW RULE (example: "this person can never work on Sundays")
-----------------------------------------------------------------------
1. Store the data. E.g. add an `unavailable_weekdays` column (or table) for employees,
   and copy it into `StaffMember.attributes["unavailable_weekdays"]` in
   app/services/staffing.py (the one place that loads people for the engine).
2. Write the rule in hard.py (cannot work) or soft.py (allowed, but warn):

       class UnavailableWeekday(Constraint):
           code = "unavailable_weekday"
           severity = Severity.HARD
           description = "Days the person can never work."

           def check(self, ctx):
               if ctx.shift.day.weekday() in ctx.staff.attributes.get("unavailable_weekdays", ()):
                   return self.fail("Never works on this day")
               return None

3. Add an instance to DEFAULT_CONSTRAINTS below.

That's it: the roster generator, cover suggestions, offer acceptance and manual shift
checks all use this same list, so the new rule applies everywhere automatically.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..types import CheckContext
from .base import ALL_PURPOSES, COVER, MANUAL, ROSTER, Constraint, Finding, Severity
from .hard import (
    ActiveEmployee,
    MaxDaysPerWeek,
    MaxHoursPerDay,
    MaxHoursPerWeek,
    NoOverlap,
    NotOnApprovedLeave,
    OperatingDay,
    RoleMatch,
    WithinOpeningHours,
)
from .soft import BackToBack, PendingLeave, RecentCoverLoad

DEFAULT_CONSTRAINTS: list[Constraint] = [
    # hard
    ActiveEmployee(),
    RoleMatch(),
    OperatingDay(),
    WithinOpeningHours(),
    NotOnApprovedLeave(),
    NoOverlap(),
    MaxHoursPerDay(),
    MaxHoursPerWeek(),
    MaxDaysPerWeek(),
    # soft
    BackToBack(),
    PendingLeave(),
    RecentCoverLoad(),
]


@dataclass
class Evaluation:
    findings: list[Finding] = field(default_factory=list)

    @property
    def hard(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.HARD]

    @property
    def soft(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.SOFT]

    @property
    def ok(self) -> bool:
        return not self.hard

    @property
    def penalty(self) -> int:
        return sum(f.penalty for f in self.soft)

    def has(self, code: str) -> bool:
        return any(f.code == code for f in self.findings)


def evaluate(
    ctx: CheckContext,
    purpose: str,
    constraints: list[Constraint] | None = None,
) -> Evaluation:
    """Run every rule that applies to `purpose` (ROSTER / COVER / MANUAL)."""
    result = Evaluation()
    for rule in constraints if constraints is not None else DEFAULT_CONSTRAINTS:
        if purpose not in rule.purposes:
            continue
        finding = rule.check(ctx)
        if finding is not None:
            result.findings.append(finding)
    return result


__all__ = [
    "ALL_PURPOSES",
    "COVER",
    "DEFAULT_CONSTRAINTS",
    "MANUAL",
    "ROSTER",
    "Constraint",
    "Evaluation",
    "Finding",
    "Severity",
    "evaluate",
]
