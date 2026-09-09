"""Reciprocal-rank fusion over lexical and optional dense retrieval."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


class HybridSearcher:
    def __init__(
        self,
        fts_index: Any,
        vector_index: Any | None = None,
        *,
        fts_weight: float = 0.45,
        dense_weight: float = 0.55,
        rrf_k: int = 60,
    ) -> None:
        if fts_index is None:
            raise ValueError("fts_index is required")
        if vector_index is None:
            fts_weight, dense_weight = 1.0, 0.0
        if fts_weight < 0 or dense_weight < 0 or not (fts_weight + dense_weight):
            raise ValueError("At least one search weight must be positive")
        self.fts_index = fts_index
        self.vector_index = vector_index
        self.fts_weight = fts_weight
        self.dense_weight = dense_weight
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        limit: int = 10,
        *,
        tier: int | Iterable[int] | None = None,
        doctype: str | Iterable[str] | None = None,
        entity: str | None = None,
        candidate_multiplier: int = 4,
    ) -> list[dict[str, Any]]:
        """Retrieve from available indexes and combine rankings with weighted RRF."""
        if limit < 1:
            return []
        candidate_limit = max(limit, limit * candidate_multiplier)
        filters = {"tier": tier, "doctype": doctype, "entity": entity}
        lexical = self.fts_index.search(query, candidate_limit, **filters)
        dense: list[dict[str, Any]] = []
        if self.vector_index is not None and self.dense_weight > 0:
            try:
                dense = self.vector_index.search(query, candidate_limit, **filters)
            except Exception:
                dense = []

        if not dense:
            return lexical[:limit]

        fused: dict[str, dict[str, Any]] = {}
        for source, weight, results in (
            ("fts", self.fts_weight, lexical),
            ("dense", self.dense_weight, dense),
        ):
            for rank, result in enumerate(results, start=1):
                chunk_id = str(result["chunk_id"])
                record = fused.setdefault(
                    chunk_id,
                    {
                        **result,
                        "score": 0.0,
                        "retrieval": {},
                    },
                )
                record["score"] += weight / (self.rrf_k + rank)
                record["retrieval"][source] = {
                    "rank": rank,
                    "score": result.get("score"),
                }

        ranked = sorted(
            fused.values(),
            key=lambda item: (-float(item["score"]), str(item["chunk_id"])),
        )
        return ranked[:limit]


__all__ = ["HybridSearcher"]
