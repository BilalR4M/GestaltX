"""Incremental corpus watcher and classification fallbacks."""

from __future__ import annotations

import json
import time
from pathlib import Path

from gestaltx.config import GestaltConfig
from gestaltx.index.fts import FTSIndex
from gestaltx.index.watch import CorpusWatcher
from gestaltx.ingest.metadata import classify_document, infer_metadata
from gestaltx.ingest.models import Document, Section
from gestaltx.ingest.parsers import parse_file


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _config(root: Path) -> GestaltConfig:
    corpus = root / "corpus"
    processed = root / "processed"
    corpus.mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    return GestaltConfig.model_validate(
        {
            "app": {
                "corpus_dir": str(corpus),
                "processed_dir": str(processed),
                "documents_jsonl": str(processed / "documents.jsonl"),
                "chunks_jsonl": str(processed / "chunks.jsonl"),
                "entity_graph_path": str(processed / "entity_graph.json"),
                "corpus_manifest": str(processed / "corpus_manifest.json"),
            },
            "index": {
                "fts_path": str(processed / "fts.sqlite3"),
                "chunk_size": 400,
                "chunk_overlap": 40,
            },
            "watch": {
                "enabled": False,
                "interval_s": 30.0,
                "debounce_s": 0.0,
                "check_on_query": True,
            },
        }
    )


def test_filename_codex_at_root_is_tier_1(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    path = root / "codex_of_x.md"
    _write(path, "# Codex of X\n\nGloamreach was founded in 246 AS.\n")
    doc = parse_file(path, root)
    assert doc.source_family == "codex"
    assert doc.tier == 1
    assert doc.doctype == "codex"


def test_random_notes_default_to_chronicle(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    path = root / "random_notes.md"
    _write(path, "# Loose thoughts\n\nSomeone muttered about a founding year.\n")
    doc = parse_file(path, root)
    assert doc.source_family == "chronicles"
    assert doc.tier == 3
    assert doc.doctype == "chronicle"
    assert doc.reliability == 0.45
    assert (doc.metadata or {}).get("classification", {}).get("basis") == "default"


def test_infer_metadata_filename_keywords() -> None:
    meta = infer_metadata("codex_of_x.md")
    assert meta["source_family"] == "codex"
    assert meta["tier"] == 1
    assert meta["classification"]["basis"] == "filename"

    meta2 = infer_metadata("random_notes.md")
    assert meta2["source_family"] == "unknown"
    assert meta2["tier"] == 5


def test_classify_document_content_codex_heading() -> None:
    document = Document(
        doc_id="notes",
        path="notes.md",
        title="Notes",
        tier=5,
        doctype="unknown",
        source_family="unknown",
        sections=[Section(section_id="s1", title="Codex Entry", text="Annals of Gloamreach record 246 AS.")],
    )
    # Force content path: heading pattern needs # Codex
    document.sections[0].title = "Overview"
    document.sections[0].text = "# Codex Gazetteer\n\nGloamreach founded 246 AS."
    classify_document(document)
    assert document.source_family == "codex"
    assert document.tier == 1


def test_watcher_add_modify_delete(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    corpus = Path(cfg.app.corpus_dir)
    a = corpus / "wiki" / "Alpha.md"
    b = corpus / "wiki" / "Beta.md"
    _write(a, "# Alpha\n\nAlpha mentions the AlphaCrystalMarker crystal.\n")
    _write(b, "# Beta\n\nBeta mentions the BetaRiverMarker river.\n")
    # Ensure mtimes are stable relative to debounce=0.
    time.sleep(0.05)

    watcher = CorpusWatcher(cfg, root=tmp_path)
    summary = watcher.refresh_if_stale(force=True)
    assert summary is not None
    assert len(summary["added"]) == 2
    assert summary["version"] == 1

    with FTSIndex(cfg.index.fts_path) as fts:
        hits = fts.search("AlphaCrystalMarker")
        assert hits, "new document text should be searchable"
        assert fts.count() >= 2

    graph = json.loads(Path(cfg.app.entity_graph_path).read_text(encoding="utf-8"))
    nodes = graph.get("nodes") or []
    assert any(
        "document:" in str(node.get("id", "") if isinstance(node, dict) else node)
        for node in nodes
    )

    # Modify Beta — replace unique token.
    _write(b, "# Beta\n\nBeta now mentions BetaRiverRevised instead.\n")
    time.sleep(0.05)
    summary2 = watcher.refresh_if_stale(force=True)
    assert summary2 is not None
    assert len(summary2["modified"]) == 1
    assert summary2["version"] == 2

    with FTSIndex(cfg.index.fts_path) as fts:
        assert fts.search("BetaRiverRevised")
        assert not fts.search("BetaRiverMarker")

    docs = [
        json.loads(line)
        for line in Path(cfg.app.documents_jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(docs) == 2

    # Delete Beta.
    b.unlink()
    time.sleep(0.05)
    summary3 = watcher.refresh_if_stale(force=True)
    assert summary3 is not None
    assert len(summary3["removed"]) == 1
    assert summary3["version"] == 3

    with FTSIndex(cfg.index.fts_path) as fts:
        assert not fts.search("BetaRiverRevised")
        assert fts.search("AlphaCrystalMarker")

    docs_after = [
        json.loads(line)
        for line in Path(cfg.app.documents_jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(docs_after) == 1
    chunks_after = [
        json.loads(line)
        for line in Path(cfg.app.chunks_jsonl).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert all("beta" not in str(row.get("path", "")).casefold() for row in chunks_after)


def test_watcher_indexes_root_codex_file(tmp_path: Path) -> None:
    cfg = _config(tmp_path)
    corpus = Path(cfg.app.corpus_dir)
    _write(
        corpus / "codex_of_x.md",
        "# Codex of X\n\nThe fortress was founded in 246 AS per the official record.\n",
    )
    time.sleep(0.05)
    watcher = CorpusWatcher(cfg, root=tmp_path)
    summary = watcher.refresh_if_stale(force=True)
    assert summary is not None
    assert summary["added"][0]["tier"] == 1
    assert "codex" in summary["added"][0]["kind"]

    with FTSIndex(cfg.index.fts_path) as fts:
        hits = fts.search("246")
        assert hits
        assert int(hits[0].get("tier", 5)) == 1
