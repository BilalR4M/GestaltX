"""Lightweight entity hints from Markdown content."""

from __future__ import annotations

import re

_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
_SEPARATOR = re.compile(r"^:?-{3,}:?$")


def extract_wikilinks(text: str) -> list[str]:
    """Return unique wikilink targets in first-seen order."""
    return list(
        dict.fromkeys(
            target.strip()
            for target in _WIKILINK.findall(text)
            if target.strip()
        )
    )


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def extract_infobox(text: str) -> dict[str, str]:
    """Extract key/value rows from Markdown tables, skipping header separators."""
    lines = text.splitlines()
    output: dict[str, str] = {}
    for index, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = _cells(line)
        if len(cells) != 2 or not all(cells):
            continue
        if all(_SEPARATOR.fullmatch(cell.replace(" ", "")) for cell in cells):
            continue
        if index + 1 < len(lines):
            next_cells = _cells(lines[index + 1])
            if len(next_cells) == 2 and all(
                _SEPARATOR.fullmatch(cell.replace(" ", "")) for cell in next_cells
            ):
                continue
        key = re.sub(r"[*_`]", "", cells[0]).strip().rstrip(":")
        value = re.sub(r"[*_`]", "", cells[1]).strip()
        if key and value:
            output.setdefault(key, value)
    return output


def extract_graph_hints(text: str) -> tuple[list[str], dict[str, str]]:
    return extract_wikilinks(text), extract_infobox(text)


__all__ = ["extract_graph_hints", "extract_infobox", "extract_wikilinks"]
