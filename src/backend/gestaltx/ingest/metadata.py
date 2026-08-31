"""Infer source tier, doctype, and reliability from corpus paths."""

from __future__ import annotations

import re
from pathlib import Path

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


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


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

    tier = FAMILY_TIER.get(family, 5)
    if family == "codex":
        reliability = 0.95
    elif family == "wiki":
        reliability = 0.65
    elif family == "chronicles":
        reliability = 0.50
    elif family == "ephemera":
        reliability = EPHEMERA_RANK.get(doctype, 0.40)
    else:
        reliability = 0.30

    doc_id = _slug("/".join(parts))
    return {
        "doc_id": doc_id,
        "path": "/".join(parts).replace("\\", "/"),
        "title": (subject or stem).replace("_", " ").title(),
        "tier": tier,
        "doctype": doctype,
        "source_family": family,
        "subject_entity": subject.title() if subject else None,
        "reliability": reliability,
    }
