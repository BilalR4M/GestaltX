"""End-to-end index build: ingest (if needed) + FTS + vectors + entity graph."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gestaltx.config import GestaltConfig, load_config
from gestaltx.graph.builder import EntityGraph
from gestaltx.index.embeddings import Embedder
from gestaltx.index.fts import FTSIndex
from gestaltx.index.vector import VectorIndex
from gestaltx.ingest.models import Chunk, Document
from gestaltx.ingest.pipeline import ingest_corpus


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_indexes(config: GestaltConfig | None = None, *, force: bool = False) -> dict[str, Any]:
    """Build or refresh lexical, dense, and graph indexes."""
    cfg = config or load_config()
    processed = Path(cfg.app.processed_dir)
    processed.mkdir(parents=True, exist_ok=True)

    docs_path = Path(cfg.app.documents_jsonl)
    chunks_path = Path(cfg.app.chunks_jsonl)
    corpus = Path(cfg.app.corpus_dir)

    if force or not docs_path.exists() or not chunks_path.exists():
        if not corpus.exists():
            raise FileNotFoundError(
                f"Corpus not found at {corpus}. Place Ashen_Era_Archive under data/raw/."
            )
        ingest_corpus(corpus, config=cfg)

    documents = [Document.model_validate(row) for row in _load_jsonl(docs_path)]
    chunks = [Chunk.model_validate(row) for row in _load_jsonl(chunks_path)]

    fts_path = Path(cfg.index.fts_path)
    if force and fts_path.exists():
        fts_path.unlink()
    fts = FTSIndex(fts_path)
    if force:
        fts.clear()
    fts.add(chunks)

    embedder = Embedder(cfg.index.embedding_model)
    vector = VectorIndex(
        path=cfg.index.qdrant_path,
        collection_name=cfg.index.collection_name,
        embedder=embedder,
    )
    if force:
        vector.clear()
    vector.add(chunks)

    graph = EntityGraph().build(documents)
    graph_path = Path(cfg.app.entity_graph_path)
    graph.save(graph_path)

    entity_count = sum(
        1 for _, data in graph.graph.nodes(data=True) if data.get("kind") == "entity"
    )

    return {
        "documents": len(documents),
        "chunks": len(chunks),
        "fts_path": str(fts_path),
        "qdrant_path": cfg.index.qdrant_path,
        "entity_graph_path": str(graph_path),
        "entities": entity_count,
    }
