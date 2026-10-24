"""Where leave records come from.

All leave enters the system through ONE function, `services.leave.ingest_leave_records`,
whether it was typed in by the manager, uploaded as a CSV export from Orbyte, or (later)
pulled live from Orbyte. That way de-duplication, cover-case opening and notifications
behave identically for every source.

To connect Orbyte live once the access method is known (API or database read):
  1. Implement `OrbyteLeaveSource.fetch()` to return LeaveRecord objects
     (use `external_ref` = Orbyte's leave id so re-syncs don't create duplicates).
  2. Set ORBYTE_ENABLED=1 (plus whatever credentials it needs, stored as secrets).
  3. Call `sync_from(source)` on a schedule (e.g. every 15 minutes).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class LeaveRecord:
    leave_type: str
    start_date: date
    end_date: date
    status: str = "approved"  # approved | pending
    employee_email: str | None = None
    orbyte_id: str | None = None
    external_ref: str | None = None
    reason: str | None = None


class LeaveSource(Protocol):
    name: str  # stored on each leave row as its "source"

    def fetch(self, since: datetime | None) -> list[LeaveRecord]: ...


class OrbyteLeaveSource:
    """Placeholder for a live Orbyte eLeave connection."""

    name = "orbyte"

    def fetch(self, since: datetime | None) -> list[LeaveRecord]:
        raise NotImplementedError(
            "Orbyte access has not been set up yet. Import Orbyte CSV exports on the Leave page instead."
        )


def orbyte_connected() -> bool:
    return os.environ.get("ORBYTE_ENABLED") == "1"


_DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y")


def parse_date(value: str) -> date:
    """Accepts 2026-10-20, 20/10/2026, 20-10-2026, 20 Oct 2026."""
    text = (value or "").strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f'"{value}" is not a date (use YYYY-MM-DD or DD/MM/YYYY)')


def normalise_status(value: str | None) -> str:
    """Orbyte exports say things like "Approved", "Pending Approval", "Rejected"."""
    v = (value or "approved").strip().lower()
    if v.startswith("approv"):
        return "approved"
    if v.startswith("pend") or v in ("submitted", "applied"):
        return "pending"
    if v.startswith("reject") or v.startswith("cancel") or v.startswith("withdr"):
        return "rejected"
    raise ValueError(f'Unknown leave status "{value}"')
