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
    return parser.parse_args()


def _default_configs(repo_root: Path) -> list[Path]:
    return [
        repo_root / "configs" / "satellite" / "eagle1_analog_berlin.yml",
        repo_root / "configs" / "satellite" / "eagle1_analog_snspd.yml",
        repo_root / "configs" / "satellite" / "micius_analog.yml",
    ]


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    configs = [Path(value).expanduser().resolve() for value in args.configs] if args.configs else _default_configs(repo_root)

    try:
        payload = run_satellite_chain_sweep(
            configs,
            output_root=Path(args.output_root),
            backend=str(args.backend),
            max_workers=int(args.max_workers),
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

    print(json.dumps(payload.get("summary", {}), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

