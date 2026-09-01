"""Qdrant local-path vector index."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from gestaltx.ingest.models import Chunk

from .embeddings import Embedder


def _payload(chunk: Chunk | dict[str, Any]) -> dict[str, Any]:
    if isinstance(chunk, dict):
        return dict(chunk)
    if hasattr(chunk, "model_dump"):
        return chunk.model_dump(mode="json")
    return chunk.dict()


class VectorIndex:
    def __init__(
        self,
        path: str | Path,
        collection_name: str = "ashen_chunks",
        embedder: Embedder | None = None,
    ) -> None:
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:  # pragma: no cover - dependency error
            raise RuntimeError("Vector indexing requires the 'qdrant-client' package") from exc
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.embedder = embedder or Embedder()
        self.client = QdrantClient(path=str(self.path))

    def _ensure_collection(self, dimension: int) -> None:
        from qdrant_client.models import Distance, VectorParams

        existing = {
            item.name for item in self.client.get_collections().collections
        }
        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE),
            )

    def close(self) -> None:
        close = getattr(self.client, "close", None)
        if close:
            close()

    def add(self, chunks: Iterable[Chunk | dict[str, Any]]) -> int:
        from qdrant_client.models import PointStruct

        payloads = [_payload(chunk) for chunk in chunks]
        if not payloads:
            return 0
        vectors = self.embedder.embed_documents(item.get("text", "") for item in payloads)
        self._ensure_collection(int(vectors.shape[1]))
        points = [
            PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"gestaltx:{item['chunk_id']}")),
                vector=vector.tolist(),
                payload=item,
            )
            for item, vector in zip(payloads, vectors)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        return len(points)

    index = add

    def clear(self) -> None:
        existing = {
            item.name for item in self.client.get_collections().collections
        }
        if self.collection_name in existing:
            self.client.delete_collection(self.collection_name)

    @staticmethod
    def _filter(
        tier: int | Iterable[int] | None,
        doctype: str | Iterable[str] | None,
        entity: str | None,
    ) -> Any:
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        conditions = []
        for key, value in (("tier", tier), ("doctype", doctype)):
            if value is None:
                continue
            if isinstance(value, (list, tuple, set, frozenset)):
                conditions.append(FieldCondition(key=key, match=MatchAny(any=list(value))))
            else:
                conditions.append(FieldCondition(key=key, match=MatchValue(value=value)))
        if entity:
            conditions.append(
                FieldCondition(key="entities", match=MatchValue(value=entity))
            )
        return Filter(must=conditions) if conditions else None

    def search(
        self,
        query: str,
        limit: int = 10,
        *,
        tier: int | Iterable[int] | None = None,
        doctype: str | Iterable[str] | None = None,
        entity: str | None = None,
    ) -> list[dict[str, Any]]:
        if not query.strip() or limit < 1:
            return []
        existing = {
            item.name for item in self.client.get_collections().collections
        }
        if self.collection_name not in existing:
            return []
        vector = self.embedder.embed_query(query).tolist()
        query_filter = self._filter(tier, doctype, entity)
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
            points = response.points
        else:  # compatibility with older qdrant-client
            points = self.client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            )
        results = []
        for point in points:
            item = dict(point.payload or {})
            item["score"] = float(point.score)
            results.append(item)
        return results


QdrantVectorIndex = VectorIndex

__all__ = ["QdrantVectorIndex", "VectorIndex"]
