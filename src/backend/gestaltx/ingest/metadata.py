"""Infer source tier, doctype, and reliability from corpus paths."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

EPHEMERA_RANK = {
    "decree": 0.72,
    "trial_transcript": 0.70,
    "quartermaster_ledger": 0.68,
    "field_report": 0.55,
    "contract": 0.54,
    "petition": 0.52,
    "interrogation_record": 0.40,
    "auction_catalogue": 0.38,
    "ballad": 0.25,
    "letter": 0.45,
}

FAMILY_TIER = {
    "codex": 1,
    "wiki": 2,
    "chronicles": 3,
    "ephemera": 4,
    "images": 5,
}

# Filename stem keywords → source family (used when no folder family is present).
_STEM_FAMILY_KEYWORDS: list[tuple[str, str]] = [
    ("gazetteer", "codex"),
    ("annal", "codex"),
    ("codex", "codex"),
    ("wiki", "wiki"),
    ("chronicle", "chronicles"),
    ("ledger", "ephemera"),
    ("decree", "ephemera"),
    ("letter", "ephemera"),
    ("ballad", "ephemera"),
    ("petition", "ephemera"),
    ("transcript", "ephemera"),
]

_CODEX_HEADING = re.compile(
    r"(?im)^\s{0,3}#+\s+.*\b(codex|annals?\s+of|official\s+gazetteer)\b"
)
_WIKI_INFOBOX = re.compile(r"(?is)\{\{\s*infobox|\|\s*-\s*\|\s*[^\n|]+\s*\|\s*")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _reliability_for(family: str, doctype: str) -> float:
    if family == "codex":
        return 0.95
    if family == "wiki":
        return 0.65
    if family == "chronicles":
        return 0.50
    if family == "ephemera":
        return EPHEMERA_RANK.get(doctype, 0.40)
    if family == "images":
        return 0.30
    return 0.30


def _family_from_stem(stem: str) -> str | None:
    lower = stem.casefold()
    for keyword, family in _STEM_FAMILY_KEYWORDS:
        if keyword in lower:
            return family
    return None


def _apply_family_fields(meta: dict[str, Any], family: str, stem: str) -> None:
    """Fill doctype / tier / reliability for a resolved family."""
    doctype = meta.get("doctype") or family
    subject = meta.get("subject_entity")
    if family == "wiki" and doctype in {"wiki", "unknown", family}:
        doctype = "wiki_article"
        if not subject:
            subject = stem.replace("_", " ").title()
    elif family == "codex" and doctype in {"codex", "unknown", family}:
        doctype = "codex"
    elif family == "chronicles" and doctype in {"chronicles", "unknown", family, "chronicle"}:
        doctype = "chronicle"
    elif family == "ephemera":
        # Keep a more specific doctype already set from concerning_ pattern.
        if doctype in {"ephemera", "unknown", family}:
            for keyword, mapped in _STEM_FAMILY_KEYWORDS:
                if mapped == "ephemera" and keyword in stem.casefold():
                    doctype = keyword if keyword != "transcript" else "trial_transcript"
                    break
            else:
                doctype = "ephemera"

    meta["source_family"] = family
    meta["doctype"] = doctype
    meta["tier"] = FAMILY_TIER.get(family, 5)
    meta["reliability"] = _reliability_for(family, str(doctype))
    if subject and not meta.get("subject_entity"):
        meta["subject_entity"] = subject
    if subject and (not meta.get("title") or meta["title"] == stem.replace("_", " ").title()):
        meta["title"] = subject if isinstance(subject, str) else meta["title"]


def infer_metadata(path: str | Path, corpus_root: str | Path | None = None) -> dict:
    """Derive tier/doctype/subject metadata from a corpus-relative path."""
    p = Path(path)
    parts = list(p.parts)
    if corpus_root is not None:
        try:
            parts = list(Path(path).resolve().relative_to(Path(corpus_root).resolve()).parts)
        except Exception:  # noqa: BLE001
            parts = list(Path(path).parts)

    family = "unknown"
    for candidate in ("codex", "wiki", "chronicles", "ephemera", "images"):
        if candidate in parts:
            family = candidate
            break

    stem = p.stem
    # strip .scan from names like foo.scan.pdf -> stem may be foo.scan
    if stem.endswith(".scan"):
        stem = stem[: -len(".scan")]

    doctype = family
    subject = None
    m = re.match(r"^(?P<doctype>[a-z_]+)_concerning_(?P<subject>.+)$", stem)
    if m:
        doctype = m.group("doctype")
        subject = m.group("subject").replace("_", " ")
    elif family == "wiki":
        doctype = "wiki_article"
        subject = stem.replace("_", " ")
    elif family == "codex":
        doctype = "codex"
    elif family == "chronicles":
        doctype = "chronicle"

    classification: dict[str, Any] | None = None
    if family == "unknown":
        inferred = _family_from_stem(stem)
        if inferred:
            family = inferred
            classification = {"inferred": True, "basis": "filename"}
            if family == "wiki":
                doctype = "wiki_article"
                subject = subject or stem.replace("_", " ")
            elif family == "codex":
                doctype = "codex"
            elif family == "chronicles":
                doctype = "chronicle"
            elif family == "ephemera" and doctype == "unknown":
                for keyword, mapped in _STEM_FAMILY_KEYWORDS:
                    if mapped == "ephemera" and keyword in stem.casefold():
                        doctype = keyword if keyword != "transcript" else "trial_transcript"
                        break

    tier = FAMILY_TIER.get(family, 5)
    reliability = _reliability_for(family, doctype) if family != "unknown" else 0.30

    doc_id = _slug("/".join(parts))
    result = {
        "doc_id": doc_id,
        "path": "/".join(parts).replace("\\", "/"),
        "title": (subject or stem).replace("_", " ").title(),
        "tier": tier,
        "doctype": doctype,
        "source_family": family,
        "subject_entity": subject.title() if subject else None,
        "reliability": reliability,
    }
    if classification:
        result["classification"] = classification
    return result


def classify_document(document: Any) -> Any:
    """Content-level fallback when path/filename left ``source_family`` unknown.

    Mutates and returns the document. Unresolved files become tier-3 chronicles
    so they compete in arbitration without overriding official sources.
    """
    family = str(getattr(document, "source_family", "") or "").casefold()
    if family and family != "unknown":
        return document

    text_parts: list[str] = []
    for section in getattr(document, "sections", []) or []:
        title = getattr(section, "title", "") or ""
        body = getattr(section, "text", "") or ""
        text_parts.append(f"{title}\n{body}")
    text = "\n".join(text_parts)
    sample = text[:4000]

    stem = Path(str(getattr(document, "path", "") or "notes")).stem
    meta = {
        "doctype": getattr(document, "doctype", "unknown"),
        "subject_entity": getattr(document, "subject_entity", None),
        "title": getattr(document, "title", stem),
    }

    basis = "default"
    resolved: str | None = None
    if _CODEX_HEADING.search(sample):
        resolved = "codex"
        basis = "content"
    elif getattr(document, "wikilinks", None) or getattr(document, "infobox", None) or _WIKI_INFOBOX.search(sample):
        # Wikilink / infobox shape → community wiki.
        if getattr(document, "wikilinks", None) or getattr(document, "infobox", None) or "[[" in sample:
            resolved = "wiki"
            basis = "content"

    if resolved:
        _apply_family_fields(meta, resolved, stem)
        document.source_family = meta["source_family"]
        document.doctype = meta["doctype"]
        document.tier = meta["tier"]
        document.reliability = meta["reliability"]
        if meta.get("subject_entity"):
            document.subject_entity = meta["subject_entity"]
        if meta.get("title"):
            document.title = meta["title"]
        document.metadata = {
            **(getattr(document, "metadata", None) or {}),
            "classification": {"inferred": True, "basis": basis},
        }
        return document

    # Mid-trust default: competitive chronicle, not authoritative.
    document.source_family = "chronicles"
    document.doctype = "chronicle"
    document.tier = 3
    document.reliability = 0.45
    document.metadata = {
        **(getattr(document, "metadata", None) or {}),
        "classification": {"inferred": True, "basis": "default"},
    }
    return document


__all__ = ["EPHEMERA_RANK", "FAMILY_TIER", "classify_document", "infer_metadata"]
