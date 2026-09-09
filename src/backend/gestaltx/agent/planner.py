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
        intent = "fact"
        if any(word in lower for word in ("which source", "higher-authority", "authority", "who resolves", "what source")):
            intent = "source"
        elif any(word in lower for word in ("compare", "difference", "versus", "disagree")):
            intent = "compare"
        elif any(word in lower for word in ("when", "year", "founded", "forged")):
            intent = "date"

        entities = self._entities(question)
        required: list[str] = []
        if "found" in lower or intent == "source":
            required.append("founding year")
        if "forg" in lower:
            required.append("forging year")
        if intent == "source":
            required.append("authority source")

        focused: list[str] = []
        for entity in entities:
            if intent == "source" or "found" in lower:
                focused.extend(
                    [
                        f"{entity} founded",
                        f"{entity} founding",
                        f"{entity} Codex",
                        f"{entity} contested",
                    ]
                )
            elif "forg" in lower:
                focused.extend([f"{entity} forged", f"{entity} forging", f"{entity} Codex"])
            elif intent == "compare":
                focused.extend([f"{entity} founded", f"{entity} contested"])
            else:
                focused.append(entity)

        queries = list(dict.fromkeys([*focused, question]))
        plan = ResearchPlan(
            question=question,
            entities=entities,
            intent=intent,
            queries=queries,
            required_claims=required,
        )
        return self._llm_enhance(plan)

    @staticmethod
    def _entities(question: str) -> list[str]:
        quoted = re.findall(r"[\"“](.*?)[\"”]", question)
        proper = re.findall(r"\b(?:[A-Z][\w'-]*)(?:\s+[A-Z][\w'-]*)*\b", question)
        stop = {
            "Who", "What", "When", "Where", "Why", "How", "Which", "Consult", "Compare",
            "State", "Precise", "Year", "Age", "Shadows", "True", "Founding", "Forged",
            "Actually", "According", "Official", "The", "And", "For", "With", "Higher",
            "Authority", "Source", "Resolve", "Resolves", "Disputed", "Date", "Archive",
            "Claim", "Sample", "Question",
        }
        # Keep multi-word artifact names even if a stop token appears as a part.
        cleaned = []
        for item in proper:
            if item in stop and " " not in item:
                continue
            if len(item) <= 2:
                continue
            cleaned.append(item)
        # Explicit common entities
        for name in ("Gloamreach", "Gloammarch", "Gauntlet of Sorrowfell", "Sorrowfell"):
            if name.casefold() in question.casefold() and name not in cleaned:
                cleaned.append(name)
        cleaned.sort(key=lambda item: (-item.count(" "), -len(item)))
        return list(dict.fromkeys([*quoted, *cleaned]))

    def _llm_enhance(self, plan: ResearchPlan) -> ResearchPlan:
        if self.llm is None:
            return plan
        prompt = (
            "Return JSON only with keys entities, intent, queries, required_claims "
            "for researching this Ashen Era archive question. Prefer Codex/Annals for contested dates.\n"
            f"Question: {plan.question}"
        )
        try:
            raw = self.llm.chat(
                [{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300,
                use_cache=True,
            )
            data = json.loads(raw[raw.find("{") : raw.rfind("}") + 1])
            for key in ("entities", "queries", "required_claims"):
                value = data.get(key)
                if isinstance(value, list):
                    setattr(plan, key, list(dict.fromkeys([*getattr(plan, key), *map(str, value)])))
            if isinstance(data.get("intent"), str):
                plan.intent = data["intent"]
        except Exception:
            pass
        return plan


__all__ = ["Planner", "ResearchPlan"]
