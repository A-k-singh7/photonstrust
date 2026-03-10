#!/usr/bin/env python3
"""Run a multi-scenario satellite-chain sweep (local or Ray backend)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.pipeline.satellite_chain_sweep import run_satellite_chain_sweep


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run satellite-chain scenario sweep")
    parser.add_argument(
        "configs",
        nargs="*",
        help="Satellite config paths. Defaults to built-in M5 scenarios if omitted.",
    )
    parser.add_argument(
        "--output-root",
        default="results/satellite_chain_sweep",
        help="Output directory for sweep artifacts",
    )
    parser.add_argument(
        "--backend",
        choices=("local", "ray"),
        default="local",
        help="Execution backend for multi-scenario sweep",
    )
    parser.add_argument("--max-workers", type=int, default=4, help="Local backend worker count")
    parser.add_argument("--seed", type=int, default=42, help="Base deterministic seed")
    parser.add_argument(
        "--job-timeout-s",
        type=float,
        default=600.0,
        help="Per-job timeout in seconds (<=0 disables timeout)",
    )
    parser.add_argument("--max-retries", type=int, default=1, help="Retry count per failed job")
    parser.add_argument("--ray-num-cpus", type=float, default=1.0, help="Ray task cpu allocation")
    parser.add_argument(
        "--ray-memory-mb",
        type=float,
        default=None,
        help="Optional Ray task memory hint in MB",
    )
    parser.add_argument(
        "--ray-max-in-flight",
        type=int,
        default=None,
        help="Optional maximum concurrent in-flight Ray tasks",
    )
    parser.add_argument(
        "--tracking-mode",
        choices=("local_json", "mlflow", "none"),
        default="local_json",
        help="Experiment tracking backend",
    )
    parser.add_argument(
        "--tracking-uri",
        default=None,
        help="Optional tracking URI for selected tracking backend",
    )
    return parser.parse_args()


def _default_configs(repo_root: Path) -> list[Path | str]:
    return [
        repo_root / "configs" / "satellite" / "eagle1_analog_berlin.yml",
        repo_root / "configs" / "satellite" / "eagle1_analog_snspd.yml",
        repo_root / "configs" / "satellite" / "micius_analog.yml",
    ]


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    configs: list[Path | str]
    if args.configs:
        configs = [Path(value).expanduser().resolve() for value in args.configs]
    else:
        configs = _default_configs(repo_root)

    try:
        payload = run_satellite_chain_sweep(
            configs,
            output_root=Path(args.output_root),
            backend=str(args.backend),
            max_workers=int(args.max_workers),
            seed=int(args.seed),
            job_timeout_s=float(args.job_timeout_s),
            max_retries=int(args.max_retries),
            ray_num_cpus=float(args.ray_num_cpus),
            ray_memory_mb=float(args.ray_memory_mb) if args.ray_memory_mb is not None else None,
            ray_max_in_flight=int(args.ray_max_in_flight) if args.ray_max_in_flight is not None else None,
            tracking_mode=(None if str(args.tracking_mode) == "none" else str(args.tracking_mode)),
            tracking_uri=(str(args.tracking_uri).strip() if args.tracking_uri is not None else None),
        )
    except Exception as exc:
        print(
            json.dumps(
                {"ok": False, "error": f"satellite_chain_sweep_failed: {exc}"},
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 2

    summary_raw = payload.get("summary")
    summary: dict[str, object] = dict(summary_raw) if isinstance(summary_raw, dict) else {}
    lineage_raw = payload.get("lineage")
    lineage: dict[str, object] = dict(lineage_raw) if isinstance(lineage_raw, dict) else {}
    compact = {
        **summary,
        "report_path": payload.get("report_path"),
        "input_order_fingerprint": lineage.get("input_order_fingerprint"),
    }
    print(json.dumps(compact, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
