"""Read a single normalized document section."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import Tool


class ReadSectionTool(Tool):
    name = "read_section"
    description = "Load one section by document and section identifier."

    def __init__(self, store: str | Path | list[dict[str, Any]] | dict[str, Any] | None) -> None:
        self.store = store
        self._documents: dict[str, dict[str, Any]] | None = None

    def _load(self) -> dict[str, dict[str, Any]]:
        if self._documents is not None:
            return self._documents
        data: Any = self.store
        if isinstance(data, (str, Path)):
            path = Path(data)
            data = []
            if path.exists():
                with path.open(encoding="utf-8") as stream:
                    data = [json.loads(line) for line in stream if line.strip()]
        if isinstance(data, dict):
            if "documents" in data:
                data = data["documents"]
            else:
                self._documents = data
                return data
        self._documents = {str(doc.get("doc_id")): doc for doc in (data or [])}
        return self._documents

    def run(self, doc_id: str, section_id: str | None = None) -> dict[str, Any]:
        document = self._load().get(doc_id)
        if document is None:
            raise KeyError(f"document not found: {doc_id}")
        sections = document.get("sections", [])
        if section_id is None:
            if len(sections) != 1:
                raise ValueError("section_id is required when a document has multiple sections")
            section = sections[0]
        else:
            section = next(
                (item for item in sections if str(item.get("section_id")) == str(section_id)),
                None,
            )
            if section is None:
                raise KeyError(f"section not found: {doc_id}/{section_id}")
        return {
            "doc_id": doc_id,
            "title": document.get("title", ""),
            "path": document.get("path", ""),
            "tier": document.get("tier", 5),
            "doctype": document.get("doctype", ""),
            "reliability": document.get("reliability", 0.5),
            **section,
        }


__all__ = ["ReadSectionTool"]
