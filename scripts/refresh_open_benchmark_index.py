"""Refresh open benchmark index.json from on-disk benchmark bundles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.benchmarks._paths import open_benchmarks_dir
from photonstrust.benchmarks.open_index import rebuild_open_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild PhotonTrust open benchmark index.")
    parser.add_argument(
        "--open-root",
        type=Path,
        default=None,
        help="Path to open benchmark registry root (defaults to datasets/benchmarks/open).",
    )
    args = parser.parse_args()

    open_root = Path(args.open_root) if args.open_root is not None else open_benchmarks_dir()
    open_root.mkdir(parents=True, exist_ok=True)

    records = rebuild_open_index(open_root)
    index_path = open_root / "index.json"
    index_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    print(f"Rebuilt open benchmark index with {len(records)} records")
    print(str(index_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
