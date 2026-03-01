from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_smoke(args: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    script = REPO_ROOT / "scripts" / "run_foundry_smoke.py"
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
        env=run_env,
    )


def test_foundry_smoke_dry_run_prints_plan(tmp_path: Path) -> None:
    output_json = tmp_path / "dry_run_report.json"
    completed = _run_smoke(["--dry-run", "--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "[dry-run] foundry smoke plan" in completed.stdout
    assert "stages: drc, lvs, pex" in completed.stdout
    assert output_json.exists() is False


def test_foundry_smoke_stub_pass_writes_report_and_returns_zero(tmp_path: Path) -> None:
    output_json = tmp_path / "smoke_pass_report.json"
    completed = _run_smoke(["--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["kind"] == "photonstrust.foundry_real_backend_smoke"
    assert report["mode"] == "stub"
    assert report["overall_status"] == "pass"
    for stage in ("drc", "lvs", "pex"):
        summary = report["stages"][stage]
        assert summary["status"] == "pass"
        assert summary["execution_backend"] == "generic_cli"
        assert summary["error_code"] is None


def test_foundry_smoke_stub_fail_stage_returns_one_in_strict_mode(tmp_path: Path) -> None:
    output_json = tmp_path / "smoke_fail_report.json"
    completed = _run_smoke(["--fail-stage", "lvs", "--output-json", str(output_json)])
    assert completed.returncode == 1
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["overall_status"] == "fail"
    assert report["stages"]["lvs"]["status"] == "fail"


def test_foundry_smoke_stub_fail_stage_returns_zero_in_non_strict_mode(tmp_path: Path) -> None:
    output_json = tmp_path / "smoke_fail_nonstrict_report.json"
    completed = _run_smoke(["--fail-stage", "drc", "--no-strict", "--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert output_json.exists()

    report = json.loads(output_json.read_text(encoding="utf-8"))
    assert report["strict"] is False
    assert report["overall_status"] == "fail"
    assert report["stages"]["drc"]["status"] == "fail"


def test_foundry_smoke_local_only_guard_blocks_ci_without_allow_ci(tmp_path: Path) -> None:
    output_json = tmp_path / "ci_blocked_report.json"
    completed = _run_smoke(["--output-json", str(output_json)], env={"CI": "1"})
    assert completed.returncode == 2
    assert "local-only script refused in CI" in (completed.stdout + completed.stderr)
    assert output_json.exists() is False


def test_foundry_smoke_runner_config_missing_file_fails_cleanly(tmp_path: Path) -> None:
    output_json = tmp_path / "missing_config_report.json"
    missing_config = tmp_path / "missing_runner_config.json"
    completed = _run_smoke(["--runner-config", str(missing_config), "--output-json", str(output_json)])
    assert completed.returncode == 1
    assert "runner-config file not found" in (completed.stdout + completed.stderr).lower()
    assert output_json.exists() is False


def test_foundry_smoke_report_does_not_include_command_or_env_leakage(tmp_path: Path) -> None:
    output_json = tmp_path / "leakage_check_report.json"
    completed = _run_smoke(["--output-json", str(output_json)])
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload_text = output_json.read_text(encoding="utf-8")

    forbidden_tokens = [
        '"command"',
        '"env"',
        '"env_allowlist"',
        "deck_path",
        "rule_text",
        "summary_json_path",
        str(tmp_path),
    ]
    for token in forbidden_tokens:
        assert token not in payload_text
