"""Corpus ingestion pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gestaltx.config import GestaltConfig, load_config

from .chunker import chunk_document
from .models import Chunk, Document
from .parsers import SUPPORTED_EXTENSIONS, parse_file


def _dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return model.dict()


def _write_jsonl(path: Path, records: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            stream.write(json.dumps(_dump(record), ensure_ascii=False) + "\n")


def ingest_corpus(
    corpus_root: str | Path | None = None,
    *,
    config: GestaltConfig | None = None,
    documents_path: str | Path | None = None,
    chunks_path: str | Path | None = None,
    strict: bool = False,
) -> tuple[list[Document], list[Chunk]]:
    """Parse a corpus recursively and write deterministic JSONL artifacts."""
    cfg = config or load_config()
    root = Path(corpus_root or cfg.app.corpus_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Corpus directory does not exist: {root}")

    documents: list[Document] = []
    errors: list[dict[str, str]] = []
    sources = sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        ),
        key=lambda path: path.relative_to(root).as_posix().lower(),
    )
    for source in sources:
        try:
            documents.append(parse_file(source, root))
        except Exception as exc:  # noqa: BLE001 - strict mode optionally re-raises
            if strict:
                raise
            errors.append({"path": source.relative_to(root).as_posix(), "error": str(exc)})

    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(
            document,
            chunk_size=cfg.index.chunk_size,
            chunk_overlap=cfg.index.chunk_overlap,
        )
    ]
    if errors and documents:
        documents[0].metadata.setdefault("ingest_errors", errors)
    _write_jsonl(Path(documents_path or cfg.app.documents_jsonl), documents)
    _write_jsonl(Path(chunks_path or cfg.app.chunks_jsonl), chunks)
    return documents, chunks


run_pipeline = ingest_corpus

__all__ = ["ingest_corpus", "run_pipeline"]
