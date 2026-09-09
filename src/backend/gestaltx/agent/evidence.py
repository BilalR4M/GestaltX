"""Document dossier: friendly titles, kinds, locators, and per-document roles."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .scratchpad import ClaimRecord


ROLE_SETTLES = "settles"
ROLE_DISPUTES = "disputes"
ROLE_POINTER = "pointer"
ROLE_MENTIONS = "mentions"


@dataclass
class DocumentFinding:
    ref: int
    title: str
    kind: str
    locator: str
    said: str
    quote: str | None
    role: str
    path: str
    value: str | None = None
    claim: str | None = None
    tier: int = 5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalLog:
    passages: int = 0
    documents: set[str] = field(default_factory=set)
    queries: list[str] = field(default_factory=list)

    def observe(self, rows: list[dict[str, Any]], *, query: str | None = None) -> None:
        self.passages += len(rows)
        if query:
            self.queries.append(query)
        for row in rows:
            path = str(row.get("path") or row.get("source") or row.get("doc_id") or "")
            if path:
                self.documents.add(path)

    @property
    def document_count(self) -> int:
        return len(self.documents)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passages": self.passages,
            "document_count": self.document_count,
            "documents": sorted(self.documents),
            "queries": list(self.queries),
        }


def _title_case_words(text: str) -> str:
    small = {"of", "the", "and", "a", "an", "in", "on", "for", "to", "vs"}
    parts = text.split()
    out: list[str] = []
    for index, word in enumerate(parts):
        lower = word.casefold()
        if index > 0 and lower in small:
            out.append(lower)
        elif word.isupper() and len(word) <= 3:
            out.append(word)
        else:
            out.append(word[:1].upper() + word[1:].lower() if word else word)
    return " ".join(out)


def friendly_title(path: str, metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    raw = str(meta.get("title") or "").strip()
    if not raw:
        stem = Path(path.replace("\\", "/")).stem
        raw = stem.replace("_", " ").replace("-", " ")
    cleaned = re.sub(r"\s+", " ", raw).strip()
    # Insert colon after volume numeral: "Codex Vaeloria I Gazetteer..." -> "... I: Gazetteer..."
    cleaned = re.sub(
        r"\b(Codex\s+Vaeloria\s+[IVXLC]+)\s+(Gazetteer|Armory|Annals)\b",
        r"\1: \2",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(Annals\s+of\s+[\w']+)\s+(Volume)\b",
        r"\1: \2",
        cleaned,
        flags=re.IGNORECASE,
    )
    titled = _title_case_words(cleaned)
    # Keep roman numerals uppercase after title-case.
    titled = re.sub(r"\b([ivxlc]+)\b", lambda m: m.group(1).upper(), titled)
    titled = re.sub(r"\bOf\b", "of", titled)
    titled = re.sub(r"\bThe\b", "the", titled)
    titled = re.sub(r"\bAnd\b", "and", titled)
    # Restore leading capital.
    if titled:
        titled = titled[0].upper() + titled[1:]
    return titled


def document_kind(path: str, tier: int, metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    family = str(meta.get("source_family") or meta.get("doctype") or "").casefold()
    lower = path.casefold()
    if "codex" in family or "codex" in lower or tier == 1 and "annals" not in lower:
        if "annals" in lower:
            return "official annals"
        return "official codex"
    if "annals" in family or "annals" in lower or (tier == 1 and "annals" in lower):
        return "official annals"
    if "wiki" in family or "wiki" in lower or tier == 2:
        return "community wiki"
    if "chronicle" in family or "chronicles" in lower or tier == 3:
        return "chronicle"
    return "loose paper"


def locator_for(metadata: dict[str, Any] | None = None) -> str:
    meta = metadata or {}
    start = meta.get("page_start")
    end = meta.get("page_end")
    if start is not None:
        if end is not None and end != start:
            return f"pages {start}–{end}"
        return f"page {start}"
    section = str(meta.get("section_title") or "").strip()
    # Ignore section titles that merely repeat the document name or a bare Page N.
    if section and not re.fullmatch(r"Page\s+\d+", section, flags=re.I):
        title = str(meta.get("title") or "").casefold()
        generic = {"infobox", "overview", "summary", "contents", "index"}
        if section.casefold() in generic:
            return ""
        if section.casefold() not in title and title not in section.casefold():
            return section
    return ""


def _normalize_work_key(title: str, path: str) -> str:
    stem = Path(path.replace("\\", "/")).stem.casefold()
    stem = re.sub(r"\.(pdf|docx|md|txt)$", "", stem)
    if title:
        return re.sub(r"[^a-z0-9]+", "", title.casefold())
    return re.sub(r"[^a-z0-9]+", "", stem)


def _said_for(
    record: ClaimRecord,
    *,
    role: str,
    kind: str,
) -> str:
    value = str(record.value)
    contested = bool((record.metadata or {}).get("contested")) or value.casefold() == "contested"
    if role == ROLE_POINTER or contested:
        return (
            "calls the founding date disputed and tells readers to consult the "
            "codex or annals instead"
            if "found" in record.claim.casefold()
            else "marks the claim as disputed and points to a higher authority"
        )
    if role == ROLE_DISPUTES:
        return f"mentions **{value}**, which conflicts with the settled reading"
    if role == ROLE_SETTLES:
        if "found" in record.claim.casefold():
            return f"states the founding year plainly: **{value}**"
        if "forg" in record.claim.casefold():
            return f"states the forging year plainly: **{value}**"
        return f"records **{record.claim}** as **{value}**"
    # mentions
    if kind == "loose paper":
        return f"mentions **{value}** in passing, not as a settled record"
    return f"mentions **{value}**"


def build_dossier(
    claims: list[ClaimRecord],
    winners: list[ClaimRecord],
    *,
    retrieval: RetrievalLog | None = None,
) -> list[DocumentFinding]:
    """Build one DocumentFinding per work, ordered settles → pointers → disputes → mentions."""
    winner_by_claim = {w.claim.casefold(): w for w in winners}
    winner_sources = {w.source for w in winners}

    # Prefer claim rows; also surface paths seen in retrieval that lack claims.
    by_work: dict[str, dict[str, Any]] = {}
    for record in claims:
        meta = record.metadata or {}
        title = friendly_title(record.source, meta)
        key = _normalize_work_key(title, record.source)
        bucket = by_work.setdefault(
            key,
            {
                "title": title,
                "path": record.source,
                "tier": record.tier,
                "metadata": meta,
                "records": [],
            },
        )
        # Prefer lower tier / codex path as canonical.
        if record.tier < bucket["tier"]:
            bucket["tier"] = record.tier
            bucket["path"] = record.source
            bucket["metadata"] = meta
            bucket["title"] = title
        elif record.tier == bucket["tier"] and record.source.endswith(".pdf"):
            bucket["path"] = record.source
        bucket["records"].append(record)

    findings: list[DocumentFinding] = []
    for bucket in by_work.values():
        records: list[ClaimRecord] = bucket["records"]
        meta = bucket["metadata"] or {}
        kind = document_kind(bucket["path"], int(bucket["tier"]), meta)
        loc = locator_for(meta)

        # Pick the most informative record for this work.
        primary = min(records, key=lambda r: (r.tier, -r.confidence, r.source))
        for claim_key, winner in winner_by_claim.items():
            match = next((r for r in records if r.claim.casefold() == claim_key), None)
            if match is None:
                continue
            if match.source == winner.source or (
                str(match.value).casefold() == str(winner.value).casefold()
                and match.tier == winner.tier
            ):
                role = ROLE_SETTLES
                primary = match
                break
            if str(match.value).casefold() == "contested" or (match.metadata or {}).get("contested"):
                role = ROLE_POINTER
                primary = match
                break
            if str(match.value).casefold() != str(winner.value).casefold():
                role = ROLE_DISPUTES
                primary = match
                break
        else:
            if primary.source in winner_sources or any(
                str(r.value).casefold() == str(winner_by_claim.get(r.claim.casefold(), primary).value).casefold()
                and r.tier <= 1
                for r in records
                if r.claim.casefold() in winner_by_claim
            ):
                role = ROLE_SETTLES
            elif any(
                str(r.value).casefold() == "contested" or (r.metadata or {}).get("contested")
                for r in records
            ):
                role = ROLE_POINTER
                primary = next(
                    r
                    for r in records
                    if str(r.value).casefold() == "contested" or (r.metadata or {}).get("contested")
                )
            elif any(
                r.claim.casefold() in winner_by_claim
                and str(r.value).casefold() != str(winner_by_claim[r.claim.casefold()].value).casefold()
                for r in records
            ):
                role = ROLE_DISPUTES
            else:
                role = ROLE_MENTIONS

        quote = (primary.quote or "").strip() or None
        findings.append(
            DocumentFinding(
                ref=0,  # assigned after sort
                title=bucket["title"],
                kind=kind,
                locator=loc,
                said=_said_for(primary, role=role, kind=kind),
                quote=quote,
                role=role,
                path=bucket["path"],
                value=str(primary.value) if primary.value is not None else None,
                claim=primary.claim,
                tier=int(bucket["tier"]),
            )
        )

    role_order = {
        ROLE_SETTLES: 0,
        ROLE_POINTER: 1,
        ROLE_DISPUTES: 2,
        ROLE_MENTIONS: 3,
    }
    findings.sort(key=lambda f: (role_order.get(f.role, 9), f.tier, f.title.casefold()))
    for index, finding in enumerate(findings, start=1):
        finding.ref = index
    return findings


def dossier_compact(findings: list[DocumentFinding]) -> list[dict[str, Any]]:
    return [
        {
            "ref": f.ref,
            "title": f.title,
            "kind": f.kind,
            "locator": f.locator,
            "said": f.said,
            "quote": f.quote,
            "role": f.role,
            "value": f.value,
        }
        for f in findings
    ]


__all__ = [
    "DocumentFinding",
    "ROLE_DISPUTES",
    "ROLE_MENTIONS",
    "ROLE_POINTER",
    "ROLE_SETTLES",
    "RetrievalLog",
    "build_dossier",
    "document_kind",
    "dossier_compact",
    "friendly_title",
    "locator_for",
]
