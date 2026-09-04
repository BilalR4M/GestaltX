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

        required = []
        if "found" in lower:
            required.append(("founding year", ("found", "establish")))
        if "forg" in lower:
            required.append(("forging year", ("forg", "creat")))
        for label, needles in required:
            if not any(
                any(needle in item.claim.casefold() for needle in needles)
                and re.search(r"\b\d{2,4}\s*(?:AS)?\b", str(item.value), re.IGNORECASE)
                for item in scratchpad.claims
            ):
                reasons.append(f"missing {label}")

        values: dict[str, set[str]] = {}
        for item in scratchpad.claims:
            values.setdefault(item.claim.casefold(), set()).add(str(item.value).casefold())
        contested = "contested" in all_text.casefold() or any(len(group) > 1 for group in values.values())
        if contested and not any(item.tier == 1 for item in scratchpad.claims):
            reasons.append("contested claim lacks tier-1 authority")
            return Critique(
                False,
                reasons,
                {"tool": "search_corpus", "query": question + " Codex", "tiers": [1]},
            )

        pointer = self.POINTER.search(all_text)
        if pointer and not any(pointer.group("target").casefold() in item.source.casefold() for item in scratchpad.claims):
            reasons.append(f"unfollowed pointer to {pointer.group('target').strip()}")
            return Critique(
                False,
                reasons,
                {"tool": "search_corpus", "query": pointer.group("target").strip(), "tiers": [1, 3]},
            )

        if reasons:
            return Critique(
                False,
                reasons,
                {"tool": "search_corpus", "query": f"{question} {' '.join(reasons)}", "tiers": [1, 2, 3]},
            )
        if not scratchpad.claims:
            return Critique(False, ["no evidence"], {"tool": "search_corpus", "query": question})
        return Critique(True, [])


__all__ = ["Critique", "GapCritic"]
