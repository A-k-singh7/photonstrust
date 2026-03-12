#!/usr/bin/env python3
"""Refresh PIC handoff artifacts in one daily command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


DEFAULT_GATE_B = Path("results/pic_readiness/gate_b/packet_missing_data_seeded_2026-03-03.json")
DEFAULT_GATE_E = Path("results/pic_readiness/governance/pic_gate_e_packet_2026-03-03.json")
DEFAULT_MANIFEST_OUTPUT = Path("results/pic_readiness/handoff/pic_required_external_data_manifest_2026-03-03.json")
DEFAULT_TASK_BOARD_JSON = Path("results/pic_readiness/handoff/pic_integration_task_board_in_progress_2026-03-03.json")
DEFAULT_TASK_BOARD_CSV = Path("results/pic_readiness/handoff/pic_integration_task_board_in_progress_2026-03-03.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Daily refresh of PIC handoff artifacts")
    parser.add_argument("--gate-b", type=Path, default=DEFAULT_GATE_B, help="Gate B packet path")
    parser.add_argument("--gate-e", type=Path, default=DEFAULT_GATE_E, help="Gate E packet path")
    parser.add_argument("--rc-id", default="rc_next", help="Release candidate identifier")
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=DEFAULT_MANIFEST_OUTPUT,
        help="External-data manifest output path",
    )
    parser.add_argument(
        "--task-board-json",
        type=Path,
        default=DEFAULT_TASK_BOARD_JSON,
        help="Task board JSON output path",
    )
    parser.add_argument(
        "--task-board-csv",
        type=Path,
        default=DEFAULT_TASK_BOARD_CSV,
        help="Task board CSV output path",
    )
    parser.add_argument(
        "--task-status",
        default="in_progress",
        help="Default task status for task board rows",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Target schedule start date (UTC) in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--target-step-days",
        type=int,
        default=2,
        help="Spacing in days between tasks inside each area lane",
    )
    return parser.parse_args()


def _resolve(path: Path, *, cwd: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (cwd / path).resolve()


def _run_command(command: list[str], *, repo_root: Path) -> tuple[int, str, str]:
    completed = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    return int(completed.returncode), str(completed.stdout or ""), str(completed.stderr or "")


def _parse_last_json_line(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in str(text or "").splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _fail(
    *,
    stage: str,
    returncode: int,
    command: list[str],
    stdout: str,
    stderr: str,
) -> int:
    payload = {
        "ok": False,
        "stage": stage,
        "returncode": int(returncode),
        "command": command,
        "stdout_tail": str(stdout)[-2000:],
        "stderr_tail": str(stderr)[-2000:],
    }
    print(json.dumps(payload, separators=(",", ":")))
    return 1


def main() -> int:
    args = parse_args()
    cwd = Path.cwd()
    repo_root = Path(__file__).resolve().parents[1]

    gate_b_path = _resolve(args.gate_b, cwd=cwd)
    gate_e_path = _resolve(args.gate_e, cwd=cwd)
    manifest_output = _resolve(args.manifest_output, cwd=cwd)
    task_board_json = _resolve(args.task_board_json, cwd=cwd)
    task_board_csv = _resolve(args.task_board_csv, cwd=cwd)

    manifest_cmd = [
        sys.executable,
        str((repo_root / "scripts" / "build_pic_external_data_manifest.py").resolve()),
        "--gate-b",
        str(gate_b_path),
        "--gate-e",
        str(gate_e_path),
        "--rc-id",
        str(args.rc_id),
        "--output",
        str(manifest_output),
    ]
    rc_manifest, stdout_manifest, stderr_manifest = _run_command(manifest_cmd, repo_root=repo_root)
    if rc_manifest != 0:
        return _fail(
            stage="manifest_builder",
            returncode=rc_manifest,
            command=manifest_cmd,
            stdout=stdout_manifest,
            stderr=stderr_manifest,
        )
    manifest_summary = _parse_last_json_line(stdout_manifest)

    task_board_cmd = [
        sys.executable,
        str((repo_root / "scripts" / "build_pic_integration_task_board.py").resolve()),
        "--manifest",
        str(manifest_output),
        "--output-json",
        str(task_board_json),
        "--output-csv",
        str(task_board_csv),
        "--default-status",
        str(args.task_status),
        "--target-step-days",
        str(max(1, int(args.target_step_days))),
    ]
    if args.start_date is not None and str(args.start_date).strip() != "":
        task_board_cmd.extend(["--start-date", str(args.start_date).strip()])

    rc_task, stdout_task, stderr_task = _run_command(task_board_cmd, repo_root=repo_root)
    if rc_task != 0:
        return _fail(
            stage="task_board_builder",
            returncode=rc_task,
            command=task_board_cmd,
            stdout=stdout_task,
            stderr=stderr_task,
        )
    task_summary = _parse_last_json_line(stdout_task)

    payload = {
        "ok": True,
        "manifest": str(manifest_summary.get("manifest") or manifest_output),
        "task_board_json": str(task_summary.get("task_board_json") or task_board_json),
        "task_board_csv": str(task_summary.get("task_board_csv") or task_board_csv),
        "requirement_count": int(manifest_summary.get("requirement_count") or 0),
        "source_candidate_count": int(manifest_summary.get("source_candidate_count") or 0),
        "integration_plan_count": int(manifest_summary.get("integration_plan_count") or 0),
        "task_count": int(task_summary.get("task_count") or 0),
        "owner_count": int(task_summary.get("owner_count") or 0),
        "blocked_task_count": int(task_summary.get("blocked_task_count") or 0),
        "task_status": str(args.task_status),
        "manifest_command": manifest_cmd,
        "task_board_command": task_board_cmd,
    }
    print(json.dumps(payload, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
