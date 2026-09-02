"""NetworkX entity graph construction and persistence."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import networkx as nx

from gestaltx.ingest.models import Document

from .extract import extract_graph_hints
from .names import find_near_name_pairs


def _document_text(document: Document) -> str:
    return "\n\n".join(section.text for section in document.sections)


class EntityGraph:
    def __init__(self, graph: nx.MultiDiGraph | None = None) -> None:
        self.graph = graph or nx.MultiDiGraph()

    def build(self, documents: Iterable[Document]) -> "EntityGraph":
        """Add document/entity nodes and typed relationships."""
        for document in documents:
            text = _document_text(document)
            extracted_links, extracted_infobox = extract_graph_hints(text)
            links = list(dict.fromkeys(document.wikilinks + extracted_links))
            infobox = {**extracted_infobox, **document.infobox}
            entities = list(
                dict.fromkeys(
                    document.entities
                    + links
                    + ([document.subject_entity] if document.subject_entity else [])
                )
            )
            doc_node = f"document:{document.doc_id}"
            self.graph.add_node(
                doc_node,
                kind="document",
                doc_id=document.doc_id,
                title=document.title,
                path=document.path,
                tier=document.tier,
                doctype=document.doctype,
            )
            for entity in entities:
                self.graph.add_node(entity, kind="entity", name=entity)
                self.graph.add_edge(
                    doc_node,
                    entity,
                    key=f"mentions:{entity}",
                    relation="mentions",
                )
            if document.subject_entity:
                for target in links:
                    self.graph.add_edge(
                        document.subject_entity,
                        target,
                        key=f"wikilink:{document.doc_id}:{target}",
                        relation="wikilink",
                        document=document.doc_id,
                    )
                for field, raw_value in infobox.items():
                    targets, _ = extract_graph_hints(raw_value)
                    for target in targets:
                        self.graph.add_node(target, kind="entity", name=target)
                        self.graph.add_edge(
                            document.subject_entity,
                            target,
                            key=f"infobox:{document.doc_id}:{field}:{target}",
                            relation=field.casefold().replace(" ", "_"),
                            document=document.doc_id,
                        )
        self._add_near_name_warnings()
        return self

    def _add_near_name_warnings(self) -> None:
        names = [
            str(node)
            for node, data in self.graph.nodes(data=True)
            if data.get("kind") == "entity"
        ]
        for left, right, similarity in find_near_name_pairs(names):
            self.graph.nodes[left].setdefault("near_names", [])
            self.graph.nodes[right].setdefault("near_names", [])
            if right not in self.graph.nodes[left]["near_names"]:
                self.graph.nodes[left]["near_names"].append(right)
            if left not in self.graph.nodes[right]["near_names"]:
                self.graph.nodes[right]["near_names"].append(left)
            self.graph.add_edge(
                left,
                right,
                key=f"near_name:{right}",
                relation="near_name_warning",
                similarity=round(similarity, 4),
            )

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self.graph)
        destination.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return destination

    @classmethod
    def load(cls, path: str | Path) -> "EntityGraph":
        data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
        graph = nx.node_link_graph(data, directed=True, multigraph=True)
        return cls(nx.MultiDiGraph(graph))


def build_entity_graph(documents: Iterable[Document]) -> EntityGraph:
    return EntityGraph().build(documents)


__all__ = ["EntityGraph", "build_entity_graph"]
