"""Iterative local-first research loop."""

from __future__ import annotations

import re
import time
from collections.abc import Iterable, Iterator
from typing import Any

from gestaltx.tools.base import ToolRegistry

from .gap_critic import GapCritic
from .evidence import RetrievalLog
from .narrate import ResearchNarrator
from .planner import Planner
from .scratchpad import ClaimRecord, Scratchpad
from .synthesize import split_answer_sections, synthesize_answer


def _quote_span(text: str, match: re.Match[str], radius: int = 90) -> str:
    """Prefer a compact clause around the matched year/fact."""
    start = max(0, match.start() - radius)
    end = min(len(text), match.end() + radius)
    snippet = text[start:end]
    clauses = re.split(r"[;\n]", text)
    for clause in clauses:
        if match.group(0) in clause or (match.group(1) if match.lastindex else "") in clause:
            cleaned = re.sub(r"\s+", " ", clause).strip(" ,;")
            if 12 <= len(cleaned) <= 220:
                return cleaned
    cleaned = re.sub(r"\s+", " ", snippet).strip(" ,;")
    if start > 0:
        cleaned = "…" + cleaned
    if end < len(text):
        cleaned = cleaned + "…"
    return cleaned[:240]


def _source_list(rows: list[Any], limit: int = 6) -> list[str]:
    paths: list[str] = []
    for raw in rows:
        row = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
        path = str(row.get("path") or row.get("source") or row.get("doc_id") or "")
        if path and path not in paths:
            paths.append(path)
        if len(paths) >= limit:
            break
    return paths


