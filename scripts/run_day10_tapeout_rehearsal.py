#!/usr/bin/env python3
"""Run Day 10 end-to-end tapeout rehearsal and emit GO/HOLD packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from photonstrust.pic.assembly import assemble_pic_chip
from photonstrust.pic.signoff import build_pic_signoff_ladder
from photonstrust.pic.tapeout_package import build_tapeout_package


STAGES = ("drc", "lvs", "pex")
_SYNTHETIC_SMOKE_GENERATED_AT = "2026-03-01T00:00:00+00:00"
_REAL_MODE_REQUIRED_SCRIPTS = (
    Path("scripts/run_foundry_smoke.py"),
    Path("scripts/check_pic_tapeout_gate.py"),
)
_LOCAL_BOOTSTRAP_SCRIPT = Path("scripts/materialize_local_tapeout_run.py")
_MANDATORY_DRC_RULE_IDS = (
    "DRC.WG.MIN_WIDTH",
    "DRC.WG.MIN_SPACING",
    "DRC.WG.MIN_BEND_RADIUS",
    "DRC.WG.MIN_ENCLOSURE",
)
_HEX_CHARS = set("0123456789abcdef")
_RUN_ID_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Day 10 tapeout rehearsal and decision packet generation")
    parser.add_argument("--mode", choices=["synthetic", "real"], default="synthetic")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/day10/day10_decision_packet.json"),
        help="Path for decision packet JSON output",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Tapeout run directory (required in real mode; optional in synthetic mode)",
    )
    parser.add_argument(
        "--runner-config",
        type=Path,
        default=None,
        help="Foundry smoke runner config path (required in real mode unless --smoke-local-backend)",
    )
    parser.add_argument(
        "--smoke-local-backend",
        action="store_true",
        help=(
            "Real mode only: run foundry smoke with local backends "
            "(drc=local_rules, lvs=local_lvs, pex=local_pex) from --run-dir context"
        ),
    )
    parser.add_argument(
        "--bootstrap-local-run-dir",
        action="store_true",
        help=(
            "Real mode + --smoke-local-backend only: materialize --run-dir by invoking "
            "scripts/materialize_local_tapeout_run.py before smoke checks"
        ),
    )
    parser.add_argument(
        "--waiver-file",
        type=Path,
        default=None,
        help="Optional waiver JSON passed to tapeout gate",
    )
    parser.add_argument(
        "--allow-waived-failures",
        action="store_true",
        help="Allow waived foundry failures when running tapeout gate",
    )
    parser.add_argument(
        "--require-non-mock-backend",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require non-mock backend in tapeout gate (default: true)",
    )
    parser.add_argument(
        "--run-pic-gate",
        action="store_true",
        help="Forward --run-pic-gate to check_pic_tapeout_gate.py",
    )
    parser.add_argument(
        "--pic-gate-args",
        default="--dry-run",
        help="Arguments forwarded via --pic-gate-args when --run-pic-gate is enabled",
    )
    parser.add_argument(
        "--deck-fingerprint",
        default="sha256:day10-rehearsal",
        help="Deck fingerprint label for smoke run",
    )
    parser.add_argument(
        "--timeout-sec",
        type=float,
        default=60.0,
        help="Per-stage timeout forwarded to foundry smoke",
    )
    parser.add_argument(
        "--allow-ci",
        action="store_true",
        help="Forward --allow-ci to local bootstrap/smoke scripts",
    )
    parser.add_argument(
        "--fail-stage",
        choices=["none", *STAGES],
        default="none",
        help="Synthetic mode only: inject fail status in one foundry stage",
    )
    parser.add_argument(
        "--strict",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Return non-zero on HOLD (default: true)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan only")
    args = parser.parse_args()

    if str(args.mode) == "real" and not bool(args.smoke_local_backend) and args.runner_config is None:
        parser.error("--runner-config is required in real mode unless --smoke-local-backend is set")
    if str(args.mode) == "real" and bool(args.smoke_local_backend) and args.runner_config is not None:
        parser.error("--runner-config cannot be combined with --smoke-local-backend")
    if bool(args.bootstrap_local_run_dir) and str(args.mode) != "real":
        parser.error("--bootstrap-local-run-dir requires --mode real")
    if bool(args.bootstrap_local_run_dir) and not bool(args.smoke_local_backend):
        parser.error("--bootstrap-local-run-dir requires --smoke-local-backend")
    if bool(args.allow_waived_failures) and args.waiver_file is None:
        parser.error("--allow-waived-failures requires --waiver-file")

    return args


def _resolve_path(repo_root: Path, value: Path | None, fallback: Path) -> Path:
    if value is None:
        path = fallback
    else:
        path = value
    if not path.is_absolute():
        path = repo_root / path
    return path.resolve()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _create_synthetic_inputs(run_dir: Path) -> None:
    inputs = run_dir / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    graph = {
        "schema_version": "0.1",
        "graph_id": "day10_synthetic_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "day10_synthetic_graph", "wavelength_nm": 1550},
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 200.0}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {}},
        ],
        "edges": [
            {"from": "gc_in", "to": "wg_1", "kind": "optical"},
            {"from": "wg_1", "to": "ec_out", "kind": "optical"},
        ],
    }
    (inputs / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    (inputs / "ports.json").write_text(
        json.dumps({"schema_version": "0.1", "kind": "pic.ports", "ports": []}, indent=2),
        encoding="utf-8",
    )
    (inputs / "routes.json").write_text(
        json.dumps({"schema_version": "0.1", "kind": "pic.routes", "routes": []}, indent=2),
        encoding="utf-8",
    )
    (inputs / "layout.gds").write_bytes(b"GDSII")


def _missing_real_mode_scripts(repo_root: Path, *, include_bootstrap: bool) -> list[Path]:
    missing: list[Path] = []
    required_scripts = list(_REAL_MODE_REQUIRED_SCRIPTS)
    if include_bootstrap:
        required_scripts.append(_LOCAL_BOOTSTRAP_SCRIPT)
    for rel_path in required_scripts:
        candidate = (repo_root / rel_path).resolve()
        if not candidate.exists() or not candidate.is_file():
            missing.append(candidate)
    return missing


def _build_synthetic_smoke_report(*, deck_fingerprint: str, fail_stage: str) -> dict[str, Any]:
    fail_stage_normalized = str(fail_stage).strip().lower()
    stages: dict[str, dict[str, Any]] = {}
    for kind in STAGES:
        stage_failed = fail_stage_normalized == kind
        status = "fail" if stage_failed else "pass"
        stages[kind] = {
            "run_id": f"day10_synth_{kind}",
            "status": status,
            # Keep synthetic artifacts schema-compatible with sealed summary contracts.
            "execution_backend": "generic_cli",
            "check_counts": {
                "total": 3,
                "passed": 2 if stage_failed else 3,
                "failed": 1 if stage_failed else 0,
                "errored": 0,
            },
            "failed_check_ids": [f"{kind.upper()}.SYNTH.FAIL"] if stage_failed else [],
            "failed_check_names": [f"Synthetic injected {kind.upper()} failure"] if stage_failed else [],
            "error_code": "synthetic_injected_failure" if stage_failed else None,
        }
    overall_status = "fail" if any(str(stage.get("status")) != "pass" for stage in stages.values()) else "pass"
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.foundry_smoke_report",
        "generated_at": _SYNTHETIC_SMOKE_GENERATED_AT,
        "deck_fingerprint": str(deck_fingerprint),
        "overall_status": overall_status,
        "stages": stages,
    }


def _build_synthetic_tapeout_gate_report(
    *,
    run_dir: Path,
    smoke_report: dict[str, Any],
    require_non_mock_backend: bool,
    allow_waived_failures: bool,
    run_pic_gate: bool,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    stages = smoke_report.get("stages") if isinstance(smoke_report.get("stages"), dict) else {}
    for kind in STAGES:
        stage = stages.get(kind) if isinstance(stages.get(kind), dict) else {}
        status = str(stage.get("status") or "error").strip().lower()
        checks.append(
            {
                "name": f"foundry_{kind}_status",
                "status": status,
                "passed": bool(status == "pass"),
            }
        )

    non_mock_backends = True
    for kind in STAGES:
        stage = stages.get(kind) if isinstance(stages.get(kind), dict) else {}
        backend = str(stage.get("execution_backend") or "").strip().lower()
        if backend in {"mock", "stub"}:
            non_mock_backends = False
            break
    if bool(require_non_mock_backend):
        checks.append(
            {
                "name": "require_non_mock_backend",
                "passed": bool(non_mock_backends),
            }
        )

    all_passed = all(bool(item.get("passed")) for item in checks)
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_tapeout_gate_report",
        "generated_at": _SYNTHETIC_SMOKE_GENERATED_AT,
        "run_dir": str(run_dir),
        "all_passed": bool(all_passed),
        "checks": checks,
        "policy": {
            "require_non_mock_backend": bool(require_non_mock_backend),
            "allow_waived_failures": bool(allow_waived_failures),
            "run_pic_gate": bool(run_pic_gate),
        },
    }


def _run_command(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(cmd, cwd=str(cwd), check=False, capture_output=True, text=True)
    duration_s = time.perf_counter() - started
    return {
        "command": cmd,
        "returncode": int(completed.returncode),
        "duration_s": float(duration_s),
        "stdout_tail": str(completed.stdout or "")[-2000:],
        "stderr_tail": str(completed.stderr or "")[-2000:],
    }


def _load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _is_lower_hex(value: str, *, min_len: int = 8, max_len: int = 64) -> bool:
    text = str(value or "").strip().lower()
    return min_len <= len(text) <= max_len and all(ch in _HEX_CHARS for ch in text)


def _is_lower_run_id(value: str, *, min_len: int = 8, max_len: int = 64) -> bool:
    text = str(value or "").strip().lower()
    return min_len <= len(text) <= max_len and all(ch in _RUN_ID_CHARS for ch in text)


def _to_foundry_summary(
    *,
    kind: str,
    smoke_generated_at: str,
    smoke_report: dict[str, Any],
) -> dict[str, Any]:
    stage = (smoke_report.get("stages") or {}).get(kind)
    if not isinstance(stage, dict):
        stage = {}
    counts_raw = stage.get("check_counts") if isinstance(stage.get("check_counts"), dict) else {}
    failed_ids = stage.get("failed_check_ids") if isinstance(stage.get("failed_check_ids"), list) else []
    failed_names = stage.get("failed_check_names") if isinstance(stage.get("failed_check_names"), list) else []
    status = str(stage.get("status") or "error").strip().lower()
    if status not in {"pass", "fail", "error"}:
        status = "error"
    run_id = str(stage.get("run_id") or "").strip().lower()
    if not _is_lower_hex(run_id):
        run_id = _stable_digest(
            {
                "kind": f"day10_{kind}_summary_run_id",
                "source_run_id": str(stage.get("run_id") or ""),
                "status": status,
                "failed_check_ids": [str(v).strip() for v in failed_ids if str(v).strip()],
                "backend": str(stage.get("execution_backend") or "").strip().lower(),
            }
        )[:12]

    payload = {
        "schema_version": "0.1",
        "kind": f"pic.foundry_{kind}_sealed_summary",
        "run_id": run_id,
        "status": status,
        "execution_backend": str(stage.get("execution_backend") or "generic_cli"),
        "started_at": str(smoke_generated_at),
        "finished_at": str(smoke_generated_at),
        "check_counts": {
            "total": int(counts_raw.get("total", 0)),
            "passed": int(counts_raw.get("passed", 0)),
            "failed": int(counts_raw.get("failed", 0)),
            "errored": int(counts_raw.get("errored", 0)),
        },
        "failed_check_ids": [str(v) for v in failed_ids if str(v).strip()],
        "failed_check_names": [str(v) for v in failed_names if str(v).strip()],
        "deck_fingerprint": smoke_report.get("deck_fingerprint"),
        "error_code": stage.get("error_code"),
    }
    if kind == "drc":
        payload["rule_results"] = _canonical_drc_rule_results(status=status, failed_check_ids=failed_ids)
    return payload


def _canonical_drc_rule_results(*, status: str, failed_check_ids: list[Any]) -> dict[str, dict[str, Any]]:
    failed_ids_set = {str(v).strip() for v in failed_check_ids if str(v).strip()}
    failed_rule_ids = [rule_id for rule_id in _MANDATORY_DRC_RULE_IDS if rule_id in failed_ids_set]
    if status == "fail" and not failed_rule_ids:
        failed_rule_ids = [_MANDATORY_DRC_RULE_IDS[0]]
    failed_rule_ids_set = set(failed_rule_ids)

    if status == "error":
        return {
            rule_id: {
                "status": "error",
                "required_um": None,
                "observed_um": None,
                "violation_count": 0,
                "entity_refs": [],
            }
            for rule_id in _MANDATORY_DRC_RULE_IDS
        }

    return {
        rule_id: {
            "status": "fail" if rule_id in failed_rule_ids_set else "pass",
            "required_um": None,
            "observed_um": None,
            "violation_count": 1 if rule_id in failed_rule_ids_set else 0,
            "entity_refs": [],
        }
        for rule_id in _MANDATORY_DRC_RULE_IDS
    }


def _materialize_foundry_summaries(*, run_dir: Path, smoke_report: dict[str, Any]) -> dict[str, str]:
    generated_at = str(smoke_report.get("generated_at") or _SYNTHETIC_SMOKE_GENERATED_AT)
    out: dict[str, str] = {}
    for kind in STAGES:
        payload = _to_foundry_summary(kind=kind, smoke_generated_at=generated_at, smoke_report=smoke_report)
        path = run_dir / f"foundry_{kind}_sealed_summary.json"
        _write_json(path, payload)
        out[kind] = str(path)
    return out


def _stable_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_or_derive_assembly_report(*, run_dir: Path) -> dict[str, Any]:
    graph_path = run_dir / "inputs" / "graph.json"
    graph_payload: Any = None
    if graph_path.exists() and graph_path.is_file():
        try:
            graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))
        except Exception:
            graph_payload = None

    if isinstance(graph_payload, dict):
        try:
            assembly_payload = assemble_pic_chip({"graph": graph_payload}, require_schema=False)
            assembly_report = assembly_payload.get("report")
            if isinstance(assembly_report, dict):
                return assembly_report
        except Exception:
            pass

    digest = _stable_digest(
        {
            "kind": "day10_context_assembly_fallback",
            "graph_payload": graph_payload if isinstance(graph_payload, dict) else None,
            "graph_exists": bool(graph_path.exists()),
        }
    )
    return {
        "schema_version": "0.1",
        "kind": "pic.chip_assembly",
        "assembly_run_id": digest[:12],
        "outputs": {
            "summary": {
                "status": "fail",
                "output_hash": digest,
            }
        },
        "stitch": {
            "summary": {
                "status": "fail",
                "failed_links": 1,
                "stitched_links": 0,
                "warnings": ["assembly context unavailable"],
            }
        },
    }


def _load_or_derive_foundry_summaries(*, run_dir: Path, smoke_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    generated_at = str(smoke_report.get("generated_at") or _SYNTHETIC_SMOKE_GENERATED_AT)
    summaries: dict[str, dict[str, Any]] = {}
    for kind in STAGES:
        summary_path = run_dir / f"foundry_{kind}_sealed_summary.json"
        if summary_path.exists():
            if not summary_path.is_file():
                raise ValueError(f"foundry {kind} summary path is not a file: {summary_path}")
            summaries[kind] = _load_json_object(summary_path)
            continue
        summaries[kind] = _to_foundry_summary(kind=kind, smoke_generated_at=generated_at, smoke_report=smoke_report)
    return summaries


def _unique_non_empty(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _failed_check_ids_from_summary(*, kind: str, summary: dict[str, Any]) -> list[str]:
    status = str(summary.get("status") or "error").strip().lower()
    failed_raw = summary.get("failed_check_ids")
    failed_ids = [str(v).strip() for v in failed_raw if str(v).strip()] if isinstance(failed_raw, list) else []
    if status in {"fail", "error"}:
        if failed_ids:
            return _unique_non_empty(failed_ids)
        return [f"foundry_{kind}.status_{status}"]
    return []


def _tapeout_gate_failed_check_ids(tapeout_report: dict[str, Any]) -> list[str]:
    if not tapeout_report:
        return ["tapeout_gate.report_missing"]
    if bool(tapeout_report.get("all_passed", False)):
        return []

    out: list[str] = []
    checks = tapeout_report.get("checks")
    if isinstance(checks, list):
        for row in checks:
            if not isinstance(row, dict) or bool(row.get("passed", False)):
                continue
            check_name = str(row.get("name") or "").strip().lower().replace(" ", "_")
            out.append(f"tapeout_gate.{check_name or 'check_failed'}")
    if not out:
        out.append("tapeout_gate.all_passed_false")
    return _unique_non_empty(out)


def _derive_foundry_approval(
    *,
    smoke_report: dict[str, Any],
    tapeout_report: dict[str, Any],
    summaries: dict[str, dict[str, Any]],
    include_gate_checks: bool = True,
) -> dict[str, Any]:
    smoke_status = str(smoke_report.get("overall_status") or "").strip().lower()
    if smoke_status not in {"pass", "fail", "error"}:
        smoke_status = "error" if smoke_status else "missing"

    failed_check_ids: list[str] = []
    for kind in STAGES:
        summary = summaries.get(kind) if isinstance(summaries.get(kind), dict) else {}
        failed_check_ids.extend(_failed_check_ids_from_summary(kind=kind, summary=summary))
    if bool(include_gate_checks):
        failed_check_ids.extend(_tapeout_gate_failed_check_ids(tapeout_report))
    if smoke_status != "pass":
        failed_check_ids.append(f"foundry_smoke.status_{smoke_status}")
    failed_check_ids = _unique_non_empty(failed_check_ids)
    if failed_check_ids:
        return {"decision": "HOLD", "status": "fail", "failed_check_ids": failed_check_ids}
    return {"decision": "GO", "status": "pass", "failed_check_ids": []}


def _resolve_source_run_ids(summaries: dict[str, dict[str, Any]]) -> dict[str, str]:
    out: dict[str, str] = {}
    for kind in STAGES:
        summary = summaries.get(kind) if isinstance(summaries.get(kind), dict) else {}
        run_id = str(summary.get("run_id") or "").strip().lower()
        if not _is_lower_run_id(run_id):
            run_id = _stable_digest(
                {
                    "kind": f"day10_{kind}_source_run_id",
                    "summary_hash": _stable_digest(summary),
                }
            )[:12]
        out[kind] = run_id
    return out


def _to_foundry_approval_summary(
    *,
    smoke_report: dict[str, Any],
    tapeout_report: dict[str, Any],
    summaries: dict[str, dict[str, Any]],
    include_gate_checks: bool = True,
) -> dict[str, Any]:
    decision_data = _derive_foundry_approval(
        smoke_report=smoke_report,
        tapeout_report=tapeout_report,
        summaries=summaries,
        include_gate_checks=bool(include_gate_checks),
    )
    failed_check_ids = _unique_non_empty([str(v) for v in decision_data.get("failed_check_ids", []) if str(v).strip()])
    started_at = str(smoke_report.get("generated_at") or _SYNTHETIC_SMOKE_GENERATED_AT)
    finished_at = str(tapeout_report.get("generated_at") or started_at)
    source_run_ids = _resolve_source_run_ids(summaries)
    run_id = _stable_digest(
        {
            "kind": "day10_foundry_approval_run_id",
            "decision": str(decision_data.get("decision") or "HOLD"),
            "status": str(decision_data.get("status") or "fail"),
            "failed_check_ids": failed_check_ids,
            "source_run_ids": source_run_ids,
            "smoke_overall_status": str(smoke_report.get("overall_status") or ""),
            "tapeout_all_passed": bool(tapeout_report.get("all_passed", False)),
        }
    )[:12]

    return {
        "schema_version": "0.1",
        "kind": "pic.foundry_approval_sealed_summary",
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": finished_at,
        "decision": str(decision_data.get("decision") or "HOLD"),
        "status": str(decision_data.get("status") or "fail"),
        "failed_check_ids": failed_check_ids,
        "failed_check_names": list(failed_check_ids),
        "source_run_ids": source_run_ids,
        "deck_fingerprint": smoke_report.get("deck_fingerprint"),
        "error_code": None,
    }


def _materialize_foundry_approval_summary(
    *,
    run_dir: Path,
    smoke_report: dict[str, Any],
    tapeout_report: dict[str, Any],
    summaries: dict[str, dict[str, Any]],
    include_gate_checks: bool = True,
) -> tuple[str, dict[str, Any]]:
    payload = _to_foundry_approval_summary(
        smoke_report=smoke_report,
        tapeout_report=tapeout_report,
        summaries=summaries,
        include_gate_checks=bool(include_gate_checks),
    )
    path = run_dir / "foundry_approval_sealed_summary.json"
    _write_json(path, payload)
    return str(path), payload


def _build_context_signoff_ladder(
    *,
    run_dir: Path,
    smoke_report: dict[str, Any],
    tapeout_report: dict[str, Any],
    foundry_approval_summary: dict[str, Any] | None = None,
) -> str:
    assembly_report = _load_or_derive_assembly_report(run_dir=run_dir)
    summaries = _load_or_derive_foundry_summaries(run_dir=run_dir, smoke_report=smoke_report)
    foundry_approval = (
        dict(foundry_approval_summary)
        if isinstance(foundry_approval_summary, dict)
        else _to_foundry_approval_summary(
            smoke_report=smoke_report,
            tapeout_report=tapeout_report,
            summaries=summaries,
        )
    )
    request = {
        "assembly_report": assembly_report,
        "policy": {"multi_stage": True},
        "drc_summary": summaries["drc"],
        "lvs_summary": summaries["lvs"],
        "pex_summary": summaries["pex"],
        "foundry_approval": foundry_approval,
    }
    result = build_pic_signoff_ladder(request)
    report = result.get("report")
    if not isinstance(report, dict):
        raise ValueError("context signoff builder returned invalid report payload")
    out_path = run_dir / "signoff_ladder.json"
    _write_json(out_path, report)
    return str(out_path)


def _derive_decision(*, smoke_status: str, tapeout_all_passed: bool, tapeout_package_ok: bool) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if str(smoke_status).strip().lower() != "pass":
        reasons.append(f"foundry_smoke_status={smoke_status}")
    if not bool(tapeout_all_passed):
        reasons.append("tapeout_gate_failed")
    if not bool(tapeout_package_ok):
        reasons.append("tapeout_package_failed")
    if reasons:
        return "HOLD", reasons
    return "GO", []


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    is_synthetic_mode = str(args.mode) == "synthetic"

    packet_path = _resolve_path(repo_root, args.output_json, Path("results/day10/day10_decision_packet.json"))
    out_dir = packet_path.parent
    run_dir = _resolve_path(repo_root, args.run_dir, out_dir / "run_pkg")
    smoke_report_path = (out_dir / "foundry_smoke_report.json").resolve()
    tapeout_report_path = (out_dir / "tapeout_gate_report.json").resolve()
    waiver_file = _resolve_path(repo_root, args.waiver_file, Path(".")) if args.waiver_file is not None else None
    runner_config = _resolve_path(repo_root, args.runner_config, Path(".")) if args.runner_config is not None else None

    if args.dry_run:
        print("[dry-run] Day 10 tapeout rehearsal plan")
        print(f"- mode: {args.mode}")
        print(f"- run_dir: {run_dir}")
        print(f"- output_json: {packet_path}")
        print(f"- smoke_report_path: {smoke_report_path}")
        print(f"- tapeout_report_path: {tapeout_report_path}")
        print(f"- runner_config: {runner_config}")
        print(f"- smoke_local_backend: {bool(args.smoke_local_backend)}")
        print(f"- bootstrap_local_run_dir: {bool(args.bootstrap_local_run_dir)}")
        print(f"- waiver_file: {waiver_file}")
        print(f"- require_non_mock_backend: {bool(args.require_non_mock_backend)}")
        print(f"- allow_waived_failures: {bool(args.allow_waived_failures)}")
        print(f"- allow_ci: {bool(args.allow_ci)}")
        print(f"- tapeout_package_output_root: {out_dir / 'tapeout_packages'}")
        print(f"- strict: {bool(args.strict)}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    bootstrap_used = bool(not is_synthetic_mode and args.smoke_local_backend and args.bootstrap_local_run_dir)
    if is_synthetic_mode:
        _create_synthetic_inputs(run_dir)
    else:
        missing_scripts = _missing_real_mode_scripts(repo_root, include_bootstrap=bootstrap_used)
        if missing_scripts:
            print("day10 error: missing required external scripts for real mode:")
            for script_path in missing_scripts:
                print(f"- {script_path}")
            return 2
        if not bootstrap_used and (not run_dir.exists() or not run_dir.is_dir()):
            print(f"day10 error: run_dir does not exist for real mode: {run_dir}")
            return 2

    steps: list[dict[str, Any]] = []
    smoke_report: dict[str, Any] = {}
    if is_synthetic_mode:
        smoke_started = time.perf_counter()
        smoke_report = _build_synthetic_smoke_report(
            deck_fingerprint=str(args.deck_fingerprint),
            fail_stage=str(args.fail_stage),
        )
        _write_json(smoke_report_path, smoke_report)
        steps.append(
            {
                "name": "foundry_smoke",
                "passed": True,
                "returncode": 0,
                "duration_s": float(time.perf_counter() - smoke_started),
                "execution": "in_process_synthetic",
            }
        )
    else:
        if bootstrap_used:
            bootstrap_cmd = [
                sys.executable,
                str((repo_root / _LOCAL_BOOTSTRAP_SCRIPT).resolve()),
                "--run-dir",
                str(run_dir),
            ]
            if bool(args.allow_ci):
                bootstrap_cmd.append("--allow-ci")
            bootstrap_step = _run_command(bootstrap_cmd, cwd=repo_root)
            bootstrap_step["name"] = "bootstrap_local_run_dir"
            bootstrap_step["passed"] = bool(bootstrap_step.get("returncode") == 0)
            steps.append(bootstrap_step)

        smoke_cmd = [
            sys.executable,
            str((repo_root / "scripts" / "run_foundry_smoke.py").resolve()),
            "--output-json",
            str(smoke_report_path),
            "--deck-fingerprint",
            str(args.deck_fingerprint),
            "--timeout-sec",
            str(float(args.timeout_sec)),
            "--no-strict",
        ]
        if bool(args.allow_ci):
            smoke_cmd.append("--allow-ci")
        if bool(args.smoke_local_backend):
            smoke_cmd.extend(
                [
                    "--use-local-backend",
                    "--run-dir",
                    str(run_dir),
                ]
            )
        else:
            smoke_cmd.extend(
                [
                    "--runner-config",
                    str(runner_config),
                ]
            )
        smoke_step = _run_command(smoke_cmd, cwd=repo_root)
        smoke_step["name"] = "foundry_smoke"
        smoke_step["passed"] = bool(smoke_step.get("returncode") == 0)
        steps.append(smoke_step)

    materialized_paths: dict[str, str] = {}
    summaries_for_approval: dict[str, dict[str, Any]] = {}
    try:
        smoke_report = _load_json_object(smoke_report_path)
        materialized_paths = _materialize_foundry_summaries(run_dir=run_dir, smoke_report=smoke_report)
        summaries_for_approval = _load_or_derive_foundry_summaries(run_dir=run_dir, smoke_report=smoke_report)
        steps.append(
            {
                "name": "materialize_foundry_summaries",
                "passed": True,
                "duration_s": 0.0,
                "paths": materialized_paths,
            }
        )
    except Exception as exc:
        steps.append(
            {
                "name": "materialize_foundry_summaries",
                "passed": False,
                "duration_s": 0.0,
                "error": str(exc),
            }
        )

    if (not is_synthetic_mode) and summaries_for_approval:
        try:
            provisional_approval_path, _ = _materialize_foundry_approval_summary(
                run_dir=run_dir,
                smoke_report=smoke_report,
                tapeout_report={},
                summaries=summaries_for_approval,
                include_gate_checks=False,
            )
            materialized_paths["foundry_approval"] = provisional_approval_path
            steps.append(
                {
                    "name": "materialize_foundry_approval_summary_pre_gate",
                    "passed": True,
                    "duration_s": 0.0,
                    "path": provisional_approval_path,
                }
            )
        except Exception as exc:
            steps.append(
                {
                    "name": "materialize_foundry_approval_summary_pre_gate",
                    "passed": False,
                    "duration_s": 0.0,
                    "error": str(exc),
                }
            )

    tapeout_report: dict[str, Any] = {}
    if is_synthetic_mode:
        gate_started = time.perf_counter()
        tapeout_report = _build_synthetic_tapeout_gate_report(
            run_dir=run_dir,
            smoke_report=smoke_report,
            require_non_mock_backend=bool(args.require_non_mock_backend),
            allow_waived_failures=bool(args.allow_waived_failures),
            run_pic_gate=bool(args.run_pic_gate),
        )
        _write_json(tapeout_report_path, tapeout_report)
        gate_returncode = 0 if bool(tapeout_report.get("all_passed", False)) else 1
        steps.append(
            {
                "name": "tapeout_gate",
                "passed": bool(gate_returncode == 0),
                "returncode": int(gate_returncode),
                "duration_s": float(time.perf_counter() - gate_started),
                "execution": "in_process_synthetic",
            }
        )
    else:
        gate_cmd = [
            sys.executable,
            str((repo_root / "scripts" / "check_pic_tapeout_gate.py").resolve()),
            "--run-dir",
            str(run_dir),
            "--require-foundry-signoff",
            "--report-path",
            str(tapeout_report_path),
        ]
        if bool(args.require_non_mock_backend):
            gate_cmd.append("--require-non-mock-backend")
        if bool(args.allow_waived_failures):
            gate_cmd.extend(["--allow-waived-failures", "--waiver-file", str(waiver_file)])
        if bool(args.run_pic_gate):
            gate_cmd.extend(["--run-pic-gate", "--pic-gate-args", str(args.pic_gate_args)])

        gate_step = _run_command(gate_cmd, cwd=repo_root)
        gate_step["name"] = "tapeout_gate"
        gate_step["passed"] = bool(gate_step.get("returncode") == 0)
        steps.append(gate_step)

    if not tapeout_report:
        try:
            tapeout_report = _load_json_object(tapeout_report_path)
        except Exception:
            tapeout_report = {}

    foundry_approval_summary: dict[str, Any] = {}
    try:
        if not summaries_for_approval:
            summaries_for_approval = _load_or_derive_foundry_summaries(run_dir=run_dir, smoke_report=smoke_report)
        foundry_approval_path, foundry_approval_summary = _materialize_foundry_approval_summary(
            run_dir=run_dir,
            smoke_report=smoke_report,
            tapeout_report=tapeout_report,
            summaries=summaries_for_approval,
            include_gate_checks=True,
        )
        materialized_paths["foundry_approval"] = foundry_approval_path
        steps.append(
            {
                "name": "materialize_foundry_approval_summary",
                "passed": True,
                "duration_s": 0.0,
                "path": foundry_approval_path,
            }
        )
    except Exception as exc:
        steps.append(
            {
                "name": "materialize_foundry_approval_summary",
                "passed": False,
                "duration_s": 0.0,
                "error": str(exc),
            }
        )

    try:
        signoff_path = _build_context_signoff_ladder(
            run_dir=run_dir,
            smoke_report=smoke_report,
            tapeout_report=tapeout_report,
            foundry_approval_summary=foundry_approval_summary if foundry_approval_summary else None,
        )
        steps.append(
            {
                "name": "materialize_signoff_ladder",
                "passed": True,
                "duration_s": 0.0,
                "path": signoff_path,
            }
        )
    except Exception as exc:
        steps.append(
            {
                "name": "materialize_signoff_ladder",
                "passed": False,
                "duration_s": 0.0,
                "error": str(exc),
            }
        )

    tapeout_package_artifact: dict[str, Any] | None = None
    tapeout_package_ok = False
    tapeout_package_report_path = (out_dir / "tapeout_package_report.json").resolve()
    try:
        package_report = build_tapeout_package(
            {
                "run_dir": str(run_dir),
                "output_root": str(out_dir / "tapeout_packages"),
                "allow_missing_signoff": False,
                "allow_stub_pex": False,
            },
            repo_root=repo_root,
        )
        tapeout_package_ok = True
        _write_json(tapeout_package_report_path, package_report)
        tapeout_package_artifact = {
            "package_dir": str(package_report.get("package_dir")),
            "manifest_path": str(package_report.get("manifest_path")),
            "package_manifest_path": str(package_report.get("package_manifest_path")),
            "report_json": str(tapeout_package_report_path),
        }
        steps.append(
            {
                "name": "tapeout_package",
                "passed": True,
                "duration_s": 0.0,
                "package_dir": str(package_report.get("package_dir")),
            }
        )
    except Exception as exc:
        steps.append(
            {
                "name": "tapeout_package",
                "passed": False,
                "duration_s": 0.0,
                "error": str(exc),
            }
        )

    smoke_status = str(smoke_report.get("overall_status") or "error").strip().lower()
    tapeout_all_passed = bool(tapeout_report.get("all_passed", False))
    decision, reasons = _derive_decision(
        smoke_status=smoke_status,
        tapeout_all_passed=tapeout_all_passed,
        tapeout_package_ok=tapeout_package_ok,
    )

    packet = {
        "schema_version": "0.1",
        "kind": "photonstrust.day10_tapeout_rehearsal_packet",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": str(args.mode),
        "strict": bool(args.strict),
        "decision": decision,
        "reasons": reasons,
        "inputs": {
            "run_dir": str(run_dir),
            "runner_config": str(runner_config) if runner_config is not None else None,
            "waiver_file": str(waiver_file) if waiver_file is not None else None,
            "allow_waived_failures": bool(args.allow_waived_failures),
            "require_non_mock_backend": bool(args.require_non_mock_backend),
            "run_pic_gate": bool(args.run_pic_gate),
            "deck_fingerprint": str(args.deck_fingerprint),
            "timeout_sec": float(args.timeout_sec),
            "fail_stage": str(args.fail_stage),
            "smoke_local_backend": bool(args.smoke_local_backend),
            "bootstrap_local_run_dir": bool(args.bootstrap_local_run_dir),
            "bootstrap_local_run_dir_used": bool(bootstrap_used),
            "allow_ci": bool(args.allow_ci),
        },
        "artifacts": {
            "foundry_smoke_report_json": str(smoke_report_path),
            "tapeout_gate_report_json": str(tapeout_report_path),
            "foundry_summary_paths": materialized_paths,
            "tapeout_package": tapeout_package_artifact,
        },
        "smoke_overall_status": smoke_status,
        "tapeout_all_passed": tapeout_all_passed,
        "steps": steps,
    }
    _write_json(packet_path, packet)

    print(f"day10 decision: {decision}")
    print(f"day10 packet_path: {packet_path}")
    if decision == "GO":
        return 0
    if bool(args.strict):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
