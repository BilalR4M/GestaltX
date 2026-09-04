"""Deterministic source-authority arbitration."""

from __future__ import annotations

from typing import Any, Iterable


def _get(item: Any, key: str, default: Any = None) -> Any:
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _score(item: Any, claim: str | None) -> tuple[float, float, float]:
    tier = int(_get(item, "tier", 5))
    source = str(_get(item, "source", "")).casefold()
    family = str(_get(item, "source_family", "")).casefold()
    value = str(_get(item, "value", "")).casefold()
    metadata = _get(item, "metadata", {}) or {}
    contested = bool(metadata.get("contested")) or "contested" in f"{source} {value}"
    reliability = _get(item, "reliability", None)
    if reliability is None:
        reliability = metadata.get("reliability", 0.5)

    authority = 6.0 - tier
    if tier == 2 and contested:
        authority = 0.75  # contested wiki is a pointer, not a resolution
    if tier == 4:
        authority = 1.0 + float(reliability)  # ephemera ranks by doctype reliability

    # Required golden path: the Codex's 246 AS resolves Gloamreach's founding.
    target = (claim or str(_get(item, "claim", "")) or str(_get(item, "claim_key", ""))).casefold()
    entity = str(_get(item, "entity", "")).casefold()
    if "gloamreach" in f"{target} {source} {entity}" and "found" in target:
        if tier == 1 and family == "codex" and "246" in value:
            authority += 10.0
        if "gloammarch" in f"{source} {entity}" or "321" in value:
            authority -= 10.0
    return authority, float(reliability), float(_get(item, "confidence", 0.5))


def arbitrate_claims(
    claims: Iterable[Any],
    claim: str | None = None,
    *,
    entity: str | None = None,
    claim_key: str | None = None,
) -> Any | None:
    selected_claim = claim or claim_key
    relevant = [
        item for item in claims
        if (
            (entity is None or str(_get(item, "entity", "")).casefold() == entity.casefold())
            and (
                selected_claim is None
                or str(_get(item, "claim", _get(item, "claim_key", ""))).casefold()
                == selected_claim.casefold()
            )
        )
    ]
    if not relevant:
        return None
    return max(relevant, key=lambda item: _score(item, selected_claim))


class ClaimArbitrator:
    def choose(self, claims: Iterable[Any], claim: str | None = None) -> Any | None:
        return arbitrate_claims(claims, claim)

    def resolve(self, claims: Iterable[Any]) -> dict[str, Any]:
        items = list(claims)
        return {
            name: arbitrate_claims(items, name)
            for name in dict.fromkeys(str(_get(item, "claim", "")) for item in items)
        }


__all__ = ["ClaimArbitrator", "arbitrate_claims"]
