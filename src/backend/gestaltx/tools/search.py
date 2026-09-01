"""Corpus search tool."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from .base import Tool


def _plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return value
    if hasattr(value, "__dict__"):
        return vars(value)
    return value


class SearchCorpusTool(Tool):
    name = "search_corpus"
    description = "Hybrid full-text and semantic search over archive sections."

    def __init__(self, searcher: Any | None) -> None:
        self.searcher = searcher

    def run(
        self,
        query: str,
        *,
        top_k: int = 8,
        tier: int | None = None,
        tiers: list[int] | None = None,
        **filters: Any,
    ) -> list[dict[str, Any]]:
        if self.searcher is None:
            return []
        allowed = tiers or ([tier] if tier is not None else None)
        attempts = (
            {"query": query, "top_k": top_k, "tiers": allowed, **filters},
            {"query": query, "k": top_k, "tier": tier, **filters},
            {"query": query, "top_k": top_k},
        )
        last_error: TypeError | None = None
        for kwargs in attempts:
            try:
                result = self.searcher.search(**{k: v for k, v in kwargs.items() if v is not None})
                rows = result.get("results", []) if isinstance(result, dict) else result
                plain = [_plain(row) for row in (rows or [])]
                if allowed:
                    plain = [row for row in plain if not isinstance(row, dict) or row.get("tier") in allowed]
                return plain[:top_k]
            except TypeError as exc:
                last_error = exc
        if last_error:
            raise last_error
        return []


__all__ = ["SearchCorpusTool"]
