"""Run release gate checks and write a machine-readable report."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _run(cmd: list[str], *, timeout_s: int | None = None) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(None if timeout_s is None else int(timeout_s)),
        )
    except subprocess.TimeoutExpired as exc:
        combined = (_as_text(exc.stdout) + "\n" + _as_text(exc.stderr)).strip()
        return False, f"timeout after {timeout_s}s\n{combined}".strip()
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode == 0, output.strip()


def _checks(*, quick: bool) -> list[dict[str, Any]]:
    python = sys.executable
    checks = [
        {
            "name": "contract_gate",
            "cmd": [python, "-m", "pytest", "-q", "tests/api/test_api_contract_v1.py"],
            "timeout_s": 300,
        },
        {
            "name": "security_gate",
            "cmd": [python, "-m", "pytest", "-q", "tests/api/test_api_auth_rbac.py"],
            "timeout_s": 300,
        },
        {
            "name": "observability_gate",
            "cmd": [python, "-m", "pytest", "-q", "tests/api/test_api_server_optional.py"],
            "timeout_s": 300,
        },
        {
            "name": "parity_gate",
            "cmd": [
                python,
                "scripts/run_protocol_engine_parity.py",
                "--strict",
                "--engines",
                "qiskit,analytic",
                "--baseline",
                "qiskit",
                "--output-dir",
                "results/release_gate/protocol_parity",
            ],
            "timeout_s": 300,
        },
        {
            "name": "uncertainty_gate",
            "cmd": [
                python,
                "-m",
                "pytest",
                "-q",
                "tests/test_satellite_chain_pipeline.py",
                "tests/test_satellite_chain_schema.py",
                "tests/test_satellite_chain_reference.py",
                "tests/test_runtime_models.py",
            ],
            "timeout_s": 300,
        },
        {
            "name": "tests",
            "cmd": [python, "-m", "pytest", "-q", "tests"],
            "timeout_s": 1800,
        },
        {
            "name": "benchmark_drift",
            "cmd": [python, "scripts/validation/check_benchmark_drift.py"],
            "timeout_s": 300,
        },
        {
            "name": "open_benchmarks",
            "cmd": [python, "scripts/validation/check_open_benchmarks.py"],
            "timeout_s": 300,
        },
        {
            "name": "pic_crosstalk_calibration_drift",
            "cmd": [python, "scripts/check_pic_crosstalk_calibration_drift.py"],
            "timeout_s": 300,
        },
        {
            "name": "recent_research_validation",
            "cmd": [python, "scripts/validation/validate_recent_research_examples.py"],
            "timeout_s": 300,
        },
        {
            "name": "qutip_parity_strict",
            "cmd": [python, "scripts/run_qutip_parity_lane.py", "--strict"],
            "timeout_s": 300,
        },
        {
            "name": "qiskit_lane",
            "cmd": [python, "scripts/run_qiskit_lane.py", "--strict"],
            "timeout_s": 300,
        },
        {
            "name": "lineage_gate",
            "cmd": [python, "scripts/replay_satellite_chain_reports.py", "--lineage-only"],
            "timeout_s": 120,
        },
        {
            "name": "repro_gate",
            "cmd": [python, "scripts/replay_satellite_chain_reports.py", "--repro-only"],
            "timeout_s": 120,
        },
    ]
    if not quick:
        return checks
    return [
        row
        for row in checks
        if row["name"]
        in {
            "contract_gate",
            "security_gate",
            "observability_gate",
            "parity_gate",
            "uncertainty_gate",
            "lineage_gate",
            "repro_gate",
            "benchmark_drift",
            "open_benchmarks",
        }
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PhotonTrust release gate checks.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/release_gate/release_gate_report.json"),
        help="Path to write release gate report JSON.",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run a reduced set of fast checks.",
    )
    args = parser.parse_args()

    checks = _checks(quick=bool(args.quick))
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quick_mode": bool(args.quick),
        "checks": [],
    }
    all_pass = True
    for item in checks:
        ok, output = _run(item["cmd"], timeout_s=item.get("timeout_s"))
        report["checks"].append(
            {
                "name": item["name"],
                "ok": bool(ok),
                "command": item["cmd"],
                "timeout_s": item.get("timeout_s"),
                "output": output,
            }
        )
        all_pass = all_pass and bool(ok)

    report["pass"] = bool(all_pass)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Release gate report written: {args.output}")
    print("Release gate: PASS" if all_pass else "Release gate: FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
