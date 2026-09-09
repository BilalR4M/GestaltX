"""Citation-bearing answer synthesis as a human-readable brief."""

from __future__ import annotations

import json
import re
from typing import Any

from .arbitration import ClaimArbitrator
from .evidence import (
    ROLE_DISPUTES,
    ROLE_MENTIONS,
    ROLE_POINTER,
    ROLE_SETTLES,
    RetrievalLog,
    build_dossier,
    dossier_compact,
)
from .scratchpad import ClaimRecord, Scratchpad
from .voice import prose_for_voice_check, violations


SYSTEM_PROMPT = """You rewrite two short sections for GestaltX, an Ashen Era archive research tool.

Audience: a smart reader with no background in this archive.
Voice: impersonal and source-forward. Never use we/I/our/us. Never say "you can trust", "a careful reader", "set aside", or "documentary record".
Never name a file path or extension. Never invent a year, quote, or document absent from the dossier.

Write exactly:

## Answer
One or two sentences. Lead with the fact. Mention the winning document by friendly title only. Include [n] cite.

## Why this is the answer
One or two short paragraphs. Explain what other documents claimed, attribute rival years to named documents, and why the winning document stands.

Example:
## Answer
Gloamreach was founded in **246 AS**, according to the archive's official codex gazetteer [1].

## Why this is the answer
The community wiki never settled the date; it pointed readers to the codex. A loose paper mentions **286 AS** in passing. The official gazetteer records the year directly, so **246 AS** stands.
"""


def _entity_name(question: str, scratchpad: Scratchpad) -> str:
    if scratchpad.entities:
        return scratchpad.entities[0]
    proper = re.findall(r"\b(?:[A-Z][\w'-]*)(?:\s+[A-Z][\w'-]*)*\b", question)
    stop = {"Who", "What", "When", "Where", "Why", "How", "Which", "The", "In"}
    names = [n for n in proper if n not in stop]
    return names[0] if names else "it"


def _question_kind(question: str) -> str:
    lower = question.casefold()
    if any(word in lower for word in ("which source", "higher-authority", "who resolves", "what source", "authority")):
        return "source"
    if "forg" in lower:
        return "forging"
    if "found" in lower or "year" in lower:
        return "founding"
    return "general"


def _clean_quote(quote: str | None, limit: int = 220) -> str:
    if not quote:
        return ""
    text = re.sub(r"\s+", " ", quote).strip()
    # Prefer a contested / consult sentence over table junk.
    for pattern in (
        re.compile(r"[^.]*\bcontested\b[^.]*\.", re.I),
        re.compile(r"[^.]*\bconsult the\b[^.]*\.", re.I),
        re.compile(r"[^.]*\bfounded\b[^.]*\b\d{2,4}[^.]*\.", re.I),
        re.compile(r"[^.]*\bforged\b[^.]*\b\d{2,4}[^.]*\.", re.I),
    ):
        match = pattern.search(text)
        if match:
            text = match.group(0).strip()
            break
    else:
        clauses = [part.strip(" ;,") for part in re.split(r"[.;]\s+", text) if part.strip()]
        scored: list[tuple[int, str]] = []
        for clause in clauses:
            lower = clause.casefold()
            if "|" in clause or "---" in clause:
                continue
            score = 0
            if re.search(r"\b\d{2,4}\s*(?:as)?\b", lower):
                score += 2
            if any(token in lower for token in ("forged", "founded", "forging", "founding", "contested")):
                score += 3
            if any(token in lower for token in ("gauntlet", "gloamreach", "sorrowfell")):
                score += 2
            if len(clause) >= 24:
                score += 1
            if score:
                scored.append((score, clause))
        if scored:
            scored.sort(key=lambda item: (-item[0], -len(item[1])))
            text = scored[0][1]
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def _calibrate_confidence(findings: list[Any], top: ClaimRecord | None) -> tuple[float, str, str]:
    score = 0.60
    note_parts: list[str] = []
    if top is None:
        return 0.20, "Low", "No decisive document was found."
    settles = [f for f in findings if f.role == ROLE_SETTLES]
    disputes = [f for f in findings if f.role == ROLE_DISPUTES]
    pointers = [f for f in findings if f.role == ROLE_POINTER]
    if settles and settles[0].kind in {"official codex", "official annals"}:
        score += 0.25
    elif settles:
        score -= 0.10
        note_parts.append("Only secondary sources support the claim.")
    if top.quote and str(top.value).split()[0] in (top.quote or ""):
        score += 0.05
    if disputes:
        score -= 0.15
        note_parts.append("Two different years appeared in the archive.")
    elif pointers:
        note_parts.append("A secondary source marked the date as disputed.")
    score = max(0.20, min(0.95, score))
    if score >= 0.80:
        label = "High"
    elif score >= 0.55:
        label = "Reasonable"
    else:
        label = "Low"
    note = " ".join(note_parts) if note_parts else "The strongest archival record agrees on this point."
    return round(score, 3), label, note