class ResearchLoop:
    def __init__(
        self,
        tools: ToolRegistry | None = None,
        *,
        planner: Planner | None = None,
        critic: GapCritic | None = None,
        llm: Any | None = None,
        max_iterations: int = 6,
        evidence: Iterable[dict[str, Any]] | None = None,
        corpus_update: dict[str, Any] | None = None,
    ) -> None:
        self.tools = tools or ToolRegistry()
        self.planner = planner or Planner(llm)
        self.critic = critic or GapCritic()
        self.llm = llm
        self.max_iterations = max_iterations
        self.injected_evidence = list(evidence or [])
        self.corpus_update = corpus_update

    def stream(
        self,
        question: str,
        *,
        evidence: Iterable[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        if self.corpus_update:
            from gestaltx.index.watch import format_corpus_update_message

            message = format_corpus_update_message(self.corpus_update)
            if message:
                yield {
                    "event": "activity",
                    "data": {
                        "kind": "status",
                        "message": message,
                        "id": "corpus-refresh",
                    },
                }

        narrator = ResearchNarrator(self.llm)
        retrieval = RetrievalLog()
        plan = self.planner.plan(question)
        pad = Scratchpad(entities=plan.entities, intent=plan.intent, open_questions=plan.required_claims)
        yield {"event": "plan", "data": vars(plan)}
        yield {"event": "reasoning", "data": narrator.after_plan(question, plan, pad)}

        pending = list(evidence or self.injected_evidence)
        queries = iter(plan.queries or [question])
        next_action: dict[str, Any] | None = None
        iteration = 0

        for iteration in range(1, self.max_iterations + 1):
            if pending:
                action = {"tool": "injected_evidence", "query": question}
                yield {
                    "event": "activity",
                    "data": {
                        "kind": "tool_start",
                        "tool": "injected_evidence",
                        "query": question,
                        "iteration": iteration,
                        "id": f"tool-{iteration}",
                    },
                }
                rows = pending
                pending = []
            else:
                action = next_action or {"tool": "search_corpus", "query": next(queries, question)}
                tool_name = str(action.get("tool", "search_corpus"))
                query = str(action.get("query") or question)
                yield {
                    "event": "activity",
                    "data": {
                        "kind": "tool_start",
                        "tool": tool_name,
                        "query": query,
                        "iteration": iteration,
                        "id": f"tool-{iteration}",
                    },
                }
                # Brief pause so SSE clients can paint the running tool card.
                time.sleep(0.05)
                rows = self._call(action)

            row_dicts = [
                (row.model_dump() if hasattr(row, "model_dump") else dict(row))
                for row in rows
            ]
            retrieval.observe(row_dicts, query=str(action.get("query") or question))
            sources = _source_list(rows)
            yield {
                "event": "activity",
                "data": {
                    "kind": "tool_end",
                    "tool": str(action.get("tool", "search_corpus")),
                    "query": str(action.get("query") or question),
                    "iteration": iteration,
                    "id": f"tool-{iteration}",
                    "hit_count": len(rows),
                    "sources": sources,
                },
            }
            yield {"event": "tool_call", "data": {"iteration": iteration, **action}}
            # Skip redundant Search reasoning — the tool card already shows it.
            yield {"event": "tool_result", "data": {"iteration": iteration, "results": rows}}

            added = self._extract_claims(question, rows)
            for record in added:
                pad.add_claim(record)
            finding = narrator.after_finding(question, row_dicts, added, pad)
            yield {"event": "reasoning", "data": finding}

            critique = self.critic.critique(question, pad)
            yield {
                "event": "critique",
                "data": {
                    "iteration": iteration,
                    "sufficient": critique.sufficient,
                    "reasons": critique.reasons,
                    "next_action": critique.next_action,
                },
            }
            yield {
                "event": "reasoning",
                "data": narrator.after_judgment(
                    question,
                    critique,
                    pad,
                    query=str((critique.next_action or {}).get("query") or action.get("query") or ""),
                ),
            }
            if critique.sufficient:
                break
            next_action = critique.next_action

        result = synthesize_answer(
            question,
            pad,
            self.llm,
            reasoning_steps=narrator.steps,
            retrieval=retrieval,
        )
        result["iterations"] = iteration
        result["sufficient"] = self.critic.critique(question, pad).sufficient
        result["reasoning"] = narrator.steps

        sections = result.get("sections") or split_answer_sections(str(result.get("answer") or ""))
        for key in ("answer", "documents", "why", "how", "sources"):
            markdown = sections.get(key) or ""
            if markdown:
                yield {
                    "event": "answer_chunk",
                    "data": {"section": key, "markdown": markdown},
                }
                time.sleep(0.04)

        yield {"event": "answer", "data": result}

    def run(self, question: str, *, evidence: Iterable[dict[str, Any]] | None = None) -> dict[str, Any]:
        final: dict[str, Any] = {}
        for event in self.stream(question, evidence=evidence):
            if event["event"] == "answer":
                final = event["data"]
        return final

    def _call(self, action: dict[str, Any]) -> list[dict[str, Any]]:
        name = str(action.get("tool", "search_corpus"))
        if name not in self.tools:
            return []
        kwargs = {key: value for key, value in action.items() if key != "tool"}
        result = self.tools.call(name, **kwargs)
        if isinstance(result, dict):
            return result.get("results", [result])
        return list(result or [])

    @staticmethod
    def _extract_claims(question: str, rows: Iterable[Any]) -> list[ClaimRecord]:
        records: list[ClaimRecord] = []
        lower_q = question.casefold()
        kind = (
            "founding year"
            if "found" in lower_q
            else "forging year"
            if "forg" in lower_q
            else "date"
        )
        year_patterns = (
            re.compile(
                r"\b(?:founded|founding|forged|forging|established)\b[^\n.]{0,40}?\b(\d{2,4})(?:\s*AS)?\b",
                re.IGNORECASE,
            ),
            re.compile(
                r"\b(\d{2,4}\s*AS)\b[^\n.]{0,40}?\b(?:founded|founding|forged|forging)\b",
                re.IGNORECASE,
            ),
            re.compile(r"\b(?:founded|forged)\s*(?:is|:)?\s*(\d{2,4})(?:\s*AS)?\b", re.IGNORECASE),
            re.compile(r"\b(\d{2,4}\s*AS)\b", re.IGNORECASE),
        )
        for raw in rows:
            row = raw.model_dump() if hasattr(raw, "model_dump") else dict(raw)
            embedded = row.get("claims")
            if embedded:
                for claim in embedded:
                    merged = {
                        "source": row.get("source") or row.get("path") or row.get("doc_id", "injected"),
                        "tier": row.get("tier", 5),
                        "confidence": row.get("confidence", 0.7),
                        "doctype": row.get("doctype", ""),
                        "reliability": row.get("reliability"),
                        **claim,
                    }
                    records.append(ClaimRecord.model_validate(merged))
                continue
            if "claim" in row and "value" in row:
                records.append(ClaimRecord.model_validate({
                    "source": row.get("source") or row.get("path") or "injected",
                    "tier": row.get("tier", 5),
                    "confidence": row.get("confidence", 0.7),
                    **row,
                }))
                continue
            text = str(row.get("text", ""))
            year = None
            for pattern in year_patterns:
                year = pattern.search(text)
                if year:
                    break
            if year:
                value = year.group(1).strip()
                if not value.upper().endswith("AS"):
                    value = f"{value} AS"
                contested = "contested" in text.casefold() or "consult the" in text.casefold()
                if contested and int(row.get("tier", 5)) >= 2:
                    value = "Contested"
                records.append(ClaimRecord(
                    claim=kind,
                    value=value,
                    source=str(row.get("path") or row.get("source") or row.get("doc_id", "search")),
                    tier=int(row.get("tier", 5)),
                    confidence=float(row.get("confidence", row.get("score", 0.65))),
                    doctype=str(row.get("doctype", "")),
                    reliability=row.get("reliability"),
                    quote=_quote_span(text, year),
                    metadata={
                        **(row.get("metadata") or {}),
                        "contested": contested,
                    },
                ))
            else:
                # Contested / pointer passages may lack a year digit.
                contested = "contested" in text.casefold() or "consult the" in text.casefold()
                if contested and ("found" in lower_q or "forg" in lower_q or "found" in text.casefold()):
                    snippet = re.sub(r"\s+", " ", text).strip()[:220]
                    records.append(ClaimRecord(
                        claim=kind,
                        value="Contested",
                        source=str(row.get("path") or row.get("source") or row.get("doc_id", "search")),
                        tier=int(row.get("tier", 5)),
                        confidence=float(row.get("confidence", row.get("score", 0.55))),
                        doctype=str(row.get("doctype", "")),
                        reliability=row.get("reliability"),
                        quote=snippet,
                        metadata={
                            **(row.get("metadata") or {}),
                            "contested": True,
                        },
                    ))
        return records


__all__ = ["ResearchLoop"]
