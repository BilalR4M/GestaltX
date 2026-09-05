"""Citation-bearing answer synthesis."""

from __future__ import annotations

from typing import Any

from .arbitration import ClaimArbitrator
from .scratchpad import Scratchpad


def synthesize_answer(question: str, scratchpad: Scratchpad, llm: Any | None = None) -> dict[str, Any]:
    resolved = ClaimArbitrator().resolve(scratchpad.claims)
    winners = [record for record in resolved.values() if record is not None]
    citations = list(dict.fromkeys(record.source for record in winners))
    confidence = min((record.confidence for record in winners), default=0.0)
    facts = "; ".join(f"{record.claim}: {record.value}" for record in winners)
    answer = facts or "I could not find sufficient evidence to answer this question."

    if llm is not None and winners:
        evidence = "\n".join(
            f"- {record.claim}: {record.value} [{index + 1}]"
            for index, record in enumerate(winners)
        )
        try:
            answer = llm.chat(
                [
                    {
                        "role": "system",
                        "content": "Answer only from the evidence. Preserve citation markers exactly.",
                    },
                    {"role": "user", "content": f"Question: {question}\nEvidence:\n{evidence}"},
                ],
                temperature=0,
            )
        except Exception:
            pass
    elif winners:
        answer = ". ".join(
            f"{record.claim.capitalize()} is {record.value} [{citations.index(record.source) + 1}]"
            for record in winners
        ) + "."

    return {
        "answer": answer,
        "citations": [
            {"id": index + 1, "source": source}
            for index, source in enumerate(citations)
        ],
        "confidence": round(confidence, 3),
        "claims": [record.model_dump() for record in winners],
    }


__all__ = ["synthesize_answer"]
