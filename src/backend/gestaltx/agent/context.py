"""Scratchpad compaction helpers."""

from __future__ import annotations

from .arbitration import arbitrate_claims
from .scratchpad import Scratchpad


def compact_scratchpad(scratchpad: Scratchpad, token_budget: int = 3500) -> str:
    """Render within an approximate token budget while retaining best evidence."""
    max_chars = max(200, token_budget * 4)
    context = scratchpad.to_context()
    if len(context) <= max_chars:
        return context

    winners = []
    for claim_name in dict.fromkeys(item.claim for item in scratchpad.claims):
        winner = arbitrate_claims(scratchpad.claims, claim=claim_name)
        if winner is not None:
            winners.append(winner)
    compact = Scratchpad(
        claims=winners,
        open_questions=scratchpad.open_questions,
        entities=scratchpad.entities,
        intent=scratchpad.intent,
    ).to_context()
    return compact[: max_chars - 1] + "…" if len(compact) > max_chars else compact


__all__ = ["compact_scratchpad"]
