"""Rule-based research planning with an optional LLM assist."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ResearchPlan:
    question: str
    entities: list[str] = field(default_factory=list)
    intent: str = "fact"
    queries: list[str] = field(default_factory=list)
    required_claims: list[str] = field(default_factory=list)


class Planner:
    def __init__(self, llm: Any | None = None) -> None:
        self.llm = llm

    def plan(self, question: str) -> ResearchPlan:
        lower = question.casefold()
        intent = "compare" if any(word in lower for word in ("compare", "difference", "versus")) else "fact"
        if any(word in lower for word in ("when", "year", "founded", "forged")):
            intent = "date"
        entities = self._entities(question)
        required = []
        if "found" in lower:
            required.append("founding year")
        if "forg" in lower:
            required.append("forging year")
        plan = ResearchPlan(
            question=question,
            entities=entities,
            intent=intent,
            queries=[question, *[f"{entity} {intent}" for entity in entities]],
            required_claims=required,
        )
        return self._llm_enhance(plan)

    @staticmethod
    def _entities(question: str) -> list[str]:
        quoted = re.findall(r"[\"“](.*?)[\"”]", question)
        proper = re.findall(r"\b(?:[A-Z][\w'-]*)(?:\s+[A-Z][\w'-]*)*\b", question)
        stop = {"Who", "What", "When", "Where", "Why", "How", "Which", "Consult", "Compare"}
        return list(dict.fromkeys([*quoted, *(item for item in proper if item not in stop)]))

    def _llm_enhance(self, plan: ResearchPlan) -> ResearchPlan:
        if self.llm is None:
            return plan
        prompt = (
            "Return JSON only with entities, intent, queries, required_claims for this question: "
            + plan.question
        )
        try:
            raw = self.llm.chat([{"role": "user", "content": prompt}], temperature=0)
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            for key in ("entities", "queries", "required_claims"):
                value = data.get(key)
                if isinstance(value, list):
                    setattr(plan, key, list(dict.fromkeys(getattr(plan, key) + value)))
            if isinstance(data.get("intent"), str):
                plan.intent = data["intent"]
        except Exception:
            pass
        return plan


__all__ = ["Planner", "ResearchPlan"]
