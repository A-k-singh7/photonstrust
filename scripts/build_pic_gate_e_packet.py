#!/usr/bin/env python3
"""Build PIC Gate E operations/governance packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Any


DEFAULT_DECISION_PACKETS = [
    Path("results/pic_readiness/day10_decision_packet.json"),
    Path("results/pic_readiness/day10_decision_packet_repeat.json"),
    Path("results/pic_readiness/day10_decision_packet_third.json"),
]
DEFAULT_CLAIM_MATRIX = Path("results/pic_readiness/governance/claim_evidence_matrix_2026-03-03.json")
DEFAULT_OUTPUT = Path("results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build PIC Gate E packet")
    parser.add_argument(
        "--decision-packet",
        dest="decision_packets",
        action="append",
        default=None,
        help="Path to day10 decision packet JSON. Repeat to include multiple runs.",
    )
    parser.add_argument("--claim-matrix", type=Path, default=DEFAULT_CLAIM_MATRIX, help="Claim-evidence matrix JSON path")
    parser.add_argument(
        "--ci-workflow",
        type=Path,
        default=Path(".github/workflows/ci.yml"),
        help="CI workflow file path",
    )
    parser.add_argument(
        "--triage-metrics-json",
        type=Path,
        default=None,
        help="Optional triage metrics JSON (for E3 quantitative pass/fail)",
    )
    parser.add_argument(
        "--ci-history-json",
        type=Path,
        default=None,
        help="Optional CI history metrics JSON (for E1 quantitative pass/fail)",
    )
    parser.add_argument(
        "--run-release-verifiers",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run release packet verification scripts for E5 (default: true)",
    )
    parser.add_argument("--e2-sla-seconds", type=float, default=600.0, help="E2 p95 SLA threshold in seconds")
    parser.add_argument("--e2-min-runs", type=int, default=3, help="Minimum run count required for E2 evaluation")
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
    return float(parsed)


def _packet_duration_seconds(packet: dict[str, Any]) -> float:
    steps_obj = packet.get("steps")
    steps: list[Any] = steps_obj if isinstance(steps_obj, list) else []
    total = 0.0
    for row in steps:
        if not isinstance(row, dict):
            continue
        try:
            total += float(row.get("duration_s") or 0.0)
        except Exception:
            continue
    return float(total)


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    clean = sorted(float(v) for v in values)
    index = max(0, min(len(clean) - 1, int((0.95 * len(clean)) + 0.999999) - 1))
    return float(clean[index])


def _run_script(script_rel: str, *, repo_root: Path) -> tuple[bool, str]:
    script_path = (repo_root / script_rel).resolve()
    cmd = [sys.executable, str(script_path)]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, check=False)
    output = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
    return proc.returncode == 0, output


def _evaluate_e1(
    *,
    ci_workflow_path: Path,
    repo_root: Path,
    decision_packets: list[dict[str, Any]],
    ci_history_path: Path | None,
) -> dict[str, Any]:
    required_files = [
        (repo_root / ".pre-commit-config.yaml").resolve(),
        (repo_root / "scripts" / "validation" / "ci_checks.py").resolve(),
        ci_workflow_path,
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        return {
            "status": "fail",
            "reason": "missing quality control files",
            "missing_files": missing,
        }

    ci_text = ci_workflow_path.read_text(encoding="utf-8")
    has_pre_commit = "pre-commit" in ci_text
    has_pytest = "pytest" in ci_text

    local_proxy_rate = None
    if decision_packets:
        proxy_flags = [
            bool(packet.get("tapeout_all_passed") is True and str(packet.get("decision") or "") == "GO")
            for packet in decision_packets
        ]
        local_proxy_rate = 100.0 * (sum(1 for flag in proxy_flags if flag) / float(len(proxy_flags)))

    if not (has_pre_commit and has_pytest):
        return {
            "status": "fail",
            "reason": "required CI controls missing",
            "controls_present": {
                "pre_commit_hooked": bool(has_pre_commit),
                "pytest_in_ci": bool(has_pytest),
                "ci_history_available": False,
            },
            "local_proxy_pass_rate_percent": local_proxy_rate,
        }

    if ci_history_path is None:
        return {
            "status": "pending_ci_history_required",
            "controls_present": {
                "pre_commit_hooked": bool(has_pre_commit),
                "pytest_in_ci": bool(has_pytest),
                "ci_history_available": False,
            },
            "local_proxy_pass_rate_percent": local_proxy_rate,
        }

    if not ci_history_path.exists():
        return {
            "status": "pending_ci_history_required",
            "reason": f"ci history file missing: {ci_history_path}",
            "controls_present": {
                "pre_commit_hooked": bool(has_pre_commit),
                "pytest_in_ci": bool(has_pytest),
                "ci_history_available": False,
            },
            "local_proxy_pass_rate_percent": local_proxy_rate,
        }

    payload = _load_json_object(ci_history_path)
    metric_obj = payload.get("metrics")
    metric_block: dict[str, Any] = metric_obj if isinstance(metric_obj, dict) else {}
    threshold_obj = payload.get("thresholds")
    threshold_block: dict[str, Any] = threshold_obj if isinstance(threshold_obj, dict) else {}

    pass_rate = _as_float(metric_block.get("pass_rate_percent"))
    if pass_rate is None:
        pass_rate = _as_float(payload.get("pass_rate_percent"))
    flaky_rate = _as_float(metric_block.get("flaky_rate_percent"))
    if flaky_rate is None:
        flaky_rate = _as_float(payload.get("flaky_rate_percent"))

    run_count_raw = metric_block.get(
        "run_count",
        metric_block.get("runs", payload.get("run_count", payload.get("runs", 0))),
    )
    try:
        run_count = int(run_count_raw or 0)
    except Exception:
        run_count = 0

    min_pass_rate = _as_float(threshold_block.get("min_pass_rate_percent"))
    if min_pass_rate is None:
        min_pass_rate = 95.0
    max_flaky_rate = _as_float(threshold_block.get("max_flaky_rate_percent"))
    if max_flaky_rate is None:
        max_flaky_rate = 3.0

    if pass_rate is None or flaky_rate is None or run_count <= 0:
        return {
            "status": "fail",
            "reason": "invalid ci history payload; pass_rate/flaky_rate/run_count required",
            "controls_present": {
                "pre_commit_hooked": bool(has_pre_commit),
                "pytest_in_ci": bool(has_pytest),
                "ci_history_available": True,
            },
            "ci_history_path": str(ci_history_path),
            "local_proxy_pass_rate_percent": local_proxy_rate,
        }

    synthetic = bool(payload.get("synthetic") is True)
    ci_pass = bool(pass_rate >= float(min_pass_rate) and flaky_rate <= float(max_flaky_rate))
    if ci_pass:
        status = "preflight_pass_synthetic" if synthetic else "pass"
    else:
        status = "fail"

    return {
        "status": status,
        "controls_present": {
            "pre_commit_hooked": bool(has_pre_commit),
            "pytest_in_ci": bool(has_pytest),
            "ci_history_available": True,
        },
        "ci_history_path": str(ci_history_path),
        "run_count": run_count,
        "pass_rate_percent": float(pass_rate),
        "flaky_rate_percent": float(flaky_rate),
        "min_pass_rate_percent": float(min_pass_rate),
        "max_flaky_rate_percent": float(max_flaky_rate),
        "synthetic": synthetic,
        "local_proxy_pass_rate_percent": local_proxy_rate,
    }


def _evaluate_e2(*, decision_packets: list[dict[str, Any]], min_runs: int, sla_seconds: float) -> dict[str, Any]:
    durations = [_packet_duration_seconds(packet) for packet in decision_packets]
    durations = [value for value in durations if value > 0.0]

    if len(durations) < int(min_runs):
        return {
            "status": "pending",
            "reason": f"need at least {int(min_runs)} runs with duration data",
            "run_count": int(len(durations)),
            "sla_seconds": float(sla_seconds),
        }

    p95_seconds = _p95(durations)
    mean_seconds = float(statistics.mean(durations))
    decisions = [str(packet.get("decision") or "") for packet in decision_packets]
    decisions_consistent = len(set(decisions)) == 1
    status = "pass"
    if p95_seconds is None or p95_seconds > float(sla_seconds) or not decisions_consistent:
        status = "fail"

    return {
        "status": status,
        "run_count": int(len(durations)),
        "mean_seconds": mean_seconds,
        "p95_seconds": p95_seconds,
        "sla_seconds": float(sla_seconds),
        "decisions": decisions,
        "decision_consistent": bool(decisions_consistent),
    }


def _evaluate_e3(*, repo_root: Path, triage_metrics_path: Path | None) -> dict[str, Any]:
    evidence_candidates = [
        (repo_root / "docs" / "operations" / "week52" / "phase62_w52_ga_postmortem_2026-02-16.md").resolve(),
        (repo_root / "docs" / "operations" / "product" / "ui_raid_log_2026-02-19.md").resolve(),
    ]
    present = [str(path) for path in evidence_candidates if path.exists()]

    if triage_metrics_path is None:
        return {
            "status": "evidence_ready_pending_timeseries" if present else "pending",
            "reason": "quantitative triage timeseries not provided",
            "evidence_paths": present,
        }

    if not triage_metrics_path.exists():
        return {
            "status": "pending",
            "reason": f"triage metrics file missing: {triage_metrics_path}",
            "evidence_paths": present,
        }

    metrics = _load_json_object(triage_metrics_path)
    mttr = _as_float(metrics.get("mean_time_to_root_cause_hours"))
    threshold = _as_float(metrics.get("target_hours"))
    if threshold is None:
        threshold = 24.0
    if mttr is None:
        return {
            "status": "fail",
            "reason": "invalid triage metrics payload",
            "evidence_paths": present,
        }

    synthetic = bool(metrics.get("synthetic") is True)
    status = "pass" if mttr <= threshold else "fail"
    if status == "pass" and synthetic:
        status = "preflight_pass_synthetic"

    return {
        "status": status,
        "mean_time_to_root_cause_hours": mttr,
        "target_hours": threshold,
        "synthetic": synthetic,
        "evidence_paths": present + [str(triage_metrics_path)],
    }


def _evaluate_e4(*, claim_matrix_path: Path) -> dict[str, Any]:
    if not claim_matrix_path.exists():
        return {
            "status": "fail",
            "reason": f"claim matrix missing: {claim_matrix_path}",
        }

    matrix = _load_json_object(claim_matrix_path)
    claims_obj = matrix.get("claims")
    claims: list[Any] = claims_obj if isinstance(claims_obj, list) else []
    external_claims = [row for row in claims if isinstance(row, dict) and bool(row.get("external"))]

    def _is_mapped(row: dict[str, Any]) -> bool:
        evidence_paths = row.get("evidence_paths")
        return isinstance(evidence_paths, list) and len(evidence_paths) > 0

    mapped_external = [row for row in external_claims if _is_mapped(row)]
    unmapped = len(external_claims) - len(mapped_external)
    status = "pass" if external_claims and unmapped == 0 else "fail"

    return {
        "status": status,
        "matrix_path": str(claim_matrix_path),
        "external_claims": int(len(external_claims)),
        "mapped_external_claims": int(len(mapped_external)),
        "unmapped_external_claims": int(unmapped),
    }


def _evaluate_e5(*, repo_root: Path, run_release_verifiers: bool) -> dict[str, Any]:
    required_files = [
        (repo_root / ".pre-commit-config.yaml").resolve(),
        (repo_root / ".github" / "workflows" / "ci.yml").resolve(),
        (repo_root / "scripts" / "release" / "release_gate_check.py").resolve(),
        (repo_root / "scripts" / "check_pic_tapeout_gate.py").resolve(),
    ]
    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        return {
            "status": "fail",
            "reason": "missing change-control files",
            "missing_files": missing,
        }

    verifier_results: dict[str, Any] = {
        "release_packet_verify": None,
        "release_signature_verify": None,
    }
    if bool(run_release_verifiers):
        ok_packet, output_packet = _run_script("scripts/release/verify_release_gate_packet.py", repo_root=repo_root)
        ok_sig, output_sig = _run_script("scripts/release/verify_release_gate_packet_signature.py", repo_root=repo_root)
        verifier_results = {
            "release_packet_verify": {"ok": bool(ok_packet), "output": output_packet[-2000:]},
            "release_signature_verify": {"ok": bool(ok_sig), "output": output_sig[-2000:]},
        }
        status = "pass" if ok_packet and ok_sig else "fail"
    else:
        status = "pending"

    return {
        "status": status,
        "controls_present": True,
        "verifiers_ran": bool(run_release_verifiers),
        "verifier_results": verifier_results,
    }


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()
    repo_root = Path(__file__).resolve().parents[1]

    ci_workflow_path = _resolve(args.ci_workflow, cwd=cwd)
    claim_matrix_path = _resolve(args.claim_matrix, cwd=cwd)
    output_path = _resolve(args.output, cwd=cwd)
    triage_metrics_path = _resolve(args.triage_metrics_json, cwd=cwd) if args.triage_metrics_json is not None else None
    ci_history_path = _resolve(args.ci_history_json, cwd=cwd) if args.ci_history_json is not None else None

    if args.decision_packets:
        decision_packet_paths = [_resolve(Path(path), cwd=cwd) for path in args.decision_packets]
    else:
        decision_packet_paths = [_resolve(path, cwd=cwd) for path in DEFAULT_DECISION_PACKETS]

    decision_packets: list[dict[str, Any]] = []
    missing_decision_packets: list[str] = []
    for path in decision_packet_paths:
        if not path.exists():
            missing_decision_packets.append(str(path))
            continue
        decision_packets.append(_load_json_object(path))

    e1 = _evaluate_e1(
        ci_workflow_path=ci_workflow_path,
        repo_root=repo_root,
        decision_packets=decision_packets,
        ci_history_path=ci_history_path,
    )
    e2 = _evaluate_e2(
        decision_packets=decision_packets,
        min_runs=int(max(1, args.e2_min_runs)),
        sla_seconds=float(max(1.0, args.e2_sla_seconds)),
    )
    e3 = _evaluate_e3(repo_root=repo_root, triage_metrics_path=triage_metrics_path)
    e4 = _evaluate_e4(claim_matrix_path=claim_matrix_path)
    e5 = _evaluate_e5(repo_root=repo_root, run_release_verifiers=bool(args.run_release_verifiers))

    statuses = [str(row.get("status") or "pending") for row in (e1, e2, e3, e4, e5)]
    if any(status == "fail" for status in statuses):
        overall = "fail"
    elif all(status == "pass" for status in statuses):
        overall = "pass"
    elif all(status in {"pass", "preflight_pass_synthetic"} for status in statuses):
        overall = "pending"
    else:
        overall = "pending"

    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_gate_e_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "decision_packets": [str(path) for path in decision_packet_paths],
            "claim_matrix": str(claim_matrix_path),
            "ci_workflow": str(ci_workflow_path),
            "triage_metrics_json": str(triage_metrics_path) if triage_metrics_path is not None else None,
            "ci_history_json": str(ci_history_path) if ci_history_path is not None else None,
            "run_release_verifiers": bool(args.run_release_verifiers),
            "e2_sla_seconds": float(args.e2_sla_seconds),
            "e2_min_runs": int(args.e2_min_runs),
        },
        "metrics": {
            "e1_ci_stability": e1,
            "e2_time_to_evidence_sla": e2,
            "e3_failure_triage_quality": e3,
            "e4_claim_governance_matrix": e4,
            "e5_change_control_audit": e5,
        },
        "status": {
            "overall": overall,
        },
        "notes": {
            "missing_decision_packets": missing_decision_packets,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps({"packet": str(output_path), "overall": overall}, separators=(",", ":")))
    return 0 if overall != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
