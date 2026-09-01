"""Common tool protocol and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
import inspect
from typing import Any


class Tool(ABC):
    """Small synchronous tool interface used by the research loop."""

    name: str
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool."""

    def __call__(self, **kwargs: Any) -> Any:
        return self.run(**kwargs)

    def schema(self) -> dict[str, Any]:
        """Return a compact JSON schema for the tool's keyword arguments."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for name, parameter in inspect.signature(self.run).parameters.items():
            if name in {"self", "kwargs"}:
                continue
            annotation = parameter.annotation
            kind = "integer" if annotation is int else "boolean" if annotation is bool else "string"
            properties[name] = {"type": kind}
            if parameter.default is inspect.Parameter.empty:
                required.append(name)
        schema: dict[str, Any] = {"type": "object", "properties": properties}
        if required:
            schema["required"] = required
        return schema


class ToolRegistry:
    """Name-addressable collection with duplicate protection."""

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: Tool, *, replace: bool = False) -> Tool:
        if not replace and tool.name in self._tools:
            raise ValueError(f"tool already registered: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"unknown tool {name!r}; available: {', '.join(self.names())}") from exc

    def call(self, name: str, **kwargs: Any) -> Any:
        return self.get(name).run(**kwargs)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def as_mapping(self) -> Mapping[str, Tool]:
        return dict(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __iter__(self):
        return iter(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def values(self):
        return self._tools.values()

    def keys(self):
        return self._tools.keys()

    def items(self):
        return self._tools.items()


__all__ = ["Tool", "ToolRegistry"]
