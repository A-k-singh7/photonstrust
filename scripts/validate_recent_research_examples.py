"""Validate model behavior against literature-anchored research examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.benchmarks.research_validation import run_research_validation_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run recent research example validation suite.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/research_validation/recent_research_validation_report.json"),
        help="Path to write JSON report.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report = run_research_validation_suite(repo_root=repo_root)

    output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if bool(report.get("ok", False)):
        print("Recent research validation: PASS")
        print(str(output_path))
        return 0

    print("Recent research validation: FAIL")
    for row in report.get("checks") or []:
        if bool(row.get("ok", False)):
            continue
        name = str(row.get("name") or "check")
        print(f" - {name}")
        for line in row.get("details") or []:
            print(f"   * {line}")
    print(str(output_path))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
