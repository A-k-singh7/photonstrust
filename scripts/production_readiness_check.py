"""One-command production readiness check (fail-closed)."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _venv_python_path(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _run(cmd: list[str], *, cwd: Path) -> tuple[int, str, float]:
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    elapsed = time.perf_counter() - started
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    if output:
        print(output)
    return int(proc.returncode), output, elapsed


def _bootstrap_isolated_env(
    *,
    repo_root: Path,
    bootstrap_python: str,
    venv_dir: Path,
    recreate: bool,
    lock_file: Path,
    include_qiskit: bool,
) -> Path:
    if recreate and venv_dir.exists():
        shutil.rmtree(venv_dir)
    if not _venv_python_path(venv_dir).exists():
        cmd = [bootstrap_python, "-m", "venv", str(venv_dir)]
        print("+", " ".join(cmd), flush=True)
        rc = subprocess.run(cmd, cwd=repo_root).returncode
        if rc != 0:
            raise RuntimeError("failed to create isolated virtual environment")

    venv_python = _venv_python_path(venv_dir)
    extras = "dev,signing,qutip,qiskit" if include_qiskit else "dev,signing,qutip"
    install_steps = [
        [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "-c",
            str(lock_file),
            "-e",
            f".[{extras}]",
        ],
    ]
    for cmd in install_steps:
        print("+", " ".join(cmd), flush=True)
        rc = subprocess.run(cmd, cwd=repo_root).returncode
        if rc != 0:
            raise RuntimeError(f"failed to bootstrap dependency step: {' '.join(cmd)}")

    return venv_python


def build_command_plan(
    *,
    python_exe: Path,
    lock_file: Path,
    smoke_config: Path,
    smoke_output: Path,
    refresh_release_packet: bool,
    include_qiskit: bool,
) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = [
        (
            "runtime_environment",
            [
                str(python_exe),
                "scripts/check_runtime_environment.py",
                "--lock-file",
                str(lock_file),
                "--require-local-venv",
            ],
        ),
        ("ci_checks", [str(python_exe), "scripts/validation/ci_checks.py"]),
    ]
    if include_qiskit:
        commands.append(("qiskit_lane", [str(python_exe), "scripts/run_qiskit_lane.py", "--strict"]))
    commands.extend(
        [
        ("release_gate", [str(python_exe), "scripts/release/release_gate_check.py"]),
        (
            "runtime_smoke",
            [
                str(python_exe),
                "-m",
                "photonstrust.cli",
                "run",
                str(smoke_config),
                "--output",
                str(smoke_output),
            ],
        ),
        ("external_reviewer_findings", [str(python_exe), "scripts/check_external_reviewer_findings.py"]),
        ("pilot_packet", [str(python_exe), "scripts/check_pilot_packet.py"]),
        ("milestone_archive", [str(python_exe), "scripts/check_milestone_archive.py"]),
    ]
    )

    if refresh_release_packet:
        commands.append(
            (
                "release_packet_refresh",
                [str(python_exe), "scripts/release/refresh_release_gate_packet.py"],
            )
        )
    else:
        commands.extend(
            [
                ("release_packet_verify", [str(python_exe), "scripts/release/verify_release_gate_packet.py"]),
                (
                    "release_packet_signature_verify",
                    [str(python_exe), "scripts/release/verify_release_gate_packet_signature.py"],
                ),
            ]
        )
    return commands


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fail-closed production readiness checks.")
    parser.add_argument(
        "--python",
        default=sys.executable,
        help="Bootstrap Python executable used to create isolated venv (default: current interpreter).",
    )
    parser.add_argument(
        "--venv-dir",
        type=Path,
        default=Path(".venv.production"),
        help="Repository-local virtual environment directory.",
    )
    parser.add_argument(
        "--recreate-venv",
        action="store_true",
        help="Delete and recreate the isolated venv before running checks.",
    )
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("requirements/runtime.lock.txt"),
        help="Dependency constraints file for isolated environment bootstrap.",
    )
    parser.add_argument(
        "--smoke-config",
        type=Path,
        default=Path("configs/quickstart/qkd_quick_smoke.yml"),
        help="Config path for runtime smoke execution.",
    )
    parser.add_argument(
        "--smoke-output",
        type=Path,
        default=Path("results/production_readiness/runtime_smoke"),
        help="Output directory for runtime smoke artifacts.",
    )
    parser.add_argument(
        "--refresh-release-packet",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rebuild/sign/verify release packet artifacts as part of readiness check (default: true).",
    )
    parser.add_argument(
        "--continue-on-failure",
        action="store_true",
        help="Continue running all checks after a failure (default: stop at first failure).",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=Path("results/production_readiness/production_readiness_report.json"),
        help="Path to write machine-readable readiness report.",
    )
    parser.add_argument(
        "--include-qiskit",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Install qiskit extra and enforce strict Qiskit lane (default: true).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    venv_dir = args.venv_dir if args.venv_dir.is_absolute() else (repo_root / args.venv_dir)
    lock_file = args.lock_file if args.lock_file.is_absolute() else (repo_root / args.lock_file)
    smoke_config = args.smoke_config if args.smoke_config.is_absolute() else (repo_root / args.smoke_config)
    smoke_output = args.smoke_output if args.smoke_output.is_absolute() else (repo_root / args.smoke_output)
    report_path = args.report_json if args.report_json.is_absolute() else (repo_root / args.report_json)

    report: dict = {
        "schema_version": "0.1",
        "kind": "photonstrust.production_readiness",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "venv_dir": str(venv_dir),
        "lock_file": str(lock_file),
        "refresh_release_packet": bool(args.refresh_release_packet),
        "include_qiskit": bool(args.include_qiskit),
        "steps": [],
        "ok": True,
    }

    try:
        venv_python = _bootstrap_isolated_env(
            repo_root=repo_root,
            bootstrap_python=str(args.python),
            venv_dir=venv_dir,
            recreate=bool(args.recreate_venv),
            lock_file=lock_file,
            include_qiskit=bool(args.include_qiskit),
        )
    except Exception as exc:
        report["ok"] = False
        report["steps"].append(
            {
                "name": "bootstrap_isolated_env",
                "ok": False,
                "returncode": 1,
                "elapsed_seconds": 0.0,
                "output": str(exc),
            }
        )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print("Production readiness: FAIL")
        print(f" - {exc}")
        return 1

    command_plan = build_command_plan(
        python_exe=venv_python,
        lock_file=lock_file,
        smoke_config=smoke_config,
        smoke_output=smoke_output,
        refresh_release_packet=bool(args.refresh_release_packet),
        include_qiskit=bool(args.include_qiskit),
    )

    all_ok = True
    for step_name, cmd in command_plan:
        print("+", " ".join(cmd), flush=True)
        rc, output, elapsed = _run(cmd, cwd=repo_root)
        ok = rc == 0
        report["steps"].append(
            {
                "name": step_name,
                "ok": ok,
                "command": cmd,
                "returncode": rc,
                "elapsed_seconds": elapsed,
                "output": output,
            }
        )
        if not ok:
            all_ok = False
            if not args.continue_on_failure:
                break

    report["ok"] = all_ok
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if all_ok:
        print("Production readiness: PASS")
        print(str(report_path))
        return 0

    print("Production readiness: FAIL")
    print(str(report_path))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
