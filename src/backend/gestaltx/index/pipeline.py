"""End-to-end index build: ingest (if needed) + FTS + optional vectors + entity graph."""

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


def build_indexes(
    config: GestaltConfig | None = None,
    *,
    force: bool = False,
    skip_dense: bool = True,
    prefer_fastembed: bool = False,
) -> dict[str, Any]:
    """Build or refresh indexes.

    Dense vectors are skipped by default because FastEmbed/ONNX over the full
    Ashen Era corpus is slow on CPU. FTS5 + entity graph are enough for the
    Sub-track 1C demo (exact names, contested pointers, tier filters).
    """
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
        print(f"Ingesting corpus from {corpus} ...")
        ingest_corpus(corpus, config=cfg)

    documents = [Document.model_validate(row) for row in _load_jsonl(docs_path)]
    chunks = [Chunk.model_validate(row) for row in _load_jsonl(chunks_path)]
    print(f"Loaded {len(documents)} documents / {len(chunks)} chunks")

    fts_path = Path(cfg.index.fts_path)
    if force and fts_path.exists():
        fts_path.unlink()
    fts = FTSIndex(fts_path)
    if force:
        fts.clear()
    print(f"Building FTS index at {fts_path} ...")
    fts.add(chunks)
    fts.close()

    vector_status = "skipped"
    if not skip_dense:
        print("Building dense vector index (this can take a while on CPU) ...")
        embedder = Embedder(cfg.index.embedding_model, prefer_fastembed=prefer_fastembed)
        print(f"Embedder backend: {embedder.backend}")
        vector = VectorIndex(
            path=cfg.index.qdrant_path,
            collection_name=cfg.index.collection_name,
            embedder=embedder,
        )
        if force:
            vector.clear()
        # Batch to keep memory bounded and show progress.
        batch_size = 256
        total = 0
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            total += vector.add(batch)
            print(f"  embedded {total}/{len(chunks)}")
        vector.close()
        vector_status = embedder.backend

    print("Building entity graph ...")
    graph = EntityGraph().build(documents)
    graph_path = Path(cfg.app.entity_graph_path)
    graph.save(graph_path)

    from gestaltx.index.watch import build_manifest_from_documents

    corpus = Path(cfg.app.corpus_dir)
    manifest = build_manifest_from_documents(corpus, documents, chunks, version=1)
    # Preserve version bump if a prior manifest exists with a higher version.
    manifest_path = Path(getattr(cfg.app, "corpus_manifest", "data/processed/corpus_manifest.json"))
    if manifest_path.exists():
        try:
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            prior_version = int(prior.get("version") or 0)
            if force:
                manifest["version"] = prior_version + 1
            else:
                manifest["version"] = max(prior_version, 1)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = manifest_path.with_suffix(manifest_path.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(manifest_path)

    entity_count = sum(
        1 for _, data in graph.graph.nodes(data=True) if data.get("kind") == "entity"
    )

    result = {
        "documents": len(documents),
        "chunks": len(chunks),
        "fts_path": str(fts_path),
        "qdrant_path": cfg.index.qdrant_path,
        "entity_graph_path": str(graph_path),
        "corpus_manifest": str(manifest_path),
        "entities": entity_count,
        "dense": vector_status,
        "manifest_version": manifest["version"],
    }
    print(result)
    return result
