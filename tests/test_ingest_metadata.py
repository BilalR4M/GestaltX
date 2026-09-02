from pathlib import Path

from gestaltx.ingest.metadata import infer_metadata


def test_codex_metadata_has_highest_authority(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    path = root / "codex" / "gazetteer.md"
    metadata = infer_metadata(path, root)
    assert metadata["source_family"] == "codex"
    assert metadata["tier"] == 1
    assert metadata["reliability"] > 0.9


def test_ephemera_doctype_is_inferred() -> None:
    metadata = infer_metadata("ephemera/decree_concerning_gloamreach.txt")
    assert metadata["doctype"] == "decree"
    assert metadata["subject_entity"] == "Gloamreach"
