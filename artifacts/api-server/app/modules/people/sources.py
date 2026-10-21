"""Where the staff list comes from.

Today people are added in the app (Team page), by CSV import or by the CLI. All of those go
through `service.add_employee()`. The plan is for Orbyte to own the directory later. When that
happens:

1. Fill in `OrbytePeopleSource.fetch()` to call Orbyte's API and return `PersonRecord`s.
2. Add a sync job that, for each record, finds the person by `orbyte_id` and updates their
   name, email, phone, role and active flag (or calls `add_employee` for new people).
3. Make the Orbyte-owned fields read-only on the Team page.

Nothing outside the people module needs to change: other modules only use people through
`Employee` rows, `employee_ref()` and the functions in `service.py`.
"""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PersonRecord:
    """One person as an outside system describes them."""

    orbyte_id: str
    name: str
    email: str
    phone: str | None = None
    role_name: str | None = None
    active: bool = True


class PeopleSource(Protocol):
    def fetch(self) -> list[PersonRecord]: ...


class OrbytePeopleSource:
    """Placeholder for the live Orbyte staff directory."""

    def fetch(self) -> list[PersonRecord]:
        raise NotImplementedError("The Orbyte staff directory is not connected yet. Use the Team page or CSV import.")

