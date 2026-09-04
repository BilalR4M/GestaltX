"""Iterative local-first research loop."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import Any

from gestaltx.tools.base import ToolRegistry

from .gap_critic import GapCritic
from .planner import Planner
from .scratchpad import ClaimRecord, Scratchpad
from .synthesize import synthesize_answer


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
    ) -> None:
        self.tools = tools or ToolRegistry()
        self.planner = planner or Planner(llm)
        self.critic = critic or GapCritic()
        self.llm = llm
        self.max_iterations = max_iterations
        self.injected_evidence = list(evidence or [])

    def stream(
        self,
        question: str,
        *,
        evidence: Iterable[dict[str, Any]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        plan = self.planner.plan(question)
        pad = Scratchpad(entities=plan.entities, intent=plan.intent, open_questions=plan.required_claims)
        yield {"event": "plan", "data": vars(plan)}
        pending = list(evidence or self.injected_evidence)
        queries = iter(plan.queries or [question])
        next_action: dict[str, Any] | None = None

        for iteration in range(1, self.max_iterations + 1):
            if pending:
                rows, action = pending, {"tool": "injected_evidence"}
                pending = []
            else:
                action = next_action or {"tool": "search_corpus", "query": next(queries, question)}
                rows = self._call(action)
            yield {"event": "tool_call", "data": {"iteration": iteration, **action}}
            yield {"event": "tool_result", "data": {"iteration": iteration, "results": rows}}

            added = self._extract_claims(question, rows)
            for record in added:
                pad.add_claim(record)
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
            if critique.sufficient:
                break
            next_action = critique.next_action

        result = synthesize_answer(question, pad, self.llm)
        result["iterations"] = iteration
        result["sufficient"] = self.critic.critique(question, pad).sufficient
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
            year = re.search(r"\b(\d{2,4}\s*AS)\b", text, re.IGNORECASE)
            if year:
                lower = question.casefold()
                kind = "founding year" if "found" in lower else "forging year" if "forg" in lower else "date"
                records.append(ClaimRecord(
                    claim=kind,
                    value=year.group(1),
                    source=str(row.get("path") or row.get("source") or row.get("doc_id", "search")),
                    tier=int(row.get("tier", 5)),
                    confidence=float(row.get("confidence", row.get("score", 0.65))),
                    doctype=str(row.get("doctype", "")),
                    reliability=row.get("reliability"),
                    quote=text,
                    metadata=row.get("metadata", {}),
                ))
        return records


__all__ = ["ResearchLoop"]
