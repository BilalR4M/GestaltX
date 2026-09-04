"""Claim comparison tool."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from gestaltx.agent.arbitration import arbitrate_claims

from .base import Tool


class CompareClaimsTool(Tool):
    name = "compare_claims"
    description = "Group conflicting claim values and select the authoritative evidence."

    def run(self, claims: list[Any], claim: str | None = None) -> dict[str, Any]:
        relevant = [
            item for item in claims
            if claim is None or _get(item, "claim", "").casefold() == claim.casefold()
        ]
        grouped: dict[str, list[Any]] = defaultdict(list)
        for item in relevant:
            grouped[str(_get(item, "value", ""))].append(item)
        winner = arbitrate_claims(relevant, claim=claim)
        return {
            "claim": claim,
            "values": {value: [_serialize(item) for item in items] for value, items in grouped.items()},
            "winner": _serialize(winner) if winner is not None else None,
            "contested": len(grouped) > 1,
        }


def _get(item: Any, key: str, default: Any = None) -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _serialize(item: Any) -> Any:
    return item.model_dump() if hasattr(item, "model_dump") else item


__all__ = ["CompareClaimsTool"]
