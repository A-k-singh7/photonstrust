"""Run release gate checks and write a machine-readable report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PhotonTrust release gate checks.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/release_gate/release_gate_report.json"),
        help="Path to write release gate report JSON.",
    )
    args = parser.parse_args()

    checks = [
        {"name": "tests", "cmd": [sys.executable, "-m", "pytest", "-q"]},
        {
            "name": "benchmark_drift",
            "cmd": [sys.executable, "scripts/check_benchmark_drift.py"],
        },
        {
            "name": "open_benchmarks",
            "cmd": [sys.executable, "scripts/check_open_benchmarks.py"],
        },
        {
            "name": "pic_crosstalk_calibration_drift",
            "cmd": [sys.executable, "scripts/check_pic_crosstalk_calibration_drift.py"],
        },
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": [],
    }
    all_pass = True
    for item in checks:
        ok, output = _run(item["cmd"])
        report["checks"].append(
            {
                "name": item["name"],
                "ok": ok,
                "command": item["cmd"],
                "output": output,
            }
        )
        all_pass = all_pass and ok

    report["pass"] = all_pass
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Release gate report written: {args.output}")
    print("Release gate: PASS" if all_pass else "Release gate: FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
