"""Build GestaltX search indexes from normalized corpus files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def build(
    config_path: str | None = None,
    *,
    force: bool = False,
    dense: bool = False,
    fastembed: bool = False,
) -> Any:
    from gestaltx.config import load_config
    from gestaltx.index.pipeline import build_indexes

    config = load_config(config_path)
    return build_indexes(
        config,
        force=force,
        skip_dense=not dense,
        prefer_fastembed=fastembed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Path to GestaltX YAML configuration")
    parser.add_argument("--force", action="store_true", help="Rebuild FTS/graph from scratch")
    parser.add_argument(
        "--dense",
        action="store_true",
        help="Also build Qdrant dense vectors (slow on CPU; optional)",
    )
    parser.add_argument(
        "--fastembed",
        action="store_true",
        help="Use FastEmbed/ONNX instead of the fast hashing embedder (with --dense)",
    )
    args = parser.parse_args()
    result = build(
        args.config,
        force=args.force,
        dense=args.dense,
        fastembed=args.fastembed,
    )
    print(result if result is not None else "Indexes built successfully.")


if __name__ == "__main__":
    main()
