"""The scheduling engine: rules (constraints), roster generation and cover ranking.

Pure Python, no database. See constraints/__init__.py for how to add a new rule.
"""

from app.modules.scheduling.engine.constraints import Constraint, COVER, DEFAULT_CONSTRAINTS, evaluate, Evaluation, MANUAL, ROSTER
from app.modules.scheduling.engine.generator import Gap, generate_week, GenerationResult, PatternDemand, PlannedShift
from app.modules.scheduling.engine.ranking import check_person, rank_candidates, RankedCandidate, Unavailable
from app.modules.scheduling.engine.types import Booking, CheckContext, LeaveBlock, ProposedShift, Rules, StaffMember

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
