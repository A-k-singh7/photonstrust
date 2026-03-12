from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "refresh_pic_handoff_daily.py"
    spec = importlib.util.spec_from_file_location("refresh_pic_handoff_daily_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeCompletedProcess:
    def __init__(self, *, returncode: int, stdout: str, stderr: str) -> None:
        self.returncode = int(returncode)
        self.stdout = str(stdout)
        self.stderr = str(stderr)


def test_refresh_pic_handoff_daily_success(monkeypatch, capsys) -> None:
    module = _load_script_module()
    observed_commands: list[list[str]] = []

    def _fake_run(command, cwd, capture_output, text, check):  # noqa: ANN001
        _ = cwd, capture_output, text, check
        command_list = [str(item) for item in command]
        observed_commands.append(command_list)
        script_name = Path(command_list[1]).name
        if script_name == "build_pic_external_data_manifest.py":
            return _FakeCompletedProcess(
                returncode=0,
                stdout='{"manifest":"manifest.json","requirement_count":6,"source_candidate_count":9,"integration_plan_count":6}\n',
                stderr="",
            )
        if script_name == "build_pic_integration_task_board.py":
            return _FakeCompletedProcess(
                returncode=0,
                stdout='{"task_board_json":"board.json","task_board_csv":"board.csv","task_count":6,"owner_count":6,"blocked_task_count":4}\n',
                stderr="",
            )
        return _FakeCompletedProcess(returncode=1, stdout="", stderr="unexpected command")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "refresh_pic_handoff_daily.py",
            "--task-status",
            "in_progress",
            "--start-date",
            "2026-03-03",
            "--target-step-days",
            "2",
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True
    assert payload["requirement_count"] == 6
    assert payload["task_count"] == 6
    assert payload["blocked_task_count"] == 4
    assert len(observed_commands) == 2
    assert "--default-status" in observed_commands[1]
    assert "in_progress" in observed_commands[1]


def test_refresh_pic_handoff_daily_manifest_failure(monkeypatch, capsys) -> None:
    module = _load_script_module()

    def _fake_run(command, cwd, capture_output, text, check):  # noqa: ANN001
        _ = command, cwd, capture_output, text, check
        return _FakeCompletedProcess(returncode=2, stdout="", stderr="manifest failure")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)
    monkeypatch.setattr(sys, "argv", ["refresh_pic_handoff_daily.py"])

    assert module.main() == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["stage"] == "manifest_builder"
