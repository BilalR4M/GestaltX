"""PDF text extraction with an optional RapidOCR fallback."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from ..metadata import infer_metadata
from ..models import Document, Section

_SHORT_TEXT_THRESHOLD = 80


def _ocr_pages(pdf: Any) -> list[str] | None:
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        return None

    engine = RapidOCR()
    output: list[str] = []
    for page in pdf:
        pixmap = page.get_pixmap(dpi=200, alpha=False)
        channels = pixmap.n
        image = np.frombuffer(pixmap.samples, dtype=np.uint8).reshape(
            pixmap.height, pixmap.width, channels
        )
        result, _ = engine(image)
        output.append("\n".join(item[1] for item in (result or []) if len(item) > 1))
    return output


def parse_pdf(path: str | Path, corpus_root: str | Path | None = None) -> Document:
    """Extract one section per PDF page, using OCR for scans or sparse text."""
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - depends on optional package
        raise RuntimeError("PDF parsing requires the 'pymupdf' package") from exc

    source = Path(path)
    metadata = infer_metadata(source, corpus_root)
    pdf = fitz.open(str(source))
    try:
        pages = [page.get_text("text").strip() for page in pdf]
        requires_ocr = ".scan." in source.name.lower() or len("".join(pages).strip()) < _SHORT_TEXT_THRESHOLD
        used_ocr = False
        if requires_ocr:
            try:
                ocr_pages = _ocr_pages(pdf)
            except Exception as exc:  # OCR must not make readable PDFs fail
                warnings.warn(
                    f"OCR failed for {source.name}: {exc}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                ocr_pages = []
            if ocr_pages is not None and len("".join(ocr_pages).strip()) > len(
                "".join(pages).strip()
            ):
                pages = ocr_pages
                used_ocr = True
            elif ocr_pages is None:
                warnings.warn(
                    f"OCR requested for {source.name}, but rapidocr-onnxruntime is unavailable",
                    RuntimeWarning,
                    stacklevel=2,
                )
    finally:
        pdf.close()

    sections = [
        Section(
            section_id=f"{metadata['doc_id']}:section:{index:04d}",
            title=f"Page {index + 1}",
            text=text,
            order=index,
            page_start=index + 1,
            page_end=index + 1,
        )
        for index, text in enumerate(pages)
        if text
    ]
    if not sections:
        sections.append(
            Section(
                section_id=f"{metadata['doc_id']}:section:0000",
                title="Page 1",
                text="",
                order=0,
                page_start=1,
                page_end=1,
            )
        )
    subject = metadata["subject_entity"]
    classification = metadata.pop("classification", None)
    nested = {
        "extension": ".pdf",
        "page_count": len(pages),
        "ocr_attempted": requires_ocr,
        "ocr_used": used_ocr,
    }
    if classification:
        nested["classification"] = classification
    return Document(
        **metadata,
        sections=sections,
        entities=[subject] if subject else [],
        metadata=nested,
    )


parse = parse_pdf
