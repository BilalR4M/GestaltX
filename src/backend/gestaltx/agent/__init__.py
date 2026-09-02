"""GestaltX research agent."""

from .arbitration import ClaimArbitrator, arbitrate_claims
from .gap_critic import Critique, GapCritic
from .loop import ResearchLoop
from .planner import Planner, ResearchPlan
from .scratchpad import ClaimRecord, Scratchpad
from .synthesize import synthesize_answer

__all__ = [
    "ClaimArbitrator",
    "ClaimRecord",
    "Critique",
    "GapCritic",
    "Planner",
    "ResearchLoop",
    "ResearchPlan",
    "Scratchpad",
    "arbitrate_claims",
    "synthesize_answer",
]