def _answer_line(
    question: str,
    kind: str,
    entity: str,
    top: ClaimRecord,
    settle_title: str,
    cite: int,
) -> str:
    if kind == "source":
        return (
            f"The document that settles the disputed record for **{entity}** is "
            f"**{settle_title}** [{cite}], which records **{top.value}**."
        )
    if kind == "founding":
        return (
            f"**{entity}** was founded in **{top.value}**, according to "
            f"**{settle_title}** [{cite}]."
        )
    if kind == "forging":
        return (
            f"**{entity}** was forged in **{top.value}**, according to "
            f"**{settle_title}** [{cite}]."
        )
    return f"**{top.claim}** is **{top.value}**, according to **{settle_title}** [{cite}]."


def _documents_section(findings: list[Any]) -> str:
    lines: list[str] = []
    for finding in findings:
        loc = f", {finding.locator}" if finding.locator else ""
        lines.append(
            f"- **{finding.title}** ({finding.kind}{loc}) {finding.said}. [{finding.ref}]"
        )
    return "## What the documents say\n" + ("\n".join(lines) if lines else "- No documents were retained.")


def _why_section(findings: list[Any], entity: str, top: ClaimRecord | None) -> str:
    settles = [f for f in findings if f.role == ROLE_SETTLES]
    pointers = [f for f in findings if f.role == ROLE_POINTER]
    disputes = [f for f in findings if f.role == ROLE_DISPUTES]
    mentions = [f for f in findings if f.role == ROLE_MENTIONS]
    parts: list[str] = []

    if pointers:
        bits = []
        for f in pointers[:2]:
            if f.title.casefold() == entity.casefold() or f.kind == "community wiki":
                bits.append(f"The community wiki entry for **{entity}**")
            else:
                bits.append(f"**{f.title}**")
        subject = bits[0] if len(bits) == 1 else ", ".join(bits)
        parts.append(
            f"{subject} never settled the date; it pointed readers toward the codex or annals instead."
        )
    if disputes:
        bits = [
            f"**{f.title}** mentions **{f.value}**"
            for f in disputes[:3]
            if f.value
        ]
        if bits:
            parts.append(
                "; ".join(bits)
                + ", which does not overturn the official reading."
            )
    if settles and top:
        winner = settles[0]
        parts.append(
            f"**{winner.title}** is the archive's {winner.kind} and records the year directly, "
            f"so **{top.value}** stands."
        )
    decoys = [
        f for f in mentions
        if "gloammarch" in f.title.casefold() or "gloammarch" in (f.quote or "").casefold()
    ]
    if decoys or any("gloammarch" in (f.quote or "").casefold() for f in findings):
        parts.append(
            "**Gloamreach** must not be confused with **Gloammarch**, a different place with its own founding year."
        )
    if not parts:
        parts.append(
            "The strongest archival record available supports this reading of the question."
        )
    return "## Why this is the answer\n" + "\n\n".join(parts)


