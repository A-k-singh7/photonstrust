#!/usr/bin/env python3
"""Build consolidated PIC foundry-readiness scorecard from gate packets."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


DEFAULT_TAPEOUT_GATE = Path("results/pic_readiness/tapeout_gate_report.json")
DEFAULT_GATE_B = Path("results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json")
DEFAULT_GATE_CD5 = Path("results/pic_readiness/process_repro/pic_c_d5_packet_2026-03-03.json")
DEFAULT_GATE_E = Path("results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json")
DEFAULT_OUTPUT = Path("results/pic_readiness/scorecard/pic_readiness_scorecard_2026-03-03.json")

WEIGHTS = {
    "A": 35.0,
    "B": 25.0,
    "C": 15.0,
    "D": 15.0,
    "E": 10.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build consolidated PIC readiness scorecard")
    parser.add_argument("--tapeout-gate", type=Path, default=DEFAULT_TAPEOUT_GATE, help="Tapeout gate report JSON")
    parser.add_argument("--gate-b", type=Path, default=DEFAULT_GATE_B, help="Gate B packet JSON")
    parser.add_argument("--gate-cd5", type=Path, default=DEFAULT_GATE_CD5, help="Gate C+D5 packet JSON")
    parser.add_argument("--gate-e", type=Path, default=DEFAULT_GATE_E, help="Gate E packet JSON")
    parser.add_argument(
        "--pending-credit",
        type=float,
        default=0.5,
        help="Score factor for pending/preflight gate status (0..1)",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output scorecard JSON path")
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


def _norm_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"pass", "ok", "true"}:
        return "pass"
    if text in {"fail", "false", "error"}:
        return "fail"
    if text.startswith("preflight_pass"):
        return "pending"
    if text in {"pending", "pending_ci_history_required", "pending_silicon_required", "evidence_ready_pending_timeseries"}:
        return "pending"
    return "pending"


def _gate_a_status(tapeout: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    checks_obj = tapeout.get("checks")
    checks: list[Any] = checks_obj if isinstance(checks_obj, list) else []
    all_passed = bool(tapeout.get("all_passed") is True)
    reasons: list[str] = []
    foundry_signoff_pass = False
    required_artifacts_pass = False
    non_mock_backend_ok = True
    summary_paths: list[str] = []

    for row in checks:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "")
        passed = bool(row.get("passed") is True)
        if name == "required_artifacts":
            required_artifacts_pass = passed
        if name == "foundry_signoff":
            foundry_signoff_pass = passed
            details = row.get("details") if isinstance(row.get("details"), dict) else {}
            summaries_obj = details.get("summaries")
            summaries: list[Any] = summaries_obj if isinstance(summaries_obj, list) else []
            for summary in summaries:
                if not isinstance(summary, dict):
                    continue
                path = summary.get("path")
                if isinstance(path, str) and path:
                    summary_paths.append(path)
                backend = str(summary.get("execution_backend") or "")
                if backend.strip().lower() == "mock":
                    non_mock_backend_ok = False

    if not all_passed:
        reasons.append("tapeout_gate all_passed=false")
    if not required_artifacts_pass:
        reasons.append("required_artifacts check failed")
    if not foundry_signoff_pass:
        reasons.append("foundry_signoff check failed")
    if not non_mock_backend_ok:
        reasons.append("mock backend detected in foundry summaries")

    missing_summary_files: list[str] = []
    for raw in summary_paths:
        path = Path(raw)
        if not path.exists():
            missing_summary_files.append(str(path))
    if missing_summary_files:
        reasons.append("missing foundry summary artifacts")

    status = "pass" if not reasons else "fail"
    details = {
        "all_passed": all_passed,
        "required_artifacts_pass": required_artifacts_pass,
        "foundry_signoff_pass": foundry_signoff_pass,
        "non_mock_backend_ok": non_mock_backend_ok,
        "missing_summary_files": missing_summary_files,
    }
    return status, reasons, details


def _gate_b_status(gate_b: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    status = _norm_status(gate_b.get("overall_gate_b_status"))
    metrics_obj = gate_b.get("metrics")
    metrics: dict[str, Any] = metrics_obj if isinstance(metrics_obj, dict) else {}

    notes: list[str] = []
    details: dict[str, Any] = {}
    for key in ["b1_insertion_loss", "b2_resonance_alignment", "b3_crosstalk", "b4_delay_rc", "b5_drift"]:
        row = metrics.get(key) if isinstance(metrics.get(key), dict) else {}
        metric_status = _norm_status(row.get("status"))
        details[key] = metric_status
        if metric_status == "fail":
            notes.append(f"{key} failed")

    return status, notes, details


def _gate_c_status(gate_cd5: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    status_block = gate_cd5.get("status") if isinstance(gate_cd5.get("status"), dict) else {}
    gate_c = _norm_status(status_block.get("gate_c"))
    notes: list[str] = []
    if gate_c == "fail":
        notes.append("gate_c status fail")
    gate_c_obj = gate_cd5.get("gate_c") if isinstance(gate_cd5.get("gate_c"), dict) else {}
    details: dict[str, Any] = {}
    for key in ["c1_monte_carlo_yield", "c2_multi_corner_closure", "c3_perturbation_robustness", "c4_netlist_layout_replay", "c5_repeatability"]:
        row = gate_c_obj.get(key) if isinstance(gate_c_obj.get(key), dict) else {}
        details[key] = _norm_status(row.get("status"))
    return gate_c, notes, details


def _gate_d_status(tapeout: dict[str, Any], gate_cd5: dict[str, Any], gate_e: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    reasons: list[str] = []
    all_passed = bool(tapeout.get("all_passed") is True)
    d5_block = gate_cd5.get("d5_reproducibility") if isinstance(gate_cd5.get("d5_reproducibility"), dict) else {}
    d5_status = _norm_status(d5_block.get("status"))
    e_metrics = gate_e.get("metrics") if isinstance(gate_e.get("metrics"), dict) else {}
    e5_block = e_metrics.get("e5_change_control_audit") if isinstance(e_metrics.get("e5_change_control_audit"), dict) else {}
    e5_status = _norm_status(e5_block.get("status"))

    if not all_passed:
        reasons.append("tapeout gate did not pass")
    if d5_status == "fail":
        reasons.append("d5 reproducibility failed")
    if e5_status == "fail":
        reasons.append("e5 change-control audit failed")

    status = "pass"
    if reasons:
        status = "fail"
    elif d5_status == "pending" or e5_status == "pending":
        status = "pending"

    details = {
        "d1_d2_preflight_from_tapeout": "pass" if all_passed else "fail",
        "d3_d4_from_e5": e5_status,
        "d5_reproducibility": d5_status,
    }
    return status, reasons, details


def _gate_e_status(gate_e: dict[str, Any]) -> tuple[str, list[str], dict[str, Any]]:
    status_block = gate_e.get("status") if isinstance(gate_e.get("status"), dict) else {}
    overall = _norm_status(status_block.get("overall"))
    metrics = gate_e.get("metrics") if isinstance(gate_e.get("metrics"), dict) else {}

    details: dict[str, Any] = {}
    notes: list[str] = []
    for key in [
        "e1_ci_stability",
        "e2_time_to_evidence_sla",
        "e3_failure_triage_quality",
        "e4_claim_governance_matrix",
        "e5_change_control_audit",
    ]:
        row = metrics.get(key) if isinstance(metrics.get(key), dict) else {}
        metric_status = _norm_status(row.get("status"))
        details[key] = metric_status
        if metric_status == "fail":
            notes.append(f"{key} failed")

    return overall, notes, details


def _score_factor(status: str, *, pending_credit: float) -> float:
    normalized = _norm_status(status)
    if normalized == "pass":
        return 1.0
    if normalized == "pending":
        return max(0.0, min(1.0, float(pending_credit)))
    return 0.0


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()

    tapeout_path = _resolve(args.tapeout_gate, cwd=cwd)
    gate_b_path = _resolve(args.gate_b, cwd=cwd)
    gate_cd5_path = _resolve(args.gate_cd5, cwd=cwd)
    gate_e_path = _resolve(args.gate_e, cwd=cwd)
    output_path = _resolve(args.output, cwd=cwd)

    tapeout = _load_json_object(tapeout_path)
    gate_b = _load_json_object(gate_b_path)
    gate_cd5 = _load_json_object(gate_cd5_path)
    gate_e = _load_json_object(gate_e_path)

    gate_rows: dict[str, dict[str, Any]] = {}

    a_status, a_notes, a_details = _gate_a_status(tapeout)
    gate_rows["A"] = {"status": a_status, "weight": WEIGHTS["A"], "notes": a_notes, "details": a_details}

    b_status, b_notes, b_details = _gate_b_status(gate_b)
    gate_rows["B"] = {"status": b_status, "weight": WEIGHTS["B"], "notes": b_notes, "details": b_details}

    c_status, c_notes, c_details = _gate_c_status(gate_cd5)
    gate_rows["C"] = {"status": c_status, "weight": WEIGHTS["C"], "notes": c_notes, "details": c_details}

    d_status, d_notes, d_details = _gate_d_status(tapeout, gate_cd5, gate_e)
    gate_rows["D"] = {"status": d_status, "weight": WEIGHTS["D"], "notes": d_notes, "details": d_details}

    e_status, e_notes, e_details = _gate_e_status(gate_e)
    gate_rows["E"] = {"status": e_status, "weight": WEIGHTS["E"], "notes": e_notes, "details": e_details}

    weighted_score = 0.0
    for key in ["A", "B", "C", "D", "E"]:
        row = gate_rows[key]
        factor = _score_factor(str(row.get("status")), pending_credit=float(args.pending_credit))
        contribution = float(row.get("weight", 0.0)) * factor
        row["score_factor"] = factor
        row["score_contribution"] = contribution
        weighted_score += contribution

    hard_stop_reasons: list[str] = []
    if _norm_status(gate_rows["A"]["status"]) == "fail":
        hard_stop_reasons.append("Gate A failed")
    if _norm_status(gate_rows["D"]["status"]) == "fail":
        hard_stop_reasons.append("Gate D failed")
    if not bool(tapeout.get("all_passed") is True):
        hard_stop_reasons.append("Tapeout gate all_passed is false")

    all_gates_pass = all(_norm_status(gate_rows[key]["status"]) == "pass" for key in ["A", "B", "C", "D", "E"])
    declaration_95 = bool(weighted_score >= 95.0 and all_gates_pass and not hard_stop_reasons)

    if declaration_95:
        grade_band = "9.5+"
    elif weighted_score >= 90.0:
        grade_band = "9.0-9.4"
    else:
        grade_band = "<9.0"

    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_foundry_readiness_scorecard",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "tapeout_gate": str(tapeout_path),
            "gate_b_packet": str(gate_b_path),
            "gate_cd5_packet": str(gate_cd5_path),
            "gate_e_packet": str(gate_e_path),
            "pending_credit": float(args.pending_credit),
        },
        "gates": gate_rows,
        "score": {
            "weighted_score_percent": float(weighted_score),
            "grade_band": grade_band,
            "declaration_95_allowed": declaration_95,
        },
        "hard_stop": {
            "hold": bool(len(hard_stop_reasons) > 0),
            "reasons": hard_stop_reasons,
        },
        "next_closure_items": [
            "Replace synthetic Gate B and Gate E metrics with measured/telemetry data.",
            "Close Gate B (B1-B5) with silicon correlation packet.",
            "Ensure all gates are pass with no hard-stop reasons before 9.5 declaration.",
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "scorecard": str(output_path),
                "weighted_score_percent": payload["score"]["weighted_score_percent"],
                "grade_band": grade_band,
                "declaration_95_allowed": declaration_95,
                "hold": payload["hard_stop"]["hold"],
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
