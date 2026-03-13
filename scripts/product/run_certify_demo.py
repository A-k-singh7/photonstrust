#!/usr/bin/env python3
"""Run a local demo PIC->QKD certification flow."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.pipeline.certify import run_certify


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run demo certification on graphs/demo_qkd_transmitter.json")
    parser.add_argument(
        "--output",
        default="results/certify_demo",
        help="Output directory for certificate artifacts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip simulation/QKD sweep and run deterministic certification dry-run",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    graph_path = repo_root / "graphs" / "demo_qkd_transmitter.json"
    output_dir = Path(args.output)
    if not output_dir.is_absolute():
        output_dir = (Path.cwd() / output_dir).resolve()

    result = run_certify(
        graph_path,
        output_dir=output_dir,
        dry_run=bool(args.dry_run),
    )

    summary = {
        "graph_path": str(graph_path),
        "decision": str(result.get("decision") or ""),
        "output_path": result.get("output_path"),
        "dry_run": bool(args.dry_run),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
