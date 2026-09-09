"""Lazy application runtime and index loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _discover_root(explicit: str | Path | None = None) -> Path:
    if explicit is not None:
        return Path(explicit)
    here = Path(__file__).resolve()
    # .../src/backend/gestaltx/api/runtime.py → repo root is parents[3]
    candidates = [
        Path.cwd(),
        here.parents[3],  # repo root when installed as src/backend/gestaltx
        here.parents[2],
        Path.cwd().parent,
        Path.cwd().parent.parent,
    ]
    for candidate in candidates:
        if (candidate / "data" / "processed" / "fts.sqlite3").exists():
            return candidate
        if (candidate / "gestaltx.config.yaml").exists():
            return candidate
    return Path.cwd()


def _probe_llm(config: Any | None) -> tuple[Any | None, dict[str, Any]]:
    """Return (client_or_None, status dict) using the same availability probe."""
    try:
        from gestaltx.llm import LLMClient
        import httpx

        client = LLMClient(config)
        settings = client.settings
        status = {
            "provider": settings.provider,
            "model": (
                settings.ollama_model
                if settings.provider == "ollama"
                else settings.openrouter_model
            ),
            "available": False,
        }
        if settings.provider == "ollama":
            probe = settings.ollama_base_url.rstrip("/").removesuffix("/v1") + "/api/tags"
            with httpx.Client(timeout=1.5) as http:
                http.get(probe).raise_for_status()
        elif settings.provider == "openrouter":
            import os

            if not os.getenv(settings.openrouter_api_key_env, ""):
                status["error"] = "missing OpenRouter API key"
                return None, status
        status["available"] = True
        return client, status
    except Exception as exc:  # noqa: BLE001
        return None, {"provider": None, "model": None, "available": False, "error": str(exc)}


class Runtime:
    def __init__(self, config: Any | None = None, *, root: str | Path | None = None) -> None:
        self.root = _discover_root(root)
        self.config = config
        self._searcher: Any = ...
        self._documents: Any = ...
        self._graph: Any = ...
        self._tools: Any = ...
        self._fts: Any = ...
        self._vector: Any = ...
        self._corpus_watcher: Any = ...

    def _path(self, setting: str, default: str) -> Path:
        value = default
        app = getattr(self.config, "app", None)
        index = getattr(self.config, "index", None)
        owner = app if hasattr(app, setting) else index
        if owner is not None and hasattr(owner, setting):
            value = getattr(owner, setting, default)
        elif index is not None and hasattr(index, setting):
            value = getattr(index, setting, default)
        path = Path(value)
        return path if path.is_absolute() else self.root / path

    def invalidate(self) -> None:
        """Drop cached index handles so the next access reloads from disk."""
        fts = self._fts
        if fts is not ... and fts is not None and hasattr(fts, "close"):
            try:
                fts.close()
            except Exception:  # noqa: BLE001
                pass
        self._searcher = ...
        self._documents = ...
        self._graph = ...
        self._tools = ...
        self._fts = ...
        self._vector = ...

    @property
    def documents(self) -> Path:
        if self._documents is ...:
            self._documents = self._path("documents_jsonl", "data/processed/documents.jsonl")
        return self._documents

    @property
    def graph(self) -> dict[str, Any]:
        if self._graph is ...:
            path = self._path("entity_graph_path", "data/processed/entity_graph.json")
            self._graph = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        return self._graph

    @property
    def fts(self) -> Any | None:
        if self._fts is ...:
            self._fts = None
            path = self._path("fts_path", "data/processed/fts.sqlite3")
            if path.exists():
                from gestaltx.index.fts import FTSIndex

                self._fts = FTSIndex(path)
        return self._fts

    @property
    def vector(self) -> Any | None:
        if self._vector is ...:
            # Dense index is optional. Default builds skip it (CPU FastEmbed is slow).
            # Enable only when GESTALTX_USE_DENSE=1 and the Qdrant path exists.
            self._vector = None
            import os

            if os.getenv("GESTALTX_USE_DENSE", "").strip() in {"1", "true", "yes"}:
                path = self._path("qdrant_path", "data/processed/qdrant_local")
                if path.exists() and any(path.iterdir()):
                    try:
                        from gestaltx.index.embeddings import Embedder
                        from gestaltx.index.vector import VectorIndex

                        index_cfg = getattr(self.config, "index", None)
                        model = getattr(index_cfg, "embedding_model", "BAAI/bge-small-en-v1.5")
                        collection = getattr(index_cfg, "collection_name", "ashen_chunks")
                        embedder = Embedder(model, prefer_fastembed=True)
                        self._vector = VectorIndex(
                            path=path,
                            collection_name=collection,
                            embedder=embedder,
                        )
                    except Exception:
                        self._vector = None
        return self._vector

    @property
    def searcher(self) -> Any | None:
        if self._searcher is ...:
            self._searcher = None
            if self.fts is not None:
                from gestaltx.index.hybrid import HybridSearcher

                index_cfg = getattr(self.config, "index", None)
                self._searcher = HybridSearcher(
                    self.fts,
                    self.vector,
                    fts_weight=getattr(index_cfg, "hybrid_fts_weight", 0.45),
                    dense_weight=getattr(index_cfg, "hybrid_dense_weight", 0.55),
                )
        return self._searcher

    @property
    def tools(self):
        if self._tools is ...:
            from gestaltx.tools import build_default_tools

            self._tools = build_default_tools(self)
        return self._tools

    @property
    def corpus_watcher(self):
        if self._corpus_watcher is ...:
            self._corpus_watcher = None
            if self.config is not None:
                from gestaltx.index.watch import CorpusWatcher

                self._corpus_watcher = CorpusWatcher(self.config, runtime=self, root=self.root)
        return self._corpus_watcher

    def refresh_corpus(self, *, force: bool = False) -> dict[str, Any] | None:
        watcher = self.corpus_watcher
        if watcher is None:
            return None
        watch = getattr(self.config, "watch", None)
        if watch is not None and not getattr(watch, "check_on_query", True) and not force:
            return None
        try:
            acquired = watcher._lock.acquire(timeout=20.0)  # noqa: SLF001
            if not acquired:
                return None
            try:
                return watcher.refresh_if_stale(force=force)
            finally:
                watcher._lock.release()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return None

    def start_corpus_watcher(self) -> None:
        watcher = self.corpus_watcher
        if watcher is None:
            return
        # Snapshot an existing index into the manifest first so startup does
        # not re-parse the entire corpus when the manifest is missing.
        try:
            watcher._seed_from_existing()  # noqa: SLF001
        except Exception:  # noqa: BLE001
            pass
        watcher.start_background()

    @property
    def corpus_status(self) -> dict[str, Any]:
        watcher = self.corpus_watcher
        if watcher is None:
            return {
                "version": 0,
                "documents": 0,
                "chunks": 0,
                "watching": False,
                "last_refresh": None,
                "recent": [],
            }
        return watcher.status()

    def research_loop(self):
        from gestaltx.agent import ResearchLoop

        agent = getattr(self.config, "agent", None)
        corpus_update = self.refresh_corpus()
        llm, _status = _probe_llm(self.config)
        return ResearchLoop(
            self.tools,
            llm=llm,
            max_iterations=getattr(agent, "max_iterations", 6),
            corpus_update=corpus_update,
        )

    @property
    def llm_status(self) -> dict[str, Any]:
        _client, status = _probe_llm(self.config)
        return status

    @property
    def ready(self) -> bool:
        return self.searcher is not None


_runtime: Runtime | None = None


def get_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        config = None
        try:
            from gestaltx.config import load_config

            root = _discover_root()
            # Resolve relative config paths against the repo root.
            import os

            prev = os.getcwd()
            try:
                os.chdir(root)
                config = load_config()
            finally:
                os.chdir(prev)
        except Exception:
            config = None
        _runtime = Runtime(config, root=_discover_root())
    return _runtime


__all__ = ["Runtime", "get_runtime"]
