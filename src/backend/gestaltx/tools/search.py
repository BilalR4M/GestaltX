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
        limit: int | None = None,
        tier: int | list[int] | None = None,
        tiers: list[int] | None = None,
        doctype: str | None = None,
        entity: str | None = None,
        **_ignored: Any,
    ) -> list[dict[str, Any]]:
        if self.searcher is None:
            return []
        k = limit or top_k
        allowed = tiers if tiers is not None else tier
        result = self.searcher.search(
            query,
            limit=k,
            tier=allowed,
            doctype=doctype,
            entity=entity,
        )
        rows = result.get("results", []) if isinstance(result, dict) else result
        plain = [_plain(row) for row in (rows or [])]
        if isinstance(allowed, list):
            plain = [
                row
                for row in plain
                if not isinstance(row, dict) or row.get("tier") in allowed
            ]
        elif isinstance(allowed, int):
            plain = [
                row
                for row in plain
                if not isinstance(row, dict) or row.get("tier") == allowed
            ]
        return plain[:k]


__all__ = ["SearchCorpusTool"]
