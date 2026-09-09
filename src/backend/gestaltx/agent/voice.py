"""Impersonal voice spec: banned pronouns, slop phrases, and machine artifacts."""

from __future__ import annotations

import re

_PRONOUN_PATTERNS = (
    re.compile(r"\bwe(?:'ll| will| are| can| do| did| need| look| search| set| continue)?\b", re.I),
    re.compile(r"\bour\b", re.I),
    re.compile(r"\bus\b", re.I),
    # Avoid flagging roman numeral I in titles like "Codex Vaeloria I".
    re.compile(r"\bI(?:'m| am| will| can| checked| found| trusted)\b"),
    re.compile(r"(?:^|[.!?]\s+)I\b"),
    re.compile(r"\blet's\b", re.I),
)

_SLOP_PATTERNS = (
    re.compile(r"you can trust", re.I),
    re.compile(r"a careful reader", re.I),
    re.compile(r"someone reading", re.I),
    re.compile(r"it is important to note", re.I),
    re.compile(r"\bset aside\b", re.I),
    re.compile(r"documentary record", re.I),
    re.compile(r"the way a human", re.I),
    re.compile(r"\bdelve\b", re.I),
    re.compile(r"in conclusion", re.I),
    re.compile(r"it should be noted", re.I),
)

_ARTIFACT_PATTERNS = (
    re.compile(r"\b[\w.-]+/(?:[\w.-]+/)*[\w.-]+\.(?:pdf|docx|md|txt)\b", re.I),
    re.compile(r"\b[\w-]+\.(?:pdf|docx|md|txt)\b", re.I),
    re.compile(r"\b(?:founding|forging)\s+year\s*:", re.I),
    re.compile(r"\btier\s*\d*\b", re.I),
    re.compile(r"\barbitration\b", re.I),
    re.compile(r"\(\s*[^)]*\([^)]*\)[^)]*\)"),  # nested ((
    re.compile(r"\b[a-z]+_[a-z0-9_]+\b"),  # snake_case tokens like search_corpus
)


def violations(text: str) -> list[str]:
    """Return human-readable violation labels found in text."""
    found: list[str] = []
    for pattern in _PRONOUN_PATTERNS:
        match = pattern.search(text)
        if match:
            found.append(f"pronoun:{match.group(0)}")
    for pattern in _SLOP_PATTERNS:
        match = pattern.search(text)
        if match:
            found.append(f"slop:{match.group(0)}")
    for pattern in _ARTIFACT_PATTERNS:
        match = pattern.search(text)
        if match:
            label = match.group(0)
            # Allow snake_case only if clearly not a path-like tool dump in prose sections;
            # still flag it — callers strip Sources paths before checking.
            found.append(f"artifact:{label}")
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for item in found:
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def prose_for_voice_check(markdown: str) -> str:
    """Strip Sources / code fences so path lines do not false-positive."""
    blocks = re.split(r"\n(?=## )", markdown.strip())
    keep: list[str] = []
    for block in blocks:
        heading = block.split("\n", 1)[0].casefold()
        if heading.startswith("## sources") or heading.startswith("## evidence"):
            continue
        # Drop fenced / inline-backtick paths for voice check of Answer/Why.
        cleaned = re.sub(r"`[^`]+`", "", block)
        keep.append(cleaned)
    return "\n".join(keep)


__all__ = ["prose_for_voice_check", "violations"]
