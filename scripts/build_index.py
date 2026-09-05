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


def build(config_path: str | None = None, *, force: bool = False) -> Any:
    from gestaltx.config import load_config

    config = load_config(config_path)
    try:
        from gestaltx.index.pipeline import build_indexes

        return build_indexes(config, force=force)
    except ImportError:
        from gestaltx.index.hybrid import HybridSearcher

        builder = getattr(HybridSearcher, "build", None)
        if builder is None:
            raise RuntimeError("No index builder is available in gestaltx.index")
        return builder(config=config, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", help="Path to GestaltX YAML configuration")
    parser.add_argument("--force", action="store_true", help="Replace existing indexes")
    args = parser.parse_args()
    result = build(args.config, force=args.force)
    print(result if result is not None else "Indexes built successfully.")


if __name__ == "__main__":
    main()
