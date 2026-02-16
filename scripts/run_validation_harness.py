"""Run canonical benchmark validation harness and emit structured artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.benchmarks.validation_harness import run_validation_harness


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PhotonTrust canonical validation harness")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/validation"),
        help="Directory under which timestamped harness artifacts are written.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    summary = run_validation_harness(repo_root=repo_root, output_root=args.output_root)

    print(json.dumps(summary, indent=2))
    return 0 if bool(summary.get("ok", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
