"""Near-name detection for potentially confused entities."""

from __future__ import annotations

import difflib
import re
from collections.abc import Iterable


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def name_similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(left), _normalize(right)).ratio()


def near_names(
    name: str,
    candidates: Iterable[str],
    *,
    cutoff: float = 0.72,
    limit: int = 5,
) -> list[str]:
    """Return suspiciously similar names, most similar first."""
    normalized = _normalize(name)
    scored = [
        (name_similarity(name, candidate), candidate)
        for candidate in candidates
        if _normalize(candidate) != normalized
    ]
    return [
        candidate
        for score, candidate in sorted(scored, key=lambda item: (-item[0], item[1]))
        if score >= cutoff
    ][:limit]


def find_near_name_pairs(
    names: Iterable[str], *, cutoff: float = 0.72
) -> list[tuple[str, str, float]]:
    unique = list(dict.fromkeys(name for name in names if name.strip()))
    pairs = []
    for index, left in enumerate(unique):
        for right in unique[index + 1 :]:
            similarity = name_similarity(left, right)
            if _normalize(left) != _normalize(right) and similarity >= cutoff:
                pairs.append((left, right, similarity))
    return sorted(pairs, key=lambda item: (-item[2], item[0], item[1]))


__all__ = ["find_near_name_pairs", "name_similarity", "near_names"]
