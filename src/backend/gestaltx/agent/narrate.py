"""Human-readable research narration for chain-of-thought UX."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from .evidence import document_kind
from .scratchpad import ClaimRecord, Scratchpad


PHASE_THOUGHT = "thought"
PHASE_SEARCH = "search"
PHASE_FINDING = "finding"
PHASE_JUDGMENT = "judgment"


def _entity(scratchpad: Scratchpad, question: str) -> str:
    if scratchpad.entities:
        return scratchpad.entities[0]
    import re

    names = re.findall(r"\b(?:[A-Z][\w'-]*)(?:\s+[A-Z][\w'-]*)*\b", question)
    stop = {"Who", "What", "When", "Where", "Why", "How", "Which", "The", "In"}
    names = [n for n in names if n not in stop]
    return names[0] if names else "the subject"


def _kind(question: str) -> str:
    lower = question.casefold()
    if any(w in lower for w in ("which source", "higher-authority", "authority", "who resolves")):
        return "source"
    if "forg" in lower:
        return "forging"
    if "found" in lower:
        return "founding"
    return "fact"


def _source_paths(rows: list[dict[str, Any]], limit: int = 5) -> list[str]:
    paths: list[str] = []
    for row in rows:
        path = str(row.get("path") or row.get("source") or row.get("doc_id") or "")
        if path and path not in paths:
            paths.append(path)
        if len(paths) >= limit:
            break
    return paths


def _readable_chips(claims: list[ClaimRecord], limit: int = 4) -> list[str]:
    out: list[str] = []
    for claim in claims:
        kind = document_kind(claim.source, claim.tier, claim.metadata or {})
        value = str(claim.value)
        label = f"{value} — {kind}"
        if label not in out:
            out.append(label)
        if len(out) >= limit:
            break
    return out


def _value_conflicts(claims: list[ClaimRecord]) -> dict[str, list[str]]:
    by_claim: dict[str, set[str]] = defaultdict(set)
    for claim in claims:
        value = str(claim.value).strip()
        if value:
            by_claim[claim.claim.casefold()].add(value)
    return {key: sorted(values) for key, values in by_claim.items() if len(values) > 1}


class ResearchNarrator:
    """Build first-class reasoning steps with impersonal short narratives."""

    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm
        self._step = 0
        self.steps: list[dict[str, Any]] = []

    def _emit(
        self,
        phase: str,
        title: str,
        narrative: str,
        *,
        query: str | None = None,
        sources: list[str] | None = None,
        highlights: list[str] | None = None,
    ) -> dict[str, Any]:
        self._step += 1
        step = {
            "step": self._step,
            "phase": phase,
            "title": title,
            "narrative": narrative,
            "query": query,
            "sources": sources or [],
            "highlights": highlights or [],
        }
        self.steps.append(step)
        return step

    def after_plan(self, question: str, plan: Any, scratchpad: Scratchpad) -> dict[str, Any]:
        entity = _entity(scratchpad, question)
        kind = _kind(question)
        queries = list(getattr(plan, "queries", []) or [])
        first_query = queries[0] if queries else question

        if kind == "source":
            title = f"Identify what settles {entity}"
            narrative = (
                f"The question asks which document settles the disputed record for **{entity}**, "
                "not merely which year appears most often."
            )
        elif kind == "forging":
            title = f"Ask when {entity} was forged"
            narrative = (
                f"The question asks for the forging year of **{entity}**. "
                "Popular tellings may disagree with the official armory."
            )
        elif kind == "founding":
            title = f"Ask when {entity} was founded"
            narrative = (
                f"The question asks for the founding year of **{entity}**. "
                "Contested wiki notes and near-name places like Gloammarch are possible traps."
            )
        else:
            title = f"Frame the question about {entity}"
            narrative = f"Clarify what the archive must prove about **{entity}**, then compare sources."

        scratchpad.notes.append(f"{title}: {narrative}")
        return self._emit(
            PHASE_THOUGHT,
            title,
            narrative,
            query=first_query,
            sources=list(getattr(plan, "entities", []) or []),
        )

    def after_search(self, question: str, action: dict[str, Any], scratchpad: Scratchpad) -> dict[str, Any] | None:
        # Tool cards already show the live search; skip a redundant Search step.
        _ = (question, action, scratchpad)
        return None

    def after_finding(
        self,
        question: str,
        rows: list[dict[str, Any]],
        added: list[ClaimRecord],
        scratchpad: Scratchpad,
    ) -> dict[str, Any]:
        entity = _entity(scratchpad, question)
        sources = _source_paths(rows)
        highlights = _readable_chips(added)
        conflicts = _value_conflicts(added)
        contested = any(
            str(c.value).casefold() == "contested" or (c.metadata or {}).get("contested")
            for c in added
        )
        has_tier1 = any(c.tier == 1 for c in added)

        if conflicts:
            values = []
            for group in conflicts.values():
                values.extend(group)
            shown = ", ".join(f"**{v}**" for v in values[:4])
            title = "Sources disagree on the date"
            narrative = (
                f"Passages about **{entity}** disagree ({shown}). "
                "Comparing how reliable each document is."
            )
        elif contested and not has_tier1:
            title = "Wiki leaves the date disputed"
            narrative = (
                f"Secondary notes about **{entity}** call the date disputed and point to the codex or annals."
            )
        elif has_tier1:
            top = next(c for c in added if c.tier == 1)
            title = "Official codex gives a clear year"
            narrative = (
                f"An official codex passage records **{top.value}** for **{entity}**."
            )
        elif added:
            title = "Claims appear in the hits"
            narrative = f"{len(added)} claim(s) about **{entity}** were extracted for comparison."
        else:
            title = "No clean date yet"
            narrative = f"These hits do not yet give a clean year for **{entity}**."

        scratchpad.notes.append(f"{title}: {narrative}")
        return self._emit(
            PHASE_FINDING,
            title,
            narrative,
            sources=sources,
            highlights=highlights,
        )

    def after_judgment(
        self,
        question: str,
        critique: Any,
        scratchpad: Scratchpad,
        *,
        query: str | None = None,
    ) -> dict[str, Any]:
        entity = _entity(scratchpad, question)
        reasons = list(getattr(critique, "reasons", []) or [])
        sufficient = bool(getattr(critique, "sufficient", False))
        next_action = getattr(critique, "next_action", None) or {}
        conflicts = _value_conflicts(scratchpad.claims)

        if sufficient:
            title = "Enough to answer"
            winners = [c for c in scratchpad.claims if c.tier == 1] or list(scratchpad.claims)
            if winners:
                top = min(winners, key=lambda c: (c.tier, -c.confidence))
                narrative = (
                    f"The strongest record gives **{top.value}** for **{entity}**."
                )
                if conflicts:
                    other_vals = []
                    for values in conflicts.values():
                        other_vals.extend(v for v in values if v != str(top.value))
                    if other_vals:
                        narrative += (
                            f" Rival figures such as **{other_vals[0]}** appear in weaker notes."
                        )
            else:
                narrative = f"Enough archive evidence remains to answer about **{entity}**."
        else:
            next_q = str(next_action.get("query") or query or "")
            reason_text = "; ".join(reasons) if reasons else "a remaining evidence gap"
            if "tier-1" in reason_text.casefold() or "authority" in reason_text.casefold() or "pointer" in reason_text.casefold():
                title = "Need a stronger source"
                narrative = (
                    "Current notes are disputed or incomplete. "
                    "Next search targets the codex or annals"
                    + (f" (`{next_q}`)" if next_q else "")
                    + f" for **{entity}**."
                )
            else:
                title = "Still missing a piece"
                narrative = (
                    f"Evidence is still incomplete ({reason_text}). "
                    f"Continuing for **{entity}**"
                    + (f" via `{next_q}`" if next_q else "")
                    + "."
                )

        scratchpad.notes.append(f"{title}: {narrative}")
        return self._emit(
            PHASE_JUDGMENT,
            title,
            narrative,
            query=str(next_action.get("query") or query or "") or None,
            highlights=reasons,
        )


__all__ = [
    "PHASE_FINDING",
    "PHASE_JUDGMENT",
    "PHASE_SEARCH",
    "PHASE_THOUGHT",
    "ResearchNarrator",
]
