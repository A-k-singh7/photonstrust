#!/usr/bin/env python3
"""Build PIC Gate C + D5 preflight packet from available artifacts."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


DEFAULT_CORNER_REPORT = Path("results/corner_sweep/demo_qkd_transmitter/pic_corner_sweep.json")
DEFAULT_TAPEOUT_GATE = Path("results/pic_readiness/tapeout_gate_report.json")
DEFAULT_DECISION_PACKETS = [
    Path("results/pic_readiness/day10_decision_packet.json"),
    Path("results/pic_readiness/day10_decision_packet_repeat.json"),
    Path("results/pic_readiness/day10_decision_packet_third.json"),
]
DEFAULT_OUTPUT = Path("results/pic_readiness/process_repro/pic_c_d5_packet.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PIC Gate C + D5 preflight packet")
    parser.add_argument("--corner-report", type=Path, default=DEFAULT_CORNER_REPORT, help="PIC corner sweep report JSON")
    parser.add_argument(
        "--run-corner-demo",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run scripts/run_corner_sweep_demo.py when corner report is missing",
    )
    parser.add_argument("--tapeout-gate-report", type=Path, default=DEFAULT_TAPEOUT_GATE, help="PIC tapeout gate report JSON")
    parser.add_argument(
        "--decision-packet",
        dest="decision_packets",
        action="append",
        default=None,
        help="Path to day10 decision packet JSON. Repeat to add multiple packets.",
    )
    parser.add_argument("--yield-threshold", type=float, default=0.90, help="Minimum Monte Carlo yield fraction for C1")
    parser.add_argument(
        "--robustness-threshold",
        type=float,
        default=0.90,
        help="Minimum worst/nominal key-rate ratio for C3 perturbation robustness",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output packet JSON path")
    return parser.parse_args()


def _resolve(path: Path, *, cwd: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _as_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except Exception:
        return None
    return parsed


def _run_corner_demo(*, repo_root: Path) -> tuple[bool, str]:
    cmd = [sys.executable, str((repo_root / "scripts" / "run_corner_sweep_demo.py").resolve())]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=False)
    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    return proc.returncode == 0, output


def _metric_status(passed: bool, *, pending_reason: str | None = None) -> str:
    if passed:
        return "pass"
    if pending_reason is not None:
        return "pending"
    return "fail"


def _evaluate_gate_c(
    *,
    corner_report: dict[str, Any],
    tapeout_gate_report: dict[str, Any],
    yield_threshold: float,
    robustness_threshold: float,
) -> dict[str, Any]:
    monte = corner_report.get("monte_carlo") if isinstance(corner_report.get("monte_carlo"), dict) else {}
    risk = corner_report.get("risk_assessment") if isinstance(corner_report.get("risk_assessment"), dict) else {}
    corners = corner_report.get("corners") if isinstance(corner_report.get("corners"), dict) else {}
    nominal = corner_report.get("nominal") if isinstance(corner_report.get("nominal"), dict) else {}

    yield_fraction = _as_float(monte.get("yield_fraction_above_threshold"))
    completed_samples = int(monte.get("completed_samples", 0) or 0)
    c1_pass = yield_fraction is not None and completed_samples > 0 and yield_fraction >= float(yield_threshold)

    selected = corners.get("selected") if isinstance(corners.get("selected"), list) else []
    selected_set = {str(item).strip().upper() for item in selected}
    required = {"SS", "TT", "FF"}
    evaluated = corners.get("evaluated") if isinstance(corners.get("evaluated"), list) else []
    evaluated_status_ok = all(isinstance(row, dict) and str(row.get("status") or "").lower() == "ok" for row in evaluated)
    c2_pass = required.issubset(selected_set) and evaluated_status_ok and len(evaluated) >= len(required)

    nominal_rate = _as_float(nominal.get("key_rate_bps"))
    worst_rate = _as_float(risk.get("worst_case_key_rate_bps"))
    robustness_ratio = None
    if nominal_rate is not None and nominal_rate > 0.0 and worst_rate is not None:
        robustness_ratio = float(worst_rate / nominal_rate)
    c3_pass = robustness_ratio is not None and robustness_ratio >= float(robustness_threshold)

    all_passed = bool(tapeout_gate_report.get("all_passed") is True)
    checks = tapeout_gate_report.get("checks") if isinstance(tapeout_gate_report.get("checks"), list) else []
    foundry_signoff_pass = False
    for row in checks:
        if isinstance(row, dict) and str(row.get("name") or "") == "foundry_signoff":
            foundry_signoff_pass = bool(row.get("passed") is True)
            break
    c4_pass = all_passed and foundry_signoff_pass

    return {
        "c1_monte_carlo_yield": {
            "status": _metric_status(c1_pass),
            "yield_fraction": yield_fraction,
            "completed_samples": completed_samples,
            "threshold": float(yield_threshold),
        },
        "c2_multi_corner_closure": {
            "status": _metric_status(c2_pass),
            "required_corners": sorted(required),
            "selected_corners": sorted(selected_set),
            "evaluated_count": int(len(evaluated)),
            "all_corner_status_ok": bool(evaluated_status_ok),
        },
        "c3_perturbation_robustness": {
            "status": _metric_status(c3_pass),
            "nominal_key_rate_bps": nominal_rate,
            "worst_case_key_rate_bps": worst_rate,
            "worst_over_nominal_ratio": robustness_ratio,
            "threshold": float(robustness_threshold),
        },
        "c4_netlist_layout_replay": {
            "status": _metric_status(c4_pass),
            "tapeout_gate_all_passed": bool(all_passed),
            "foundry_signoff_pass": bool(foundry_signoff_pass),
        },
    }


def _evaluate_c5_d5(*, decision_packets: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    decisions = [str(row.get("decision") or "") for row in decision_packets]
    tapeout_flags = [bool(row.get("tapeout_all_passed") is True) for row in decision_packets]
    smoke_status = [str(row.get("smoke_overall_status") or "") for row in decision_packets]

    has_runs = len(decision_packets) >= 2
    decisions_consistent = has_runs and len(set(decisions)) == 1
    tapeout_consistent = has_runs and len(set(tapeout_flags)) == 1
    smoke_consistent = has_runs and len(set(smoke_status)) == 1
    c5_pass = has_runs and decisions_consistent and tapeout_consistent and smoke_consistent

    c5 = {
        "status": _metric_status(c5_pass, pending_reason=None if has_runs else "need at least two runs"),
        "packet_count": int(len(decision_packets)),
        "decisions": decisions,
        "tapeout_all_passed": tapeout_flags,
        "smoke_overall_status": smoke_status,
    }

    d5_pass = c5_pass
    d5 = {
        "status": _metric_status(d5_pass, pending_reason=None if has_runs else "need at least two runs"),
        "packet_count": int(len(decision_packets)),
        "decision_consistent": bool(decisions_consistent),
        "tapeout_consistent": bool(tapeout_consistent),
        "smoke_status_consistent": bool(smoke_consistent),
    }
    return c5, d5


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()
    repo_root = Path(__file__).resolve().parents[1]

    corner_report_path = _resolve(args.corner_report, cwd=cwd)
    tapeout_gate_path = _resolve(args.tapeout_gate_report, cwd=cwd)
    output_path = _resolve(args.output, cwd=cwd)

    if args.decision_packets:
        decision_packet_paths = [_resolve(Path(value), cwd=cwd) for value in args.decision_packets]
    else:
        decision_packet_paths = [_resolve(path, cwd=cwd) for path in DEFAULT_DECISION_PACKETS]

    notes: list[str] = []
    if not corner_report_path.exists() and bool(args.run_corner_demo):
        ok, output = _run_corner_demo(repo_root=repo_root)
        notes.append(f"corner_demo_ran={ok}")
        if output:
            notes.append(f"corner_demo_output={output}")

    if not corner_report_path.exists():
        raise SystemExit(f"missing corner report: {corner_report_path}")
    if not tapeout_gate_path.exists():
        raise SystemExit(f"missing tapeout gate report: {tapeout_gate_path}")

    corner_report = _load_json_object(corner_report_path)
    tapeout_gate = _load_json_object(tapeout_gate_path)

    decision_packets: list[dict[str, Any]] = []
    missing_packets: list[str] = []
    for path in decision_packet_paths:
        if not path.exists():
            missing_packets.append(str(path))
            continue
        decision_packets.append(_load_json_object(path))

    if missing_packets:
        notes.append(f"missing_decision_packets={missing_packets}")

    gate_c = _evaluate_gate_c(
        corner_report=corner_report,
        tapeout_gate_report=tapeout_gate,
        yield_threshold=float(args.yield_threshold),
        robustness_threshold=float(args.robustness_threshold),
    )
    c5, d5 = _evaluate_c5_d5(decision_packets=decision_packets)
    gate_c["c5_repeatability"] = c5

    gate_c_status = "pass" if all(str(v.get("status") or "") == "pass" for v in gate_c.values()) else "pending"
    d5_status = str(d5.get("status") or "pending")

    packet = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_gate_c_d5_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "corner_report": str(corner_report_path),
            "tapeout_gate_report": str(tapeout_gate_path),
            "decision_packets": [str(path) for path in decision_packet_paths],
            "yield_threshold": float(args.yield_threshold),
            "robustness_threshold": float(args.robustness_threshold),
        },
        "gate_c": gate_c,
        "d5_reproducibility": d5,
        "status": {
            "gate_c": gate_c_status,
            "d5": d5_status,
            "overall": "pass" if gate_c_status == "pass" and d5_status == "pass" else "pending",
        },
        "notes": notes,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    print(json.dumps({"packet": str(output_path), "overall": packet["status"]["overall"]}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
