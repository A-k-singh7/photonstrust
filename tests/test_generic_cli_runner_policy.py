from __future__ import annotations

import json
from pathlib import Path
import sys

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.layout.pic.foundry_lvs_sealed import run_foundry_lvs_sealed
from photonstrust.layout.pic.foundry_pex_sealed import run_foundry_pex_sealed
from photonstrust.layout.pic.generic_cli_sealed_runner import run_generic_cli_sealed
from photonstrust.workflow.schema import (
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
)


def _fixed_clock() -> str:
    return "2026-02-16T12:00:00+00:00"


def test_generic_cli_policy_blocks_shell_wrappers() -> None:
    result = run_generic_cli_sealed(command=["bash", "-lc", "echo ok"])

    assert result.ok is False
    assert result.returncode is None
    assert result.error_code == "shell_not_allowed"


def test_generic_cli_policy_rejects_invalid_cwd(tmp_path: Path) -> None:
    result = run_generic_cli_sealed(
        command=[sys.executable, "-c", "print('{}')"],
        cwd=str(tmp_path / "missing_cwd"),
        parse_stdout_json_when_no_summary=True,
    )

    assert result.ok is False
    assert result.returncode is None
    assert result.error_code == "invalid_cwd"


def test_generic_cli_policy_rejects_relative_parent_summary_path() -> None:
    result = run_generic_cli_sealed(
        command=[sys.executable, "-c", "print('{}')"],
        summary_json_path="../escape.json",
    )

    assert result.ok is False
    assert result.returncode is None
    assert result.error_code == "invalid_path"


def test_generic_cli_policy_enforces_env_allowlist_for_overrides() -> None:
    result = run_generic_cli_sealed(
        command=[sys.executable, "-c", "print('{}')"],
        env_allowlist=["PT_ALLOWED"],
        env_overrides={"PT_BLOCKED": "on"},
        parse_stdout_json_when_no_summary=True,
    )

    assert result.ok is False
    assert result.returncode is None
    assert result.error_code == "invalid_env"


def test_generic_cli_policy_allows_explicit_override_without_allowlist() -> None:
    result = run_generic_cli_sealed(
        command=[
            sys.executable,
            "-c",
            (
                "import json, os; "
                "print(json.dumps({'mode': os.environ.get('PT_MODE', '')}))"
            ),
        ],
        env_overrides={"PT_MODE": "STRICT"},
        parse_stdout_json_when_no_summary=True,
    )

    assert result.ok is True
    assert result.error_code is None
    assert isinstance(result.summary_json, dict)
    assert result.summary_json.get("mode") == "STRICT"


def test_lvs_wrapper_maps_shell_policy_error() -> None:
    report = run_foundry_lvs_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": ["bash", "-lc", "echo ok"],
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_shell_blocked"
    assert report["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}


def test_pex_wrapper_maps_invalid_cwd_policy_error(tmp_path: Path) -> None:
    report = run_foundry_pex_sealed(
        {
            "backend": "generic_cli",
            "generic_cli": {
                "command": [sys.executable, "-c", "print(json.dumps({}))"],
                "cwd": str(tmp_path / "missing_cwd"),
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_invalid_cwd"
    assert report["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}


def test_lvs_legacy_generic_cli_command_still_succeeds() -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import json; "
            "print(json.dumps({'checks':[{'id':'LVS.OK','name':'lvs_ok','status':'pass'}]}))"
        ),
    ]
    report = run_foundry_lvs_sealed(
        {
            "backend": "generic_cli",
            "deck_fingerprint": "sha256:legacy-ok",
            "generic_cli_command": command,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["status"] == "pass"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 1, "passed": 1, "failed": 0, "errored": 0}
