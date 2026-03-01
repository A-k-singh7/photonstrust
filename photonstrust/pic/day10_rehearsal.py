"""Wrapper for invoking scripts/run_day10_tapeout_rehearsal.py."""

from __future__ import annotations

import json
import math
from pathlib import Path
import subprocess
import sys
from typing import Any

_DEFAULT_PACKET_PATH = Path("results/day10/day10_decision_packet.json")

_STRING_FLAGS: dict[str, str] = {
    "mode": "--mode",
    "output_json": "--output-json",
    "run_dir": "--run-dir",
    "runner_config": "--runner-config",
    "waiver_file": "--waiver-file",
    "pic_gate_args": "--pic-gate-args",
    "deck_fingerprint": "--deck-fingerprint",
    "fail_stage": "--fail-stage",
}

_BOOLEAN_FLAGS: dict[str, str] = {
    "allow_waived_failures": "--allow-waived-failures",
    "run_pic_gate": "--run-pic-gate",
    "dry_run": "--dry-run",
}

_BOOLEAN_OPTIONAL_FLAGS: dict[str, tuple[str, str]] = {
    "require_non_mock_backend": ("--require-non-mock-backend", "--no-require-non-mock-backend"),
    "strict": ("--strict", "--no-strict"),
}


def run_pic_day10_rehearsal(
    request: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Run the Day 10 rehearsal script and return a structured result."""

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    resolved_repo_root = _resolve_repo_root(repo_root)
    script_path = (resolved_repo_root / "scripts" / "run_day10_tapeout_rehearsal.py").resolve()
    if not script_path.exists() or not script_path.is_file():
        raise ValueError(f"Day 10 rehearsal script not found: {script_path}")

    command = [sys.executable, str(script_path)]

    for request_key, flag in _STRING_FLAGS.items():
        if request_key not in request:
            continue
        text_value = _required_non_empty_string(request, request_key)
        command.extend([flag, text_value])

    for request_key, flag in _BOOLEAN_FLAGS.items():
        if request_key not in request:
            continue
        value = request[request_key]
        if not isinstance(value, bool):
            raise TypeError(f"request.{request_key} must be a boolean when provided")
        if value:
            command.append(flag)

    for request_key, (true_flag, false_flag) in _BOOLEAN_OPTIONAL_FLAGS.items():
        if request_key not in request:
            continue
        value = request[request_key]
        if not isinstance(value, bool):
            raise TypeError(f"request.{request_key} must be a boolean when provided")
        command.append(true_flag if value else false_flag)

    if "timeout_sec" in request:
        timeout_value = request["timeout_sec"]
        if not isinstance(timeout_value, (int, float)) or isinstance(timeout_value, bool):
            raise TypeError("request.timeout_sec must be a number when provided")
        timeout_float = float(timeout_value)
        if not math.isfinite(timeout_float):
            raise ValueError("request.timeout_sec must be a finite number")
        command.extend(["--timeout-sec", str(timeout_float)])

    packet_path = _resolve_packet_path(request.get("output_json"), repo_root=resolved_repo_root)

    completed = subprocess.run(
        command,
        cwd=str(resolved_repo_root),
        capture_output=True,
        text=True,
        check=False,
    )

    packet_payload: dict[str, Any] | None = None
    if packet_path.exists() and packet_path.is_file():
        try:
            parsed = json.loads(packet_path.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                packet_payload = parsed
        except Exception:
            packet_payload = None

    return {
        "command": command,
        "returncode": int(completed.returncode),
        "ok": bool(completed.returncode == 0),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "packet_path": str(packet_path),
        "packet": packet_payload,
    }


def _resolve_repo_root(repo_root: Path | None) -> Path:
    if repo_root is None:
        return Path(__file__).resolve().parents[2]
    if not isinstance(repo_root, Path):
        raise TypeError("repo_root must be a pathlib.Path when provided")
    return repo_root.resolve()


def _required_non_empty_string(request: dict[str, Any], field_name: str) -> str:
    value = request[field_name]
    if not isinstance(value, str):
        raise TypeError(f"request.{field_name} must be a string when provided")
    text = value.strip()
    if not text:
        raise ValueError(f"request.{field_name} must be a non-empty string")
    return text


def _resolve_packet_path(output_json: Any, *, repo_root: Path) -> Path:
    if output_json is None:
        return (repo_root / _DEFAULT_PACKET_PATH).resolve()
    if not isinstance(output_json, str):
        raise TypeError("request.output_json must be a string when provided")
    text = output_json.strip()
    if not text:
        raise ValueError("request.output_json must be a non-empty string")
    packet_path = Path(text)
    if not packet_path.is_absolute():
        packet_path = repo_root / packet_path
    return packet_path.resolve()
