"""The scheduling engine: rules (constraints), roster generation and cover ranking.

Pure Python, no database. See constraints/__init__.py for how to add a new rule.
"""

from .constraints import COVER, DEFAULT_CONSTRAINTS, MANUAL, ROSTER, Constraint, Evaluation, evaluate
from .generator import Gap, GenerationResult, PatternDemand, PlannedShift, generate_week
from .ranking import RankedCandidate, Unavailable, check_person, rank_candidates
from .types import Booking, CheckContext, LeaveBlock, ProposedShift, Rules, StaffMember

__all__ = [
    "COVER",
    "DEFAULT_CONSTRAINTS",
    "MANUAL",
    "ROSTER",
    "Booking",
    "CheckContext",
    "Constraint",
    "Evaluation",
    "Gap",
    "GenerationResult",
    "LeaveBlock",
    "PatternDemand",
    "PlannedShift",
    "ProposedShift",
    "RankedCandidate",
    "Rules",
    "StaffMember",
    "Unavailable",
    "check_person",
    "evaluate",
    "generate_week",
    "rank_candidates",
]
