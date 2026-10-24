"""HARD rules: if any of these fail, the person cannot be given the shift."""

from ..types import CheckContext
from .base import Constraint, Finding, Severity


def _h(x: float) -> str:
    """8.0 -> "8", 7.5 -> "7.5"."""
    return f"{x:g}"


class ActiveEmployee(Constraint):
    code = "active"
    severity = Severity.HARD
    description = "Only active employees can be scheduled."

    def check(self, ctx: CheckContext) -> Finding | None:
        if not ctx.staff.active:
            return self.fail("Not an active employee")
        return None


class RoleMatch(Constraint):
    code = "role"
    severity = Severity.HARD
    description = "The person's job role must match the shift's role."

    def check(self, ctx: CheckContext) -> Finding | None:
        if ctx.staff.role_id != ctx.shift.role_id:
            mine = ctx.staff.role_name or "no role"
            return self.fail(f"Different role ({mine})")
        return None


class OperatingDay(Constraint):
    code = "operating_day"
    severity = Severity.HARD
    description = "Shifts can only be on days the branch is open."

    def check(self, ctx: CheckContext) -> Finding | None:
        if ctx.shift.day.weekday() not in ctx.rules.operating_days:
            return self.fail("The branch is closed that day")
        return None


class WithinOpeningHours(Constraint):
    code = "opening_hours"
    severity = Severity.HARD
    description = "Shifts must start and end within opening hours."

    def check(self, ctx: CheckContext) -> Finding | None:
        tz = ctx.rules.tz
        start, end = ctx.shift.start.astimezone(tz), ctx.shift.end.astimezone(tz)
        if (
            start.date() != ctx.shift.day
            or end.date() != ctx.shift.day
            or start.time() < ctx.rules.open_time
            or end.time() > ctx.rules.close_time
            or end <= start
        ):
            return self.fail(
                f"Outside opening hours ({ctx.rules.open_time:%H:%M}–{ctx.rules.close_time:%H:%M})"
            )
        return None


class NotOnApprovedLeave(Constraint):
    code = "on_leave"
    severity = Severity.HARD
    description = "People on approved leave can't work that day."

    def check(self, ctx: CheckContext) -> Finding | None:
        for leave in ctx.staff.leave:
            if leave.status == "approved" and leave.covers(ctx.shift.day):
                return self.fail(f"On {leave.leave_type.lower()} leave")
        return None


class NoOverlap(Constraint):
    code = "overlap"
    severity = Severity.HARD
    description = "A person can't work two shifts at the same time."

    def check(self, ctx: CheckContext) -> Finding | None:
        tz = ctx.rules.tz
        for b in ctx.other_bookings:
            if b.start < ctx.shift.end and b.end > ctx.shift.start:
                s, e = b.start.astimezone(tz), b.end.astimezone(tz)
                return self.fail(f"Already working {s:%H:%M}–{e:%H:%M} that day")
        return None


class MaxHoursPerDay(Constraint):
    code = "max_hours_day"
    severity = Severity.HARD
    description = "Daily working-hour limit (Rules: max hours per day)."

    def check(self, ctx: CheckContext) -> Finding | None:
        total = ctx.hours_that_day + ctx.shift.hours
        if total > ctx.rules.max_hours_per_day + 1e-9:
            return self.fail(
                f"Would work {_h(total)}h that day (limit {_h(ctx.rules.max_hours_per_day)}h)"
            )
        return None


class MaxHoursPerWeek(Constraint):
    code = "max_hours_week"
    severity = Severity.HARD
    description = "Weekly working-hour limit (Rules: max hours per week, or the person's own limit)."

    def check(self, ctx: CheckContext) -> Finding | None:
        if ctx.hours_after > ctx.weekly_limit + 1e-9:
            return self.fail(
                f"Would reach {_h(ctx.hours_after)}h this week (limit {_h(ctx.weekly_limit)}h)"
            )
        return None


class MaxDaysPerWeek(Constraint):
    code = "max_days_week"
    severity = Severity.HARD
    description = "Most days one person may work in a week (Rules: max days per week)."

    def check(self, ctx: CheckContext) -> Finding | None:
        if ctx.days_after > ctx.rules.max_days_per_week:
            return self.fail(
                f"Would work {ctx.days_after} days this week (limit {ctx.rules.max_days_per_week})"
            )
        return None
