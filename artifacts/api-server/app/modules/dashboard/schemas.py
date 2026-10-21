"""Desk (dashboard) shapes."""

from __future__ import annotations

from datetime import datetime

from app.core.schema import Model


class DashboardSummary(Model):
    open_cases: int
    offered_cases: int
    urgent_cases: int
    filled_this_week: int
    pending_offers: int
    pending_leave: int
    on_leave_today: int
    staff_count: int
    shifts_this_week: int
    roster_gaps_this_week: int


class Activity(Model):
    id: int
    kind: str
    message: str
    created_at: datetime
