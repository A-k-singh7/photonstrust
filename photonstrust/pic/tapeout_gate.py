"""Wrapper for invoking scripts/check_pic_tapeout_gate.py."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from typing import Any

_DEFAULT_REPORT_PATH = Path("results/pic_tapeout_gate/pic_tapeout_gate_report.json")

_BOOLEAN_FLAGS: dict[str, str] = {
    "run_pic_gate": "--run-pic-gate",
    "require_foundry_signoff": "--require-foundry-signoff",
    "allow_waived_failures": "--allow-waived-failures",
    "require_non_mock_backend": "--require-non-mock-backend",
    "dry_run": "--dry-run",
}

_STRING_FLAGS: dict[str, str] = {
    "pic_gate_args": "--pic-gate-args",
    "waiver_file": "--waiver-file",
    "drc_summary_rel": "--drc-summary-rel",
    "lvs_summary_rel": "--lvs-summary-rel",
    "pex_summary_rel": "--pex-summary-rel",
    "report_path": "--report-path",
}


def run_pic_tapeout_gate(
    request: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Run the PIC tapeout gate script and return a structured result."""

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    resolved_repo_root = _resolve_repo_root(repo_root)
    script_path = (resolved_repo_root / "scripts" / "check_pic_tapeout_gate.py").resolve()
    if not script_path.exists() or not script_path.is_file():
        raise ValueError(f"PIC tapeout gate script not found: {script_path}")

    run_dir = _required_non_empty_string(request, "run_dir")
    command = [sys.executable, str(script_path), "--run-dir", run_dir]

    required_artifacts = request.get("required_artifacts")
    if required_artifacts is not None:
        if not isinstance(required_artifacts, list):
            raise TypeError("request.required_artifacts must be a list of strings when provided")
        for index, artifact in enumerate(required_artifacts):
            if not isinstance(artifact, str):
                raise TypeError(f"request.required_artifacts[{index}] must be a string")
            artifact_value = artifact.strip()
            if not artifact_value:
                raise ValueError(f"request.required_artifacts[{index}] must be a non-empty string")
            command.extend(["--required-artifact", artifact_value])

    for request_key, flag in _BOOLEAN_FLAGS.items():
        if request_key not in request:
            continue
        value = request[request_key]
        if not isinstance(value, bool):
            raise TypeError(f"request.{request_key} must be a boolean when provided")
        if value:
            command.append(flag)

    for request_key, flag in _STRING_FLAGS.items():
        if request_key not in request:
            continue
        value = request[request_key]
        if not isinstance(value, str):
            raise TypeError(f"request.{request_key} must be a string when provided")
        text_value = value.strip()
        if not text_value:
            raise ValueError(f"request.{request_key} must be a non-empty string")
        command.extend([flag, text_value])

    report_path_text = request.get("report_path")
    if report_path_text is None:
        report_path = (resolved_repo_root / _DEFAULT_REPORT_PATH).resolve()
    else:
        if not isinstance(report_path_text, str):
            raise TypeError("request.report_path must be a string when provided")
        report_path_value = report_path_text.strip()
        if not report_path_value:
            raise ValueError("request.report_path must be a non-empty string")
        report_path_candidate = Path(report_path_value)
        if report_path_candidate.is_absolute():
            report_path = report_path_candidate.resolve()
        else:
            report_path = (resolved_repo_root / report_path_candidate).resolve()

    completed = subprocess.run(
        command,
        cwd=str(resolved_repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    report_payload: dict[str, Any] | None = None
    if report_path.exists() and report_path.is_file():
        parsed = json.loads(report_path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError(f"expected JSON object report at {report_path}")
        report_payload = parsed

    return {
        "command": command,
        "returncode": int(completed.returncode),
        "ok": bool(completed.returncode == 0),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "report_path": str(report_path),
        "report": report_payload,
    }


def _resolve_repo_root(repo_root: Path | None) -> Path:
    if repo_root is None:
        return Path(__file__).resolve().parents[2]
    if not isinstance(repo_root, Path):
        raise TypeError("repo_root must be a pathlib.Path when provided")
    return repo_root.resolve()


def _required_non_empty_string(request: dict[str, Any], field_name: str) -> str:
    if field_name not in request:
        raise ValueError(f"request.{field_name} is required")
    value = request[field_name]
    if not isinstance(value, str):
        raise TypeError(f"request.{field_name} must be a string")
    text = value.strip()
    if not text:
        raise ValueError(f"request.{field_name} must be a non-empty string")
    return text
