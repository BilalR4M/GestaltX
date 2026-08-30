"""Source-file parser dispatch."""

from __future__ import annotations

from pathlib import Path

from ..models import Document
from .docx_parser import parse_docx
from .pdf_parser import parse_pdf
from .text import parse_text

SUPPORTED_EXTENSIONS = frozenset({".md", ".txt", ".docx", ".pdf"})


def parse_file(path: str | Path, corpus_root: str | Path | None = None) -> Document:
    """Parse a supported source file into a normalized :class:`Document`."""
    source = Path(path)
    extension = source.suffix.lower()
    if extension in {".md", ".txt"}:
        return parse_text(source, corpus_root)
    if extension == ".docx":
        return parse_docx(source, corpus_root)
    if extension == ".pdf":
        return parse_pdf(source, corpus_root)
    raise ValueError(
        f"Unsupported file type {extension or '<none>'!r}; "
        f"expected one of {sorted(SUPPORTED_EXTENSIONS)}"
    )


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "parse_docx",
    "parse_file",
    "parse_pdf",
    "parse_text",
]
