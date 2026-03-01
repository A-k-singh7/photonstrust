#!/usr/bin/env python3
"""Run Day 10 end-to-end tapeout rehearsal and emit GO/HOLD packet."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from photonstrust.pic.tapeout_package import build_tapeout_package


STAGES = ("drc", "lvs", "pex")


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
        help="Foundry smoke runner config path (required in real mode)",
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

    if str(args.mode) == "real" and args.runner_config is None:
        parser.error("--runner-config is required in real mode")
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
    (inputs / "graph.json").write_text("{}", encoding="utf-8")
    (inputs / "ports.json").write_text("[]", encoding="utf-8")
    (inputs / "routes.json").write_text("[]", encoding="utf-8")
    (inputs / "layout.gds").write_bytes(b"GDSII")


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

    return {
        "schema_version": "0.1",
        "kind": f"pic.foundry_{kind}_sealed_summary",
        "run_id": str(stage.get("run_id") or f"day10_{kind}_run"),
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


def _materialize_foundry_summaries(*, run_dir: Path, smoke_report: dict[str, Any]) -> dict[str, str]:
    generated_at = str(smoke_report.get("generated_at") or datetime.now(timezone.utc).isoformat())
    out: dict[str, str] = {}
    for kind in STAGES:
        payload = _to_foundry_summary(kind=kind, smoke_generated_at=generated_at, smoke_report=smoke_report)
        path = run_dir / f"foundry_{kind}_sealed_summary.json"
        _write_json(path, payload)
        out[kind] = str(path)
    return out


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
        print(f"- waiver_file: {waiver_file}")
        print(f"- require_non_mock_backend: {bool(args.require_non_mock_backend)}")
        print(f"- allow_waived_failures: {bool(args.allow_waived_failures)}")
        print(f"- tapeout_package_output_root: {out_dir / 'tapeout_packages'}")
        print(f"- strict: {bool(args.strict)}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    if str(args.mode) == "synthetic":
        _create_synthetic_inputs(run_dir)
    else:
        if not run_dir.exists() or not run_dir.is_dir():
            print(f"day10 error: run_dir does not exist for real mode: {run_dir}")
            return 2

    steps: list[dict[str, Any]] = []

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
    if str(args.mode) == "synthetic":
        smoke_cmd.extend(["--fail-stage", str(args.fail_stage)])
    else:
        smoke_cmd.extend(["--runner-config", str(runner_config)])

    smoke_step = _run_command(smoke_cmd, cwd=repo_root)
    smoke_step["name"] = "foundry_smoke"
    smoke_step["passed"] = bool(smoke_step.get("returncode") == 0)
    steps.append(smoke_step)

    smoke_report: dict[str, Any] = {}
    materialized_paths: dict[str, str] = {}
    try:
        smoke_report = _load_json_object(smoke_report_path)
        materialized_paths = _materialize_foundry_summaries(run_dir=run_dir, smoke_report=smoke_report)
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

    tapeout_report: dict[str, Any] = {}
    try:
        tapeout_report = _load_json_object(tapeout_report_path)
    except Exception:
        tapeout_report = {}

    tapeout_package_artifact: dict[str, Any] | None = None
    tapeout_package_ok = False
    tapeout_package_report_path = (out_dir / "tapeout_package_report.json").resolve()
    try:
        package_report = build_tapeout_package(
            {
                "run_dir": str(run_dir),
                "output_root": str(out_dir / "tapeout_packages"),
                "allow_missing_signoff": True,
                "allow_stub_pex": True,
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
