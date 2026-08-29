"""Normalized document models for the Ashen Era Archive."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Section(BaseModel):
    section_id: str
    title: str = ""
    text: str
    order: int = 0
    page_start: int | None = None
    page_end: int | None = None


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    section_id: str
    text: str
    tier: int
    doctype: str
    path: str
    entities: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    doc_id: str
    path: str
    title: str
    tier: int
    doctype: str
    source_family: str
    subject_entity: str | None = None
    reliability: float = 0.5
    sections: list[Section] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    infobox: dict[str, str] = Field(default_factory=dict)
    wikilinks: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