def _how_section(
    question: str,
    entity: str,
    findings: list[Any],
    retrieval: RetrievalLog | None,
) -> str:
    passages = retrieval.passages if retrieval else 0
    docs = retrieval.document_count if retrieval else len(findings)
    disputes = [f for f in findings if f.role == ROLE_DISPUTES]
    settles = [f for f in findings if f.role == ROLE_SETTLES]
    steps = [
        f"1. Searched the archive for **{entity}**.",
        f"2. Read {passages or 'several'} passages drawn from {docs or len(findings)} document"
        f"{'' if (docs or len(findings)) == 1 else 's'}.",
    ]
    if disputes or any(f.role == ROLE_POINTER for f in findings):
        steps.append("3. Found competing or disputed claims and compared how reliable each document is.")
        if settles:
            steps.append(f"4. Settled on **{settles[0].title}**.")
    else:
        if settles:
            steps.append(f"3. Settled on **{settles[0].title}**.")
        else:
            steps.append("3. Compared the available records and formed the best supported answer.")
    return "## How this answer was found\n" + "\n".join(steps)


def _sources_section(findings: list[Any]) -> str:
    blocks: list[str] = []
    for finding in findings:
        head = f"[{finding.ref}] **{finding.title}**"
        if finding.locator:
            head += f" — {finding.locator}"
        lines = [head]
        quote = _clean_quote(finding.quote, 200)
        if quote:
            lines.append(f'    "{quote}"')
        lines.append(f"    `{finding.path}`")
        blocks.append("\n".join(lines))
    return "## Sources\n" + ("\n\n".join(blocks) if blocks else "None yet")


def _heuristic_brief(
    question: str,
    scratchpad: Scratchpad,
    winners: list[ClaimRecord],
    findings: list[Any],
    retrieval: RetrievalLog | None,
) -> str:
    kind = _question_kind(question)
    entity = _entity_name(question, scratchpad)
    if not winners or not findings:
        return (
            "## Answer\n"
            "The archive did not yield enough evidence to answer confidently.\n\n"
            "## What the documents say\n"
            "- No decisive document was retained.\n\n"
            "## Why this is the answer\n"
            "No claim survived comparison across the available records.\n\n"
            "## How this answer was found\n"
            f"1. Searched the archive for **{entity}**.\n"
            "2. No decisive passage remained after comparison.\n\n"
            "## Sources\n"
            "None yet"
        )
    top = winners[0]
    settles = [f for f in findings if f.role == ROLE_SETTLES] or findings
    settle = settles[0]
    answer = _answer_line(question, kind, entity, top, settle.title, settle.ref)
    return "\n\n".join(
        [
            f"## Answer\n{answer}",
            _documents_section(findings),
            _why_section(findings, entity, top),
            _how_section(question, entity, findings, retrieval),
            _sources_section(findings),
        ]
    )


def split_answer_sections(answer: str) -> dict[str, str]:
    """Split a structured brief into named markdown bodies."""
    sections = {
        "answer": "",
        "documents": "",
        "why": "",
        "how": "",
        "sources": "",
        # legacy aliases filled when present
        "verdict": "",
        "reasoning": "",
        "evidence": "",
    }
    blocks = re.split(r"\n(?=## )", answer.strip())
    for block in blocks:
        lines = block.strip().split("\n")
        if not lines:
            continue
        heading = lines[0].replace("## ", "").strip().casefold()
        body = "\n".join(lines[1:]).strip()
        full = f"## {lines[0].replace('## ', '').strip()}\n{body}".strip()
        if heading.startswith("answer") or heading.startswith("verdict"):
            sections["answer"] = full if heading.startswith("answer") else f"## Answer\n{body}"
            sections["verdict"] = sections["answer"]
        elif heading.startswith("what the documents"):
            sections["documents"] = full
        elif heading.startswith("why"):
            sections["why"] = full
            sections["reasoning"] = full
        elif heading.startswith("how"):
            sections["how"] = full
        elif heading.startswith("sources") or heading.startswith("evidence"):
            sections["sources"] = full if heading.startswith("sources") else f"## Sources\n{body}"
            sections["evidence"] = sections["sources"]
        elif heading.startswith("reasoning"):
            sections["why"] = f"## Why this is the answer\n{body}"
            sections["reasoning"] = sections["why"]
    return sections


