"""SOFT rules: allowed, but the manager is warned and the person ranks lower."""

from app.modules.scheduling.engine.constraints.base import Constraint, COVER, Finding, Severity
from app.modules.scheduling.engine.types import CheckContext


def _h(x: float) -> str:
    return f"{x:g}"


class BackToBack(Constraint):
    code = "back_to_back"
    severity = Severity.SOFT
    description = "Less rest than the minimum between two shifts (Rules: min rest hours)."

    def check(self, ctx: CheckContext) -> Finding | None:
        limit = ctx.rules.min_rest_hours
        before, after = ctx.rest_before, ctx.rest_after
        parts = []
        if before is not None and before < limit:
            parts.append("straight after another shift" if before == 0 else f"only {_h(before)}h after their last shift")
        if after is not None and after < limit:
            parts.append("straight into another shift" if after == 0 else f"only {_h(after)}h before their next shift")
        if parts:
            return self.fail("Back-to-back: " + " and ".join(parts), penalty=25)
        return None


class PendingLeave(Constraint):
    code = "pending_leave"
    severity = Severity.SOFT
    description = "The person has asked for leave that day (not yet approved)."

    def check(self, ctx: CheckContext) -> Finding | None:
        for leave in ctx.staff.leave:
            if leave.status == "pending" and leave.covers(ctx.shift.day):
                return self.fail("Has a pending leave request for that day", penalty=20)
        return None


class RecentCoverLoad(Constraint):
    code = "recent_covers"
    severity = Severity.SOFT
    description = "Spread cover work fairly: people who covered recently rank lower."
    purposes = frozenset({COVER})

    def check(self, ctx: CheckContext) -> Finding | None:
        n = ctx.staff.recent_covers
        if n > 0:
            return self.fail(
                f"Covered {n} shift{'s' if n != 1 else ''} in the last 30 days", penalty=min(15, 5 * n)
            )
        return None

