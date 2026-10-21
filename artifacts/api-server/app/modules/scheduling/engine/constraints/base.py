"""The building block for every scheduling rule.

A rule ("constraint") looks at a CheckContext and either says nothing (OK) or returns
a Finding. HARD findings mean the person cannot take the shift. SOFT findings are
allowed but shown to the manager as warnings and lower the person's score.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from app.modules.scheduling.engine.types import CheckContext


class Severity(str, Enum):
    HARD = "hard"
    SOFT = "soft"


# Where a rule is used. Most rules apply everywhere; some only make sense in one place
# (e.g. "has covered a lot recently" matters when picking cover, not when building a roster).
ROSTER = "roster"  # automatic weekly roster generation
COVER = "cover"  # ranking replacements / accepting a cover offer
MANUAL = "manual"  # the manager adding or editing a shift by hand
ALL_PURPOSES = frozenset({ROSTER, COVER, MANUAL})


@dataclass(frozen=True)
class Finding:
    code: str
    severity: Severity
    message: str
    penalty: int = 0  # how much a SOFT finding lowers the candidate score


class Constraint(ABC):
    """Subclass this to add a rule. Fill in `code`, `severity`, `description`, then `check()`."""

    code: ClassVar[str]
    severity: ClassVar[Severity]
    description: ClassVar[str]
    purposes: ClassVar[frozenset[str]] = ALL_PURPOSES

    @abstractmethod
    def check(self, ctx: CheckContext) -> Finding | None: ...

    # helpers so subclasses read nicely
    def fail(self, message: str, penalty: int = 0) -> Finding:
        return Finding(self.code, self.severity, message, penalty)
