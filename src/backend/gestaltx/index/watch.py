"""Incremental corpus watcher: detect new/changed/removed files and refresh indexes."""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from gestaltx.agent.evidence import document_kind
from gestaltx.config import GestaltConfig, WatchSettings
from gestaltx.graph.builder import EntityGraph
from gestaltx.index.fts import FTSIndex
from gestaltx.ingest.chunker import chunk_document
from gestaltx.ingest.models import Chunk, Document
from gestaltx.ingest.parsers import SUPPORTED_EXTENSIONS, parse_file


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _resolve(path: str | Path, root: Path | None = None) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    return (root / p) if root is not None else p


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _write_jsonl(path: Path, records: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as stream:
        for record in records:
            if hasattr(record, "model_dump"):
                payload = record.model_dump(mode="json")
            elif isinstance(record, dict):
                payload = record
            else:
                payload = dict(record)
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


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


def _empty_manifest() -> dict[str, Any]:
    return {"version": 0, "updated_at": None, "files": {}}


def scan_corpus_files(corpus_dir: Path) -> dict[str, dict[str, Any]]:
    """Walk corpus and return relative-path → {size, mtime_ns, abs_path}."""
    files: dict[str, dict[str, Any]] = {}
    if not corpus_dir.is_dir():
        return files

    def walk(directory: Path) -> None:
        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            walk(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            path = Path(entry.path)
                            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                                continue
                            rel = path.relative_to(corpus_dir).as_posix()
                            stat = entry.stat(follow_symlinks=False)
                            files[rel] = {
                                "size": int(stat.st_size),
                                "mtime_ns": int(getattr(stat, "st_mtime_ns", int(stat.st_mtime * 1e9))),
                                "abs_path": path,
                            }
                    except OSError:
                        continue
        except OSError:
            return

    walk(corpus_dir)
    return files


def corpus_signature(files: dict[str, dict[str, Any]]) -> tuple[int, int, int]:
    count = len(files)
    total_size = sum(int(info["size"]) for info in files.values())
    max_mtime = max((int(info["mtime_ns"]) for info in files.values()), default=0)
    return count, total_size, max_mtime


def build_manifest_from_documents(
    corpus_dir: Path,
    documents: list[Document],
    chunks: list[Chunk],
    *,
    version: int = 1,
) -> dict[str, Any]:
    """Build a watcher-compatible manifest after a full index build."""
    files_on_disk = scan_corpus_files(corpus_dir)
    chunks_by_doc: dict[str, list[str]] = {}
    for chunk in chunks:
        chunks_by_doc.setdefault(chunk.doc_id, []).append(chunk.chunk_id)

    files: dict[str, dict[str, Any]] = {}
    for document in documents:
        rel = document.path.replace("\\", "/")
        disk = files_on_disk.get(rel, {})
        kind = document_kind(
            document.path,
            document.tier,
            {
                "source_family": document.source_family,
                "doctype": document.doctype,
                **(document.metadata or {}),
            },
        )
        files[rel] = {
            "size": int(disk.get("size", 0)),
            "mtime_ns": int(disk.get("mtime_ns", 0)),
            "doc_id": document.doc_id,
            "chunk_ids": chunks_by_doc.get(document.doc_id, []),
            "tier": document.tier,
            "kind": kind,
            "title": document.title,
        }
    return {
        "version": version,
        "updated_at": _now_iso(),
        "files": files,
    }


class CorpusWatcher:
    """Poll the corpus directory and apply incremental FTS / JSONL / graph updates."""

    def __init__(
        self,
        config: GestaltConfig,
        *,
        runtime: Any | None = None,
        root: str | Path | None = None,
    ) -> None:
        self.config = config
        self.runtime = runtime
        self.root = Path(root) if root is not None else Path.cwd()
        watch = getattr(config, "watch", None) or WatchSettings()
        self.settings = watch if isinstance(watch, WatchSettings) else WatchSettings.model_validate(watch)
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._watching = False
        self._last_refresh: str | None = None
        self._last_summary: dict[str, Any] | None = None
        self._recent: list[dict[str, Any]] = []
        self._sig_cache: tuple[float, tuple[int, int, int]] | None = None
        self._sig_ttl = 0.75
        self._manifest = self._load_manifest()

    # ------------------------------------------------------------------ paths
    @property
    def corpus_dir(self) -> Path:
        return _resolve(self.config.app.corpus_dir, self.root)

    @property
    def manifest_path(self) -> Path:
        return _resolve(self.config.app.corpus_manifest, self.root)

    @property
    def documents_path(self) -> Path:
        return _resolve(self.config.app.documents_jsonl, self.root)

    @property
    def chunks_path(self) -> Path:
        return _resolve(self.config.app.chunks_jsonl, self.root)

    @property
    def fts_path(self) -> Path:
        return _resolve(self.config.index.fts_path, self.root)

    @property
    def graph_path(self) -> Path:
        return _resolve(self.config.app.entity_graph_path, self.root)

    # ---------------------------------------------------------------- manifest
    def _load_manifest(self) -> dict[str, Any]:
        path = self.manifest_path
        if not path.exists():
            return _empty_manifest()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _empty_manifest()
        if not isinstance(data, dict):
            return _empty_manifest()
        data.setdefault("version", 0)
        data.setdefault("files", {})
        data.setdefault("updated_at", None)
        return data

    def _seed_from_existing(self) -> bool:
        """If indexes exist but the manifest does not, snapshot without re-parsing."""
        if self.manifest_path.exists() and (self._manifest.get("files") or {}):
            return False
        if not self.documents_path.exists():
            return False
        try:
            docs_rows = _load_jsonl(self.documents_path)
            chunks_rows = _load_jsonl(self.chunks_path)
            documents = [Document.model_validate(row) for row in docs_rows]
            chunks = [Chunk.model_validate(row) for row in chunks_rows]
        except Exception:  # noqa: BLE001
            return False
        if not documents:
            return False
        seeded = build_manifest_from_documents(self.corpus_dir, documents, chunks, version=1)
        self._manifest = seeded
        self._save_manifest()
        self._last_refresh = seeded.get("updated_at")
        return True

    def _save_manifest(self) -> None:
        _write_json(self.manifest_path, self._manifest)

    # -------------------------------------------------------------- signatures
    def signature(self, *, force: bool = False) -> tuple[int, int, int]:
        now = time.monotonic()
        if not force and self._sig_cache is not None:
            cached_at, sig = self._sig_cache
            if now - cached_at < self._sig_ttl:
                return sig
        files = scan_corpus_files(self.corpus_dir)
        sig = corpus_signature(files)
        self._sig_cache = (now, sig)
        return sig

    def _manifest_signature(self) -> tuple[int, int, int]:
        files = self._manifest.get("files") or {}
        count = len(files)
        total_size = sum(int(info.get("size", 0)) for info in files.values())
        max_mtime = max((int(info.get("mtime_ns", 0)) for info in files.values()), default=0)
        return count, total_size, max_mtime

    # -------------------------------------------------------------------- diff
    def diff(self, *, debounce_s: float | None = None) -> dict[str, list[str]]:
        debounce = self.settings.debounce_s if debounce_s is None else debounce_s
        now_ns = time.time_ns()
        debounce_ns = int(debounce * 1e9)
        on_disk = scan_corpus_files(self.corpus_dir)
        known = self._manifest.get("files") or {}

        added: list[str] = []
        modified: list[str] = []
        removed: list[str] = []
        deferred: list[str] = []

        for rel, info in on_disk.items():
            age_ns = now_ns - int(info["mtime_ns"])
            if age_ns < debounce_ns:
                deferred.append(rel)
                continue
            prior = known.get(rel)
            if prior is None:
                added.append(rel)
            elif int(prior.get("size", -1)) != int(info["size"]) or int(prior.get("mtime_ns", -1)) != int(
                info["mtime_ns"]
            ):
                modified.append(rel)

        for rel in known:
            if rel not in on_disk:
                removed.append(rel)

        return {
            "added": sorted(added),
            "modified": sorted(modified),
            "removed": sorted(removed),
            "deferred": sorted(deferred),
        }

    # ------------------------------------------------------------------- apply
    def apply(self, changes: dict[str, list[str]]) -> dict[str, Any] | None:
        added = list(changes.get("added") or [])
        modified = list(changes.get("modified") or [])
        removed = list(changes.get("removed") or [])
        if not (added or modified or removed):
            return None

        with self._lock:
            on_disk = scan_corpus_files(self.corpus_dir)
            docs_rows = _load_jsonl(self.documents_path)
            chunks_rows = _load_jsonl(self.chunks_path)
            docs_by_id = {str(row["doc_id"]): row for row in docs_rows if "doc_id" in row}
            # Prefer path→doc_id from manifest for removals of missing files.
            path_to_doc = {
                rel: str(info.get("doc_id") or "")
                for rel, info in (self._manifest.get("files") or {}).items()
            }

            affected_doc_ids: set[str] = set()
            new_documents: list[Document] = []
            new_chunks: list[Chunk] = []
            summary_added: list[dict[str, Any]] = []
            summary_modified: list[dict[str, Any]] = []
            summary_removed: list[dict[str, Any]] = []
            failed: list[str] = []

            for rel in removed:
                doc_id = path_to_doc.get(rel) or ""
                if not doc_id:
                    # Fall back to scanning docs by path.
                    for row in docs_rows:
                        if str(row.get("path") or "").replace("\\", "/") == rel:
                            doc_id = str(row["doc_id"])
                            break
                if doc_id:
                    affected_doc_ids.add(doc_id)
                    prior = (self._manifest.get("files") or {}).get(rel) or {}
                    summary_removed.append(
                        {
                            "path": rel,
                            "title": prior.get("title") or rel,
                            "kind": prior.get("kind") or "document",
                            "tier": prior.get("tier"),
                        }
                    )
                self._manifest.setdefault("files", {}).pop(rel, None)

            chunk_size = getattr(self.config.index, "chunk_size", 900)
            chunk_overlap = getattr(self.config.index, "chunk_overlap", 120)

            for rel in added + modified:
                info = on_disk.get(rel)
                if info is None:
                    continue
                abs_path = Path(info["abs_path"])
                try:
                    document = parse_file(abs_path, self.corpus_dir)
                    chunks = chunk_document(
                        document,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                    )
                except Exception:  # noqa: BLE001 - retry next tick
                    failed.append(rel)
                    continue

                # If path changed doc_id somehow, still clear prior id for this path.
                prior_id = path_to_doc.get(rel)
                if prior_id:
                    affected_doc_ids.add(prior_id)
                affected_doc_ids.add(document.doc_id)
                new_documents.append(document)
                new_chunks.extend(chunks)

                kind = document_kind(
                    document.path,
                    document.tier,
                    {
                        "source_family": document.source_family,
                        "doctype": document.doctype,
                        **(document.metadata or {}),
                    },
                )
                entry = {
                    "size": int(info["size"]),
                    "mtime_ns": int(info["mtime_ns"]),
                    "doc_id": document.doc_id,
                    "chunk_ids": [c.chunk_id for c in chunks],
                    "tier": document.tier,
                    "kind": kind,
                    "title": document.title,
                }
                self._manifest.setdefault("files", {})[rel] = entry
                card = {
                    "path": rel,
                    "title": document.title,
                    "kind": kind,
                    "tier": document.tier,
                }
                if rel in added:
                    summary_added.append(card)
                else:
                    summary_modified.append(card)

            # Merge JSONL in memory.
            for doc_id in affected_doc_ids:
                docs_by_id.pop(doc_id, None)
            for document in new_documents:
                docs_by_id[document.doc_id] = document.model_dump(mode="json")

            remaining_chunks = [
                row for row in chunks_rows if str(row.get("doc_id")) not in affected_doc_ids
            ]
            for chunk in new_chunks:
                remaining_chunks.append(chunk.model_dump(mode="json"))

            # FTS update on a dedicated connection.
            self.fts_path.parent.mkdir(parents=True, exist_ok=True)
            with FTSIndex(self.fts_path) as fts:
                for doc_id in affected_doc_ids:
                    fts.remove_document(doc_id)
                if new_chunks:
                    fts.add(new_chunks)

            ordered_docs = sorted(docs_by_id.values(), key=lambda row: str(row.get("path") or ""))
            _write_jsonl(self.documents_path, ordered_docs)
            _write_jsonl(self.chunks_path, remaining_chunks)

            documents = [Document.model_validate(row) for row in ordered_docs]
            EntityGraph().build(documents).save(self.graph_path)

            self._manifest["version"] = int(self._manifest.get("version") or 0) + 1
            self._manifest["updated_at"] = _now_iso()
            self._save_manifest()
            self._sig_cache = None
            self._last_refresh = self._manifest["updated_at"]

            summary = {
                "version": self._manifest["version"],
                "updated_at": self._last_refresh,
                "added": summary_added,
                "modified": summary_modified,
                "removed": summary_removed,
                "failed": failed,
            }
            self._last_summary = summary
            if summary_added or summary_modified or summary_removed:
                self._recent = (summary_added + summary_modified + summary_removed)[:8]

            if self.runtime is not None and hasattr(self.runtime, "invalidate"):
                self.runtime.invalidate()

            return summary

    # -------------------------------------------------------------- refresh API
    def refresh_if_stale(self, *, force: bool = False) -> dict[str, Any] | None:
        if not force:
            if self.signature() == self._manifest_signature() and self.manifest_path.exists():
                return None
        changes = self.diff(debounce_s=0.0 if force else None)
        if force:
            # Force still respects only that we compare against manifest; include
            # deferred by re-diffing without debounce.
            changes = self.diff(debounce_s=0.0)
        if not (changes["added"] or changes["modified"] or changes["removed"]):
            # Signature mismatch but nothing actionable (e.g. only deferred) —
            # or empty corpus with missing manifest: seed empty manifest.
            if not self.manifest_path.exists() and not (self._manifest.get("files")):
                with self._lock:
                    self._manifest = _empty_manifest()
                    self._manifest["version"] = 1
                    self._manifest["updated_at"] = _now_iso()
                    # Snapshot whatever is stable on disk (debounce already applied).
                    on_disk = scan_corpus_files(self.corpus_dir)
                    # If files exist but all deferred, wait.
                    if on_disk and not changes.get("deferred"):
                        pass
                    self._save_manifest()
            return None
        return self.apply(changes)

    def status(self) -> dict[str, Any]:
        docs = len(self._manifest.get("files") or {})
        chunks = sum(len(info.get("chunk_ids") or []) for info in (self._manifest.get("files") or {}).values())
        return {
            "version": int(self._manifest.get("version") or 0),
            "documents": docs,
            "chunks": chunks,
            "watching": self._watching,
            "last_refresh": self._last_refresh or self._manifest.get("updated_at"),
            "recent": list(self._recent),
            "updated_at": self._manifest.get("updated_at"),
        }

    # ------------------------------------------------------------- background
    def start_background(self, interval_s: float | None = None) -> None:
        if not self.settings.enabled:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        try:
            self._seed_from_existing()
        except Exception:  # noqa: BLE001
            pass
        interval = self.settings.interval_s if interval_s is None else interval_s
        self._stop.clear()

        def loop() -> None:
            self._watching = True
            try:
                while not self._stop.wait(interval):
                    try:
                        self.refresh_if_stale()
                    except Exception:  # noqa: BLE001 - never kill the watcher thread
                        continue
            finally:
                self._watching = False

        self._thread = threading.Thread(target=loop, name="gestaltx-corpus-watch", daemon=True)
        self._thread.start()

    def stop_background(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)
        self._thread = None
        self._watching = False


def format_corpus_update_message(summary: dict[str, Any] | None) -> str | None:
    """Human-readable status line for the research activity feed."""
    if not summary:
        return None
    added = summary.get("added") or []
    modified = summary.get("modified") or []
    removed = summary.get("removed") or []
    parts: list[str] = []
    if added:
        names = ", ".join(f"{item['title']} ({item['kind']})" for item in added[:3])
        extra = f" and {len(added) - 3} more" if len(added) > 3 else ""
        noun = "document" if len(added) == 1 else "documents"
        parts.append(f"Noticed {len(added)} new {noun} in the archive — {names}{extra}. Indexed and included.")
    if modified:
        names = ", ".join(f"{item['title']} ({item['kind']})" for item in modified[:2])
        parts.append(f"Updated {len(modified)} existing source{'s' if len(modified) != 1 else ''}: {names}.")
    if removed:
        parts.append(f"Removed {len(removed)} source{'s' if len(removed) != 1 else ''} from the index.")
    return " ".join(parts) if parts else None


__all__ = [
    "CorpusWatcher",
    "build_manifest_from_documents",
    "corpus_signature",
    "format_corpus_update_message",
    "scan_corpus_files",
]
