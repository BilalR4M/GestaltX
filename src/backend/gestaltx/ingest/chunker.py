"""Structure-aware document chunking."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import Chunk, Document, Section


def _split_points(text: str, maximum: int) -> list[str]:
    """Split at paragraphs/sentences where possible, never dropping text."""
    if len(text) <= maximum:
        return [text]
    units = [
        unit.strip()
        for unit in re.split(r"(?<=\n)\s*\n+|(?<=[.!?])\s+(?=[A-Z0-9\[])|(?<=;)\s+", text)
        if unit.strip()
    ]
    pieces: list[str] = []
    current = ""
    for unit in units:
        while len(unit) > maximum:
            if current:
                pieces.append(current)
                current = ""
            cut = unit.rfind(" ", 0, maximum + 1)
            cut = cut if cut > maximum // 2 else maximum
            pieces.append(unit[:cut].strip())
            unit = unit[cut:].strip()
        candidate = f"{current}\n\n{unit}".strip() if current else unit
        if len(candidate) > maximum and current:
            pieces.append(current)
            current = unit
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces or [text[:maximum]]


def _chunk_section(section: Section, size: int, overlap: int) -> list[str]:
    if not section.text.strip():
        return []
    pieces = _split_points(section.text.strip(), size)
    if not overlap or len(pieces) < 2:
        return pieces
    output = [pieces[0]]
    for previous, piece in zip(pieces, pieces[1:]):
        prefix = previous[-overlap:].lstrip()
        first_space = prefix.find(" ")
        if first_space >= 0:
            prefix = prefix[first_space + 1 :]
        output.append(f"{prefix}\n{piece}".strip()[: size + overlap])
    return output


def chunk_document(
    document: Document,
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    """Chunk each section independently and preserve source metadata."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be non-negative and smaller than chunk_size")

    chunks: list[Chunk] = []
    for section in sorted(document.sections, key=lambda item: item.order):
        for local_index, text in enumerate(
            _chunk_section(section, chunk_size, chunk_overlap)
        ):
            ordinal = len(chunks)
            chunk_metadata = {
                **document.metadata,
                "title": document.title,
                "section_title": section.title,
                "section_order": section.order,
                "chunk_in_section": local_index,
                "source_family": document.source_family,
                "reliability": document.reliability,
            }
            if section.page_start is not None:
                chunk_metadata["page_start"] = section.page_start
                chunk_metadata["page_end"] = section.page_end
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}:chunk:{ordinal:05d}",
                    doc_id=document.doc_id,
                    section_id=section.section_id,
                    text=text,
                    tier=document.tier,
                    doctype=document.doctype,
                    path=document.path,
                    entities=list(dict.fromkeys(document.entities + document.wikilinks)),
                    metadata=chunk_metadata,
                )
            )
    return chunks


def chunk_documents(
    documents: Iterable[Document],
    chunk_size: int = 900,
    chunk_overlap: int = 120,
) -> list[Chunk]:
    return [
        chunk
        for document in documents
        for chunk in chunk_document(document, chunk_size, chunk_overlap)
    ]


__all__ = ["chunk_document", "chunk_documents"]
