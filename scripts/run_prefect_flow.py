#!/usr/bin/env python3
"""Run deterministic WS4 nightly orchestration flows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from photonstrust.ops.prefect_flows import run_nightly_flow


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WS4 nightly flow scaffolding")
    parser.add_argument(
        "--flow",
        required=True,
        choices=["satellite", "corner", "compliance"],
        help="Nightly job to execute.",
    )
    parser.add_argument("--config", type=Path, default=None, help="Optional config path.")
    parser.add_argument("--output-dir", type=Path, required=True, help="Artifact output directory.")
    parser.add_argument(
        "--mode",
        default="local",
        choices=["local", "prefect"],
        help="Execution mode (default: local).",
    )
    args = parser.parse_args()

    try:
        result = run_nightly_flow(
            flow=args.flow,
            config=args.config,
            output_dir=args.output_dir,
            mode=args.mode,
        )
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception as exc:
        payload = {
            "ok": False,
            "flow": args.flow,
            "mode": args.mode,
            "error": f"run_prefect_flow_failed: {exc}",
        }
        print(json.dumps(payload, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
