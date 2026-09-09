"""GestaltX research agent."""

from .arbitration import ClaimArbitrator, arbitrate_claims
from .evidence import DocumentFinding, RetrievalLog, build_dossier
from .gap_critic import Critique, GapCritic
from .loop import ResearchLoop
from .narrate import ResearchNarrator
from .planner import Planner, ResearchPlan
from .scratchpad import ClaimRecord, Scratchpad
from .synthesize import synthesize_answer
from .voice import prose_for_voice_check, violations

__all__ = [
    "ClaimArbitrator",
    "ClaimRecord",
    "Critique",
    "DocumentFinding",
    "GapCritic",
    "Planner",
    "ResearchLoop",
    "ResearchNarrator",
    "ResearchPlan",
    "RetrievalLog",
    "Scratchpad",
    "arbitrate_claims",
    "build_dossier",
    "prose_for_voice_check",
    "synthesize_answer",
    "violations",
]
