from types import SimpleNamespace

from gestaltx.tools import build_default_tools


def test_registry_exposes_five_research_tools() -> None:
    registry = build_default_tools(
        SimpleNamespace(searcher=None, documents=[], graph={"entities": {}})
    )
    assert {
        "search_corpus",
        "read_section",
        "lookup_entity",
        "list_sources_about",
        "compare_claims",
    } == set(registry.names())
    for name in registry.names():
        tool = registry.get(name)
        assert tool.name == name
        assert tool.description
