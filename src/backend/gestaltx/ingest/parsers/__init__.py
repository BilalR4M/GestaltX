"""Source-file parser dispatch."""

from __future__ import annotations

from pathlib import Path

from ..metadata import classify_document
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
        document = parse_text(source, corpus_root)
    elif extension == ".docx":
        document = parse_docx(source, corpus_root)
    elif extension == ".pdf":
        document = parse_pdf(source, corpus_root)
    else:
        raise ValueError(
            f"Unsupported file type {extension or '<none>'!r}; "
            f"expected one of {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return classify_document(document)


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "parse_docx",
    "parse_file",
    "parse_pdf",
    "parse_text",
]
