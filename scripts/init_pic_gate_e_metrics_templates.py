#!/usr/bin/env python3
"""Initialize synthetic template metrics for PIC Gate E1/E3."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path


DEFAULT_OUTPUT_DIR = Path("results/pic_readiness/governance")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize PIC Gate E metric templates")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument("--release-candidate", default="rc_missing_data_2026_03_03", help="Release candidate identifier")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output files")
    return parser.parse_args()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: dict, *, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir.resolve() if args.output_dir.is_absolute() else (Path.cwd() / args.output_dir).resolve()

    ci_path = output_dir / "ci_history_metrics_2026-03-03.json"
    triage_path = output_dir / "triage_metrics_2026-03-03.json"
    manifest_path = output_dir / "gate_e_template_metrics_manifest_2026-03-03.json"

    ci_payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.ci_history_metrics",
        "generated_at": _now_iso(),
        "release_candidate": str(args.release_candidate),
        "synthetic": True,
        "window": {
            "start": "2026-02-25T00:00:00Z",
            "end": "2026-03-03T00:00:00Z",
        },
        "metrics": {
            "run_count": 28,
            "pass_rate_percent": 98.2,
            "flaky_rate_percent": 2.1,
        },
        "thresholds": {
            "min_pass_rate_percent": 95.0,
            "max_flaky_rate_percent": 3.0,
        },
        "notes": [
            "Synthetic template metrics for preflight only.",
            "Replace with exported CI telemetry before production governance signoff.",
        ],
    }

    triage_payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.triage_metrics",
        "generated_at": _now_iso(),
        "release_candidate": str(args.release_candidate),
        "synthetic": True,
        "mean_time_to_root_cause_hours": 12.5,
        "target_hours": 24.0,
        "incident_count": 14,
        "notes": [
            "Synthetic template metrics for preflight only.",
            "Replace with actual incident analytics before production governance signoff.",
        ],
    }

    _write_json(ci_path, ci_payload, force=bool(args.force))
    _write_json(triage_path, triage_payload, force=bool(args.force))

    manifest_payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_gate_e_template_metrics_manifest",
        "generated_at": _now_iso(),
        "release_candidate": str(args.release_candidate),
        "ci_history_metrics": str(ci_path),
        "triage_metrics": str(triage_path),
    }
    _write_json(manifest_path, manifest_payload, force=True)

    print(
        json.dumps(
            {
                "manifest": str(manifest_path),
                "ci_history_metrics": str(ci_path),
                "triage_metrics": str(triage_path),
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
