"""Run focused Qiskit backend lane checks.

This lane validates that the optional Qiskit backend is installed and that the
repeater primitive probability cross-check remains deterministic.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.physics.backends.qiskit_backend import QiskitBackend


def _is_finite_number(value: Any) -> bool:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return False
    return candidate == candidate and candidate not in {float("inf"), float("-inf")}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run focused Qiskit backend lane.")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/qiskit_lane/qiskit_lane_report.json"),
        help="Path to write machine-readable lane report.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when Qiskit is missing or lane checks fail.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1.0e-12,
        help="Absolute tolerance for repeater primitive formula-vs-circuit parity.",
    )
    args = parser.parse_args()

    qiskit_spec = importlib.util.find_spec("qiskit")
    qiskit_available = qiskit_spec is not None
    qiskit_version = None
    if qiskit_available:
        qiskit_mod = importlib.import_module("qiskit")
        qiskit_version = str(getattr(qiskit_mod, "__version__", "unknown"))

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_mode": bool(args.strict),
        "status": "ok",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "qiskit_available": bool(qiskit_available),
            "qiskit_version": qiskit_version,
        },
        "summary": {},
    }

    if not qiskit_available:
        report["status"] = "skipped"
        report["summary"] = {
            "ok": False,
            "reason": "qiskit dependency not installed",
        }
    else:
        backend = QiskitBackend()
        result = backend.simulate("repeater_primitive", {"tolerance": float(args.tolerance)}, seed=123)
        summary = result.get("summary", {})
        absolute_delta = summary.get("absolute_delta")
        lane_ok = bool(
            result.get("status") == "pass"
            and _is_finite_number(summary.get("formula_probability"))
            and _is_finite_number(summary.get("circuit_probability"))
            and _is_finite_number(absolute_delta)
            and float(absolute_delta) <= float(args.tolerance)
        )
        report["summary"] = {
            "ok": lane_ok,
            "result_status": result.get("status"),
            "backend_summary": summary,
            "tolerance": float(args.tolerance),
        }
        if not lane_ok:
            report["status"] = "fail"

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Qiskit lane report written: {args.output_json}")
    print(f"Qiskit lane: {'PASS' if report['status'] == 'ok' else 'FAIL'}")

    if not args.strict:
        return 0
    return 0 if report["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
