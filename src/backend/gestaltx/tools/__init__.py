"""Default GestaltX research tools."""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolRegistry
from .compare import CompareClaimsTool
from .entity import ListSourcesAboutTool, LookupEntityTool
from .read import ReadSectionTool
from .search import SearchCorpusTool


def build_default_tools(runtime: Any) -> ToolRegistry:
    """Construct tools from either attributes or lazy runtime properties."""
    searcher = getattr(runtime, "searcher", None)
    documents = getattr(runtime, "documents", None)
    graph = getattr(runtime, "graph", None)
    return ToolRegistry(
        [
            SearchCorpusTool(searcher),
            ReadSectionTool(documents),
            LookupEntityTool(graph),
            ListSourcesAboutTool(graph),
            CompareClaimsTool(),
        ]
    )


def get_tool_registry(runtime: Any | None = None) -> ToolRegistry:
    """Compatibility factory; missing resources produce usable local no-op tools."""
    if runtime is None:
        class _LocalRuntime:
            searcher = None
            documents = None
            graph: dict[str, Any] = {}

        runtime = _LocalRuntime()
    return build_default_tools(runtime)


__all__ = [
    "Tool",
    "ToolRegistry",
    "SearchCorpusTool",
    "ReadSectionTool",
    "LookupEntityTool",
    "ListSourcesAboutTool",
    "CompareClaimsTool",
    "build_default_tools",
    "get_tool_registry",
]
