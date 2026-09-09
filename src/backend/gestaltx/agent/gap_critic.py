"""Detect authority gaps, contested claims, and source pointers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .scratchpad import Scratchpad


@dataclass
class Critique:
    sufficient: bool
    reasons: list[str]
    next_action: dict[str, Any] | None = None


class GapCritic:
    POINTER = re.compile(
        r"(?:consult|see|according to)\s+(?:the\s+)?(?P<target>Annals|Codex[\w\s:'-]*)",
        re.IGNORECASE,
    )

    def critique(self, question: str, scratchpad: Scratchpad) -> Critique:
        lower = question.casefold()
        reasons: list[str] = []
        claims_text = " ".join(
            f"{item.claim} {item.value} {item.quote or ''}" for item in scratchpad.claims
        )
        all_text = f"{question} {claims_text}"

        wants_source = any(
            word in lower
            for word in ("which source", "higher-authority", "authority", "who resolves", "what source")
        )
        required = []
        if "found" in lower or wants_source:
            required.append(("founding year", ("found", "establish")))
        if "forg" in lower:
            required.append(("forging year", ("forg", "creat")))
        for label, needles in required:
            if not any(
                any(needle in item.claim.casefold() for needle in needles)
                and (
                    re.search(r"\b\d{2,4}\s*(?:AS)?\b", str(item.value), re.IGNORECASE)
                    or str(item.value).casefold() == "contested"
                )
                for item in scratchpad.claims
            ):
                reasons.append(f"missing {label}")

        values: dict[str, set[str]] = {}
        for item in scratchpad.claims:
            values.setdefault(item.claim.casefold(), set()).add(str(item.value).casefold())
        contested = "contested" in all_text.casefold() or any(len(group) > 1 for group in values.values())
        entity = next(iter(scratchpad.entities), None) or self._guess_entity(question)

        if (contested or wants_source) and not any(item.tier == 1 for item in scratchpad.claims):
            reasons.append("contested claim lacks tier-1 authority" if contested else "needs higher-authority source")
            query = f"{entity} founded Codex" if entity else f"{question} Codex"
            return Critique(
                False,
                reasons,
                {"tool": "search_corpus", "query": query, "tier": 1},
            )

        pointer = self.POINTER.search(all_text)
        if pointer and not any(pointer.group("target").casefold() in item.source.casefold() for item in scratchpad.claims):
            reasons.append(f"unfollowed pointer to {pointer.group('target').strip()}")
            target = pointer.group("target").strip()
            query = f"{entity} {target}" if entity else target
            return Critique(
                False,
                reasons,
                {"tool": "search_corpus", "query": query, "tier": 1},
            )

        if reasons:
            topic = "founded" if "founding" in " ".join(reasons) else "forged" if "forging" in " ".join(reasons) else "date"
            query = f"{entity} {topic}" if entity else f"{question} {topic}"
            return Critique(
                False,
                reasons,
                {"tool": "search_corpus", "query": query, "tier": 1},
            )
        if not scratchpad.claims:
            query = f"{entity} founded" if entity else question
            return Critique(False, ["no evidence"], {"tool": "search_corpus", "query": query})
        return Critique(True, [])

    @staticmethod
    def _guess_entity(question: str) -> str | None:
        proper = re.findall(r"\b(?:[A-Z][\w'-]*)(?:\s+[A-Z][\w'-]*)*\b", question)
        stop = {
            "Who", "What", "When", "Where", "Why", "How", "Which", "State", "Precise",
            "Year", "Age", "Shadows", "True", "Founding", "Forged", "Actually", "The",
        }
        names = [item for item in proper if item not in stop]
        names.sort(key=lambda item: (-item.count(" "), -len(item)))
        return names[0] if names else None


__all__ = ["Critique", "GapCritic"]
