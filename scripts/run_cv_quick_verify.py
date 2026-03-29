"""Run a single-command, CV-ready verification flow for PhotonTrust.

This wrapper creates one deterministic demo pack, validates key artifacts, and
records optional quantum-lane evidence (QuTiP parity + Qiskit strict lane).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if output:
        print(output)
    return int(proc.returncode), output, elapsed


def _resolve_path(value: str | Path, *, repo_root: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object at {path}")
    return payload


def _validate_demo_pack(pack: dict[str, Any], *, repo_root: Path) -> tuple[list[str], dict[str, str]]:
    failures: list[str] = []
    artifact_paths: dict[str, str] = {}

    determinism = pack.get("determinism")
    if not isinstance(determinism, dict):
        failures.append("demo_pack.json missing object: determinism")
    else:
        fingerprint = determinism.get("fingerprint_sha256")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64:
            failures.append("demo_pack.json determinism.fingerprint_sha256 must be a 64-char hash")

    outputs = pack.get("outputs")
    if not isinstance(outputs, dict):
        failures.append("demo_pack.json missing object: outputs")
        return failures, artifact_paths

    required_output_keys = [
        "pack_dir",
        "scenario_dir",
        "reliability_card",
        "uncertainty",
        "results",
        "evidence_manifest",
        "reliability_summary",
        "uncertainty_summary",
    ]
    for key in required_output_keys:
        raw_value = outputs.get(key)
        if not isinstance(raw_value, str) or not raw_value.strip():
            failures.append(f"demo_pack.json missing outputs.{key}")
            continue
        resolved = _resolve_path(raw_value, repo_root=repo_root)
        artifact_paths[key] = str(resolved)
        if not resolved.exists():
            failures.append(f"missing artifact: outputs.{key} -> {resolved}")
    return failures, artifact_paths


def _qutip_backend_active(report: dict[str, Any]) -> bool:
    records = report.get("records")
    if not isinstance(records, list):
        return False
    for item in records:
        if not isinstance(item, dict):
            continue
        if str(item.get("qutip_backend_used")) == "qutip":
            return True
    return False


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = [
        "# CV Quick Verify Report",
        "",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Overall: **{'PASS' if report.get('ok') else 'FAIL'}**",
        f"- Strict quantum mode: `{report.get('inputs', {}).get('strict_quantum')}`",
        "",
        "## Core artifacts",
    ]

    artifacts = report.get("artifacts", {})
    if isinstance(artifacts, dict):
        for key in [
            "demo_pack_json",
            "pack_dir",
            "scenario_dir",
            "reliability_card",
            "uncertainty",
            "results",
            "evidence_manifest",
            "reliability_summary",
            "uncertainty_summary",
        ]:
            value = artifacts.get(key)
            if value:
                lines.append(f"- {key}: `{value}`")
    lines.append("")

    lines.append("## Quantum lanes")
    lanes = report.get("lanes", {})
    if isinstance(lanes, dict) and lanes:
        qiskit = lanes.get("qiskit")
        qutip = lanes.get("qutip")
        if isinstance(qiskit, dict):
            lines.append(
                f"- qiskit: status=`{qiskit.get('status')}` strict_pass=`{qiskit.get('strict_pass')}` "
                f"report=`{qiskit.get('report_json')}`"
            )
        if isinstance(qutip, dict):
            lines.append(
                f"- qutip: status=`{qutip.get('status')}` installed=`{qutip.get('qutip_available')}` "
                f"backend_active=`{qutip.get('backend_active')}` report=`{qutip.get('report_json')}`"
            )
    else:
        lines.append("- No quantum lanes executed.")
    lines.append("")

    failures = report.get("failures", [])
    lines.append("## Failures")
    if isinstance(failures, list) and failures:
        for item in failures:
            lines.append(f"- {item}")
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run PhotonTrust CV quick verification flow.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used to run child scripts.")
    parser.add_argument("--config", type=Path, default=Path("configs/quickstart/qkd_default.yml"), help="Demo config for phase2e pack generation.")
    parser.add_argument(
        "--demo-output-root",
        type=Path,
        default=Path("results/demo_pack"),
        help="Root directory for phase2e demo-pack outputs.",
    )
    parser.add_argument(
        "--demo-label",
        default="cv_quick_verify",
        help="Deterministic demo-pack label used by run_phase2e_demo_pack.py.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/cv_quick_verify"),
        help="Directory for verifier outputs.",
    )
    parser.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Delete previous outputs at the selected label/output-root before running.",
    )
    parser.add_argument(
        "--run-qutip-lane",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run scripts/run_qutip_parity_lane.py and record results.",
    )
    parser.add_argument(
        "--run-qiskit-lane",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run scripts/run_qiskit_lane.py and record results.",
    )
    parser.add_argument(
        "--strict-quantum",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Fail if Qiskit strict lane does not pass, or if QuTiP is not installed/active. "
            "QuTiP parity thresholds remain informational."
        ),
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional output path for machine-readable report. Defaults under output-root.",
    )
    parser.add_argument(
        "--summary-md",
        type=Path,
        default=None,
        help="Optional output path for markdown summary. Defaults under output-root.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    config_path = _resolve_path(args.config, repo_root=repo_root)
    demo_output_root = _resolve_path(args.demo_output_root, repo_root=repo_root)
    output_root = _resolve_path(args.output_root, repo_root=repo_root)
    demo_pack_dir = demo_output_root / str(args.demo_label)
    demo_pack_json_path = demo_pack_dir / "demo_pack.json"

    report_json_path = _resolve_path(
        args.report_json if args.report_json is not None else (output_root / "cv_quick_verify_report.json"),
        repo_root=repo_root,
    )
    summary_md_path = _resolve_path(
        args.summary_md if args.summary_md is not None else (output_root / "cv_quick_verify_summary.md"),
        repo_root=repo_root,
    )

    failures: list[str] = []
    report: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "photonstrust.cv_quick_verify",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "inputs": {
            "python": str(args.python),
            "config": str(config_path),
            "demo_output_root": str(demo_output_root),
            "demo_label": str(args.demo_label),
            "output_root": str(output_root),
            "strict_quantum": bool(args.strict_quantum),
            "run_qutip_lane": bool(args.run_qutip_lane),
            "run_qiskit_lane": bool(args.run_qiskit_lane),
        },
        "steps": [],
        "artifacts": {},
        "lanes": {},
        "ok": False,
        "failures": [],
    }

    if bool(args.clean):
        for path in [demo_pack_dir, output_root]:
            if path.exists():
                shutil.rmtree(path)
    output_root.mkdir(parents=True, exist_ok=True)

    if not config_path.exists():
        failures.append(f"config does not exist: {config_path}")

    if not failures:
        phase2e_cmd = [
            str(args.python),
            "scripts/run_phase2e_demo_pack.py",
            "--config",
            str(config_path),
            "--output-root",
            str(demo_output_root),
            "--label",
            str(args.demo_label),
        ]
        print("+", " ".join(phase2e_cmd), flush=True)
        rc, output, elapsed = _run(phase2e_cmd, cwd=repo_root)
        report["steps"].append(
            {
                "name": "phase2e_demo_pack",
                "returncode": rc,
                "elapsed_seconds": elapsed,
                "ok": rc == 0,
                "output_excerpt": output[-4000:],
            }
        )
        if rc != 0:
            failures.append("phase2e demo pack command failed")

    if not failures:
        if not demo_pack_json_path.exists():
            failures.append(f"missing demo pack index: {demo_pack_json_path}")
        else:
            try:
                demo_pack = _load_json(demo_pack_json_path)
            except Exception as exc:
                failures.append(f"could not parse demo pack index: {exc}")
                demo_pack = None
            if isinstance(demo_pack, dict):
                pack_failures, pack_artifacts = _validate_demo_pack(demo_pack, repo_root=repo_root)
                failures.extend(pack_failures)
                report["artifacts"]["demo_pack_json"] = str(demo_pack_json_path)
                for key, value in pack_artifacts.items():
                    report["artifacts"][key] = value

    if bool(args.run_qiskit_lane):
        qiskit_json = output_root / "qiskit_lane_report.json"
        qiskit_cmd = [
            str(args.python),
            "scripts/run_qiskit_lane.py",
            "--output-json",
            str(qiskit_json),
        ]
        if bool(args.strict_quantum):
            qiskit_cmd.append("--strict")
        print("+", " ".join(qiskit_cmd), flush=True)
        rc, output, elapsed = _run(qiskit_cmd, cwd=repo_root)
        step_ok = rc == 0
        report["steps"].append(
            {
                "name": "qiskit_lane",
                "returncode": rc,
                "elapsed_seconds": elapsed,
                "ok": step_ok,
                "output_excerpt": output[-4000:],
            }
        )
        qiskit_status = "missing_report"
        qiskit_strict_pass = False
        if qiskit_json.exists():
            try:
                qiskit_report = _load_json(qiskit_json)
                qiskit_status = str(qiskit_report.get("status", "unknown"))
                qiskit_strict_pass = qiskit_status == "ok"
            except Exception as exc:
                failures.append(f"could not parse qiskit lane report: {exc}")
        else:
            failures.append(f"qiskit lane report missing: {qiskit_json}")

        report["lanes"]["qiskit"] = {
            "status": qiskit_status,
            "strict_pass": qiskit_strict_pass,
            "report_json": str(qiskit_json),
        }
        if bool(args.strict_quantum) and not qiskit_strict_pass:
            failures.append("strict quantum gate failed: qiskit lane did not pass")

    if bool(args.run_qutip_lane):
        qutip_json = output_root / "qutip_parity_report.json"
        qutip_md = output_root / "qutip_parity_report.md"
        qutip_cmd = [
            str(args.python),
            "scripts/run_qutip_parity_lane.py",
            "--output-json",
            str(qutip_json),
            "--output-md",
            str(qutip_md),
        ]
        print("+", " ".join(qutip_cmd), flush=True)
        rc, output, elapsed = _run(qutip_cmd, cwd=repo_root)
        report["steps"].append(
            {
                "name": "qutip_lane",
                "returncode": rc,
                "elapsed_seconds": elapsed,
                "ok": rc == 0,
                "output_excerpt": output[-4000:],
            }
        )

        qutip_status = "missing_report"
        qutip_available = False
        backend_active = False
        if qutip_json.exists():
            try:
                qutip_report = _load_json(qutip_json)
                qutip_status = str(qutip_report.get("status", "unknown"))
                environment = qutip_report.get("environment", {})
                if isinstance(environment, dict):
                    qutip_available = bool(environment.get("qutip_available"))
                backend_active = _qutip_backend_active(qutip_report)
            except Exception as exc:
                failures.append(f"could not parse qutip parity report: {exc}")
        else:
            failures.append(f"qutip parity report missing: {qutip_json}")

        report["lanes"]["qutip"] = {
            "status": qutip_status,
            "qutip_available": qutip_available,
            "backend_active": backend_active,
            "report_json": str(qutip_json),
            "report_md": str(qutip_md),
        }

        if bool(args.strict_quantum):
            if not qutip_available:
                failures.append("strict quantum gate failed: qutip is not installed")
            if not backend_active:
                failures.append("strict quantum gate failed: qutip backend was not active in parity lane")

    report["failures"] = failures
    report["ok"] = not failures
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    summary_md_path.write_text(_render_markdown(report), encoding="utf-8")

    print(f"CV quick verify report written: {report_json_path}")
    print(f"CV quick verify summary written: {summary_md_path}")
    print(f"CV quick verify: {'PASS' if report['ok'] else 'FAIL'}")
    if failures:
        for item in failures:
            print(f" - {item}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
