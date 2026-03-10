#!/usr/bin/env python3
"""Run protocol primitive parity checks across protocol engines."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.protocols.engines import run_protocol_engine_parity


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run protocol engine parity harness")
    parser.add_argument(
        "--primitive",
        default="swap_bsm_equal_bits",
        help="Canonical primitive to compare",
    )
    parser.add_argument(
        "--engines",
        default="qiskit,analytic",
        help="Comma-separated engine ids to execute",
    )
    parser.add_argument(
        "--baseline",
        default="qiskit",
        help="Baseline engine id for absolute deltas",
    )
    parser.add_argument(
        "--threshold-abs",
        type=float,
        default=1.0e-9,
        help="Absolute threshold for success_probability",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic seed forwarded to engines",
    )
    parser.add_argument(
        "--output-dir",
        default="results/protocol_engine_parity",
        help="Output directory for JSON artifacts",
    )
    parser.add_argument(
        "--json-artifact",
        default=None,
        help="Optional explicit JSON artifact output path",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on threshold violations or baseline unavailability",
    )
    return parser.parse_args()


def _parse_engine_list(raw: str) -> list[str]:
    values: list[str] = []
    for token in str(raw or "").split(","):
        key = token.strip().lower()
        if not key or key in values:
            continue
        values.append(key)
    return values or ["qiskit", "analytic"]


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    engines = _parse_engine_list(args.engines)
    threshold_policy = {
        str(args.primitive).strip().lower(): {
            "success_probability": float(args.threshold_abs),
        }
    }
    report: dict[str, Any] = run_protocol_engine_parity(
        primitive=args.primitive,
        engine_ids=engines,
        baseline_engine_id=args.baseline,
        threshold_policy=threshold_policy,
        seed=args.seed,
    )

    strict_triggered = bool(args.strict) and (
        len(report.get("violations", [])) > 0 or not bool(report.get("baseline_available"))
    )
    status = "ok" if not strict_triggered else "failed"

    payload = {
        "kind": "protocol_engine_parity_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_mode": bool(args.strict),
        "status": status,
        "parity": report,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_dir / f"protocol_engine_parity_{stamp}.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    explicit_path = args.json_artifact
    if explicit_path:
        explicit = Path(str(explicit_path)).expanduser().resolve()
        explicit.parent.mkdir(parents=True, exist_ok=True)
        explicit.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    summary = {
        "ok": status == "ok",
        "strict_mode": bool(args.strict),
        "primitive": report.get("primitive"),
        "baseline_engine": report.get("baseline_engine"),
        "baseline_available": bool(report.get("baseline_available")),
        "violations_total": len(report.get("violations", [])),
        "report_path": str(report_path),
    }
    print(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
