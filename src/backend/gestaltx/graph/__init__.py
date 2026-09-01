"""Entity extraction and graph APIs."""

from .builder import EntityGraph, build_entity_graph
from .extract import extract_graph_hints, extract_infobox, extract_wikilinks
from .names import find_near_name_pairs, name_similarity, near_names

__all__ = [
    "EntityGraph",
    "build_entity_graph",
    "extract_graph_hints",
    "extract_infobox",
    "extract_wikilinks",
    "find_near_name_pairs",
    "name_similarity",
    "near_names",
]
