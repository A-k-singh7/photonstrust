#!/usr/bin/env python3
"""Lineage and reproducibility checks for satellite sweep/optuna reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate satellite sweep/optuna lineage and replay fingerprints")
    parser.add_argument(
        "--sweep-report",
        default="results/satellite_chain_sweep/satellite_chain_sweep.json",
        help="Path to satellite sweep report JSON",
    )
    parser.add_argument(
        "--optuna-report",
        default="results/satellite_chain_optuna/satellite_chain_optuna_report.json",
        help="Path to satellite optuna report JSON",
    )
    parser.add_argument("--lineage-only", action="store_true", help="Run lineage checks only")
    parser.add_argument("--repro-only", action="store_true", help="Run replay checks only")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if bool(args.lineage_only) and bool(args.repro_only):
        print(json.dumps({"ok": False, "error": "lineage-only and repro-only are mutually exclusive"}))
        return 2

    run_lineage = not bool(args.repro_only)
    run_repro = not bool(args.lineage_only)

    sweep_path = Path(args.sweep_report).expanduser().resolve()
    optuna_path = Path(args.optuna_report).expanduser().resolve()

    checks: list[dict[str, Any]] = []
    ok = True

    try:
        sweep = _load_json(sweep_path)
    except Exception as exc:
        checks.append({"name": "load_sweep_report", "ok": False, "error": str(exc)})
        sweep = None
        ok = False

    try:
        optuna = _load_json(optuna_path)
    except Exception as exc:
        checks.append({"name": "load_optuna_report", "ok": False, "error": str(exc)})
        optuna = None
        ok = False

    if run_lineage and isinstance(sweep, dict):
        errors = check_sweep_lineage(sweep)
        checks.append({"name": "sweep_lineage", "ok": len(errors) == 0, "errors": errors})
        ok = ok and len(errors) == 0
    if run_repro and isinstance(sweep, dict):
        errors = check_sweep_repro(sweep)
        checks.append({"name": "sweep_repro", "ok": len(errors) == 0, "errors": errors})
        ok = ok and len(errors) == 0

    if run_lineage and isinstance(optuna, dict):
        errors = check_optuna_lineage(optuna)
        checks.append({"name": "optuna_lineage", "ok": len(errors) == 0, "errors": errors})
        ok = ok and len(errors) == 0
    if run_repro and isinstance(optuna, dict):
        errors = check_optuna_repro(optuna)
        checks.append({"name": "optuna_repro", "ok": len(errors) == 0, "errors": errors})
        ok = ok and len(errors) == 0

    payload = {
        "ok": bool(ok),
        "sweep_report": str(sweep_path),
        "optuna_report": str(optuna_path),
        "checks": checks,
    }
    print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    return 0 if ok else 1


def check_sweep_lineage(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lineage = report.get("lineage") if isinstance(report.get("lineage"), dict) else None
    if lineage is None:
        return ["missing lineage"]

    for key in (
        "seed",
        "seed_source",
        "seed_strategy",
        "input_order_fingerprint",
        "backend_metadata",
        "execution_policy",
    ):
        if key not in lineage:
            errors.append(f"missing lineage.{key}")

    runs = report.get("runs")
    if not isinstance(runs, list) or not runs:
        errors.append("runs missing or empty")
    else:
        for idx, row in enumerate(runs):
            if not isinstance(row, dict):
                errors.append(f"runs[{idx}] not object")
                continue
            for key in (
                "row_index",
                "mission_id",
                "config_path",
                "config_hash",
                "seed",
                "status",
                "attempts",
            ):
                if key not in row:
                    errors.append(f"runs[{idx}] missing {key}")
    return errors


def check_sweep_repro(report: dict[str, Any]) -> list[str]:
    lineage = report.get("lineage") if isinstance(report.get("lineage"), dict) else {}
    expected = str(lineage.get("input_order_fingerprint") or "").strip()
    if not expected:
        return ["missing lineage.input_order_fingerprint"]

    runs_raw = report.get("runs")
    if not isinstance(runs_raw, list) or not runs_raw:
        return ["runs missing or empty"]

    rows = [row for row in runs_raw if isinstance(row, dict)]
    rows.sort(key=lambda row: int(row.get("row_index", 0) or 0))
    payload = [
        {
            "row_index": int(row.get("row_index", 0) or 0),
            "mission_id": str(row.get("mission_id") or ""),
            "config_path": str(row.get("config_path") or ""),
            "config_hash": str(row.get("config_hash") or ""),
        }
        for row in rows
    ]
    actual = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if actual != expected:
        return ["lineage.input_order_fingerprint mismatch"]
    return []


def check_optuna_lineage(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    lineage = report.get("lineage") if isinstance(report.get("lineage"), dict) else None
    if lineage is None:
        return ["missing lineage"]

    for key in (
        "seed",
        "seed_source",
        "seed_strategy",
        "objective_config_hash",
        "study_metadata",
        "storage",
        "backend_metadata",
        "replay_fingerprint",
    ):
        if key not in lineage:
            errors.append(f"missing lineage.{key}")

    trials = report.get("trials")
    if not isinstance(trials, list) or not trials:
        errors.append("trials missing or empty")
    else:
        for idx, row in enumerate(trials):
            if not isinstance(row, dict):
                errors.append(f"trials[{idx}] not object")
                continue
            for key in ("trial", "value", "params", "seed", "state", "trial_lineage"):
                if key not in row:
                    errors.append(f"trials[{idx}] missing {key}")
    return errors


def check_optuna_repro(report: dict[str, Any]) -> list[str]:
    lineage = report.get("lineage") if isinstance(report.get("lineage"), dict) else {}
    expected = str(lineage.get("replay_fingerprint") or "").strip()
    if not expected:
        return ["missing lineage.replay_fingerprint"]

    trials_raw = report.get("trials")
    if not isinstance(trials_raw, list) or not trials_raw:
        return ["trials missing or empty"]

    rows = [row for row in trials_raw if isinstance(row, dict)]
    rows.sort(
        key=lambda row: (
            -float(row.get("value", 0.0) or 0.0),
            int(row.get("trial", 0) or 0),
        )
    )
    payload = [
        {
            "trial": int(row.get("trial", 0) or 0),
            "value": float(row.get("value", 0.0) or 0.0),
            "seed": int(row.get("seed", 0) or 0),
            "params": dict(row.get("params") or {}),
        }
        for row in rows
    ]
    actual = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    if actual != expected:
        return ["lineage.replay_fingerprint mismatch"]
    return []


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"report not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"report must be object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
