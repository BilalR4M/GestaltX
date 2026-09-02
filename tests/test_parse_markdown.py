from pathlib import Path

from gestaltx.ingest.parsers import parse_file


def test_markdown_headings_become_ordered_sections(tmp_path: Path) -> None:
    source = tmp_path / "entry.md"
    source.write_text("# Gloamreach\nFounded in dispute.\n\n## History\nSee the Codex.", encoding="utf-8")
    sections = parse_file(source).sections
    assert [section.title for section in sections] == ["Gloamreach", "History"]
    assert sections[1].order == 1
    assert "Codex" in sections[1].text


def test_plain_text_is_parseable(tmp_path: Path) -> None:
    source = tmp_path / "notice.txt"
    source.write_text("A short archive notice.", encoding="utf-8")
    sections = parse_file(source).sections
    assert len(sections) == 1
    assert "archive notice" in sections[0].text
