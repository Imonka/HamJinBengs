"""Notification shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.core.schema import Model


class Notification(Model):
    id: int
    recipient_employee_id: int | None
    recipient_name: str
    recipient_email: str
    audience: Literal["offered", "replacement", "original", "team", "manager"]
    kind: str
    subject: str
    body: str
    email_status: Literal["queued", "sent", "failed"]
    read_at: datetime | None
    case_id: int | None
    offer_id: int | None
    created_at: datetime
