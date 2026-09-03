"""Entity graph lookup tools with near-name warnings."""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from .base import Tool


def _load_graph(graph: Any) -> dict[str, Any]:
    if isinstance(graph, (str, Path)):
        path = Path(graph)
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return graph or {}


def _entities(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = graph.get("entities", graph)
    if isinstance(raw, list):
        return {str(item.get("name") or item.get("id")): item for item in raw}
    return raw if isinstance(raw, dict) else {}


def _near(name: str, names: list[str]) -> list[str]:
    return difflib.get_close_matches(name, names, n=5, cutoff=0.68)


class LookupEntityTool(Tool):
    name = "lookup_entity"
    description = "Resolve an entity and return graph facts, neighbors, and name warnings."

    def __init__(self, graph: Any, *, warn_near_names: bool = True) -> None:
        self.graph = _load_graph(graph)
        self.warn_near_names = warn_near_names

    def run(self, name: str) -> dict[str, Any]:
        entities = _entities(self.graph)
        canonical = next((key for key in entities if key.casefold() == name.casefold()), None)
        near = _near(name, list(entities)) if self.warn_near_names else []
        if canonical is None:
            return {"found": False, "query": name, "near_names": near}
        warnings = [candidate for candidate in near if candidate != canonical]
        return {
            "found": True,
            "query": name,
            "name": canonical,
            "entity": entities[canonical],
            "near_names": warnings,
            "warning": f"Do not confuse {canonical} with {', '.join(warnings)}." if warnings else None,
        }


class ListSourcesAboutTool(Tool):
    name = "list_sources_about"
    description = "List source documents connected to an entity."

    def __init__(self, graph: Any, *, warn_near_names: bool = True) -> None:
        self.graph = _load_graph(graph)
        self.lookup = LookupEntityTool(self.graph, warn_near_names=warn_near_names)

    def run(self, name: str) -> dict[str, Any]:
        resolved = self.lookup.run(name)
        if not resolved["found"]:
            return {**resolved, "sources": []}
        entity = resolved["entity"]
        sources = entity.get("sources") or entity.get("documents") or entity.get("source_ids") or []
        if not sources:
            edges = self.graph.get("edges", [])
            sources = [
                edge.get("source_doc") or edge.get("document")
                for edge in edges
                if str(edge.get("entity", "")).casefold() == resolved["name"].casefold()
            ]
            sources = [source for source in sources if source]
        return {**resolved, "sources": sources}


__all__ = ["LookupEntityTool", "ListSourcesAboutTool"]
