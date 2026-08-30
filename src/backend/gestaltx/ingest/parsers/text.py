"""Parsers for Markdown and plain-text source documents."""

from __future__ import annotations

import re
from pathlib import Path

from ..metadata import infer_metadata
from ..models import Document, Section

_MD_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_WIKILINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def _section_id(doc_id: str, order: int) -> str:
    return f"{doc_id}:section:{order:04d}"


def _plain_heading(lines: list[str], index: int) -> str | None:
    line = lines[index].strip()
    if not line or len(line) > 120:
        return None
    if index + 1 < len(lines) and re.fullmatch(r"\s*[=-]{3,}\s*", lines[index + 1]):
        return line
    if (
        line == line.upper()
        and any(character.isalpha() for character in line)
        and len(line.split()) <= 12
    ):
        return line.title()
    return None


def parse_text(path: str | Path, corpus_root: str | Path | None = None) -> Document:
    """Parse a UTF-8 Markdown or text file into heading-delimited sections."""
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    metadata = infer_metadata(source, corpus_root)
    lines = text.splitlines()
    sections: list[Section] = []
    title = metadata["title"]
    current_title = title
    body: list[str] = []

    def flush() -> None:
        nonlocal body
        content = "\n".join(body).strip()
        if content:
            order = len(sections)
            sections.append(
                Section(
                    section_id=_section_id(metadata["doc_id"], order),
                    title=current_title,
                    text=content,
                    order=order,
                )
            )
        body = []

    index = 0
    while index < len(lines):
        line = lines[index]
        markdown = _MD_HEADING.match(line) if source.suffix.lower() == ".md" else None
        plain = _plain_heading(lines, index) if source.suffix.lower() == ".txt" else None
        if markdown or plain:
            flush()
            current_title = (markdown.group(2) if markdown else plain or title).strip()
            if not sections and current_title:
                title = current_title
            if plain and index + 1 < len(lines) and re.fullmatch(
                r"\s*[=-]{3,}\s*", lines[index + 1]
            ):
                index += 1
        else:
            body.append(line)
        index += 1
    flush()

    if not sections:
        sections.append(
            Section(
                section_id=_section_id(metadata["doc_id"], 0),
                title=title,
                text="",
                order=0,
            )
        )

    links = list(dict.fromkeys(match.strip() for match in _WIKILINK.findall(text)))
    entities = list(dict.fromkeys(([metadata["subject_entity"]] if metadata["subject_entity"] else []) + links))
    metadata["title"] = title
    return Document(
        **metadata,
        sections=sections,
        wikilinks=links,
        entities=entities,
        metadata={"extension": source.suffix.lower()},
    )


parse = parse_text
