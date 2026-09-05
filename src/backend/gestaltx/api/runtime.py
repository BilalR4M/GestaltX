"""Lazy application runtime and optional index loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Runtime:
    def __init__(self, config: Any | None = None, *, root: str | Path | None = None) -> None:
        self.root = Path(root or Path.cwd())
        self.config = config
        self._searcher: Any = ...
        self._documents: Any = ...
        self._graph: Any = ...
        self._tools: Any = ...

    def _path(self, setting: str, default: str) -> Path:
        value = default
        app = getattr(self.config, "app", None)
        index = getattr(self.config, "index", None)
        owner = app if hasattr(app, setting) else index
        if owner is not None:
            value = getattr(owner, setting, default)
        path = Path(value)
        return path if path.is_absolute() else self.root / path

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
    def searcher(self) -> Any | None:
        if self._searcher is ...:
            self._searcher = None
            try:
                from gestaltx.index.hybrid import HybridSearcher

                try:
                    self._searcher = HybridSearcher(config=self.config)
                except TypeError:
                    self._searcher = HybridSearcher()
            except (ImportError, OSError, RuntimeError):
                self._searcher = None
        return self._searcher

    @property
    def tools(self):
        if self._tools is ...:
            from gestaltx.tools import build_default_tools

            self._tools = build_default_tools(self)
        return self._tools

    def research_loop(self):
        from gestaltx.agent import ResearchLoop

        agent = getattr(self.config, "agent", None)
        return ResearchLoop(
            self.tools,
            max_iterations=getattr(agent, "max_iterations", 6),
        )

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

            config = load_config()
        except Exception:
            pass
        _runtime = Runtime(config)
    return _runtime


__all__ = ["Runtime", "get_runtime"]
