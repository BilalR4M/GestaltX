"""Structured working memory for iterative research."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ClaimRecord(BaseModel):
    claim: str
    value: Any
    source: str
    tier: int = Field(ge=1, le=5)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    doctype: str = ""
    reliability: float | None = None
    quote: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Scratchpad(BaseModel):
    claims: list[ClaimRecord] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    intent: str = "research"
    notes: list[str] = Field(default_factory=list)

    def add_claim(self, claim: ClaimRecord | dict[str, Any]) -> ClaimRecord:
        record = claim if isinstance(claim, ClaimRecord) else ClaimRecord.model_validate(claim)
        key = (record.claim.casefold(), str(record.value).casefold(), record.source)
        if all(
            (old.claim.casefold(), str(old.value).casefold(), old.source) != key
            for old in self.claims
        ):
            self.claims.append(record)
        return record

    def to_context(self) -> str:
        lines = [f"Intent: {self.intent}", f"Entities: {', '.join(self.entities) or 'unknown'}"]
        if self.claims:
            lines.append("Claims:")
            lines.extend(
                f"- {item.claim}: {item.value} [{item.source}; tier {item.tier}; "
                f"confidence {item.confidence:.2f}]"
                for item in self.claims
            )
        if self.open_questions:
            lines.append("Open questions:")
            lines.extend(f"- {question}" for question in self.open_questions)
        return "\n".join(lines)


__all__ = ["ClaimRecord", "Scratchpad"]