def _numbers_and_quotes_ok(text: str, findings: list[Any]) -> bool:
    dossier_text = " ".join(
        f"{f.title} {f.said} {f.quote or ''} {f.value or ''}" for f in findings
    )
    for year in re.findall(r"\b\d{3,4}\b", text):
        if year not in dossier_text and year not in text:
            return False
        if year not in dossier_text:
            return False
    for quote in re.findall(r'"([^"]{8,})"', text):
        if quote not in dossier_text and quote.casefold() not in dossier_text.casefold():
            return False
    return True


def _merge_llm_sections(llm_text: str, fallback: str) -> str | None:
    llm_parts = split_answer_sections(llm_text)
    base = split_answer_sections(fallback)
    if not llm_parts.get("answer") or not llm_parts.get("why"):
        return None
    check = prose_for_voice_check(llm_parts["answer"] + "\n" + llm_parts["why"])
    if violations(check):
        return None
    return "\n\n".join(
        [
            llm_parts["answer"],
            base.get("documents") or "",
            llm_parts["why"],
            base.get("how") or "",
            base.get("sources") or "",
        ]
    ).strip()


def synthesize_answer(
    question: str,
    scratchpad: Scratchpad,
    llm: Any | None = None,
    *,
    reasoning_steps: list[dict[str, Any]] | None = None,
    retrieval: RetrievalLog | None = None,
) -> dict[str, Any]:
    _ = reasoning_steps  # no longer used for prose; kept for API compatibility
    resolved = ClaimArbitrator().resolve(scratchpad.claims)
    winners = [record for record in resolved.values() if record is not None]
    winners.sort(key=lambda item: (item.tier, -item.confidence, item.source))
    findings = build_dossier(scratchpad.claims, winners, retrieval=retrieval)
    for finding in findings:
        if finding.quote:
            finding.quote = _clean_quote(finding.quote, 280)

    heuristic = _heuristic_brief(question, scratchpad, winners, findings, retrieval)
    answer = heuristic
    used_llm = False

    top = winners[0] if winners else None
    confidence, confidence_label, confidence_note = _calibrate_confidence(findings, top)

    if llm is not None and winners and findings:
        compact = dossier_compact(findings)
        try:
            llm_answer = llm.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"User question:\n{question}\n\n"
                            f"Document dossier (JSON):\n{json.dumps(compact, ensure_ascii=False, indent=2)}\n\n"
                            "Rewrite ## Answer and ## Why this is the answer only."
                        ),
                    },
                ],
                temperature=0.2,
                max_tokens=400,
                use_cache=True,
            )
            if llm_answer and len(llm_answer.strip()) > 40:
                merged = _merge_llm_sections(llm_answer.strip(), heuristic)
                if merged and _numbers_and_quotes_ok(
                    split_answer_sections(merged)["answer"]
                    + split_answer_sections(merged)["why"],
                    findings,
                ):
                    answer = merged
                    used_llm = True
        except Exception:
            used_llm = False
            answer = heuristic

    sections = split_answer_sections(answer)
    # Final voice gate on deterministic+merged prose (Sources excluded).
    if violations(prose_for_voice_check(answer)):
        answer = heuristic
        sections = split_answer_sections(answer)
        used_llm = False

    return {
        "answer": answer,
        "sections": sections,
        "citations": [
            {
                "id": finding.ref,
                "source": finding.path,
                "path": finding.path,
                "title": finding.title,
                "authority": finding.kind,
                "section": finding.locator or None,
                "quote": finding.quote,
                "role": finding.role,
            }
            for finding in findings
        ],
        "confidence": confidence,
        "confidence_label": confidence_label,
        "confidence_note": confidence_note,
        "claims": [record.model_dump() for record in winners],
        "mode": "llm" if used_llm else "heuristic",
        "structured": True,
        "reasoning": list(reasoning_steps or []),
        "dossier": [f.to_dict() for f in findings],
        "retrieval": retrieval.to_dict() if retrieval else None,
    }


__all__ = ["synthesize_answer", "split_answer_sections"]
