#!/usr/bin/env python3
"""Run Optuna optimization for a satellite-chain scenario config."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from photonstrust.config import load_config
from photonstrust.pipeline.satellite_chain_optuna import optimize_satellite_chain_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Optuna optimization for satellite-chain config")
    parser.add_argument("config", help="Path to satellite-chain config file")
    parser.add_argument(
        "--output-dir",
        default="results/satellite_chain_optuna",
        help="Output directory for Optuna artifacts",
    )
    parser.add_argument("--n-trials", type=int, default=20, help="Number of Optuna trials")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for Optuna sampler")
    parser.add_argument("--study-name", default=None, help="Optional Optuna study name override")
    parser.add_argument("--storage-url", default=None, help="Optional Optuna storage URL for resume")
    parser.add_argument("--resume", action="store_true", help="Resume existing study from storage")
    parser.add_argument(
        "--tracking-mode",
        choices=("local_json", "mlflow", "none"),
        default="local_json",
        help="Experiment tracking backend",
    )
    parser.add_argument("--tracking-uri", default=None, help="Optional tracking URI override")
    return parser.parse_args()


def _summary(payload: object) -> dict[str, object]:
    report = payload if isinstance(payload, dict) else {}
    return {
        "best_value": report.get("best_value"),
        "report_path": report.get("report_path"),
        "study_name": report.get("study_name"),
        "trial_count": report.get("trial_count"),
        "storage_enabled": bool(((report.get("lineage") or {}).get("storage") or {}).get("enabled", False)),
        "resume": bool(((report.get("lineage") or {}).get("storage") or {}).get("resume", False)),
    }


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    kwargs: dict[str, Any] = {
        "output_dir": output_dir,
        "n_trials": int(args.n_trials),
        "seed": int(args.seed),
    }
    if args.study_name is not None and str(args.study_name).strip():
        kwargs["study_name"] = str(args.study_name).strip()
    if args.storage_url is not None and str(args.storage_url).strip():
        kwargs["storage_url"] = str(args.storage_url).strip()
    if bool(args.resume):
        kwargs["resume"] = True
    if str(args.tracking_mode).strip().lower() != "none":
        kwargs["tracking_mode"] = str(args.tracking_mode).strip().lower()
    else:
        kwargs["tracking_mode"] = None
    if args.tracking_uri is not None and str(args.tracking_uri).strip():
        kwargs["tracking_uri"] = str(args.tracking_uri).strip()

    try:
        config = load_config(config_path)
        payload = optimize_satellite_chain_config(config, **kwargs)
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": f"satellite_chain_optuna_failed: {exc}"},
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    print(json.dumps(_summary(payload), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
