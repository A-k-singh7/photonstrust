from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.layout.pic.foundry_drc_sealed import run_foundry_drc_sealed
from photonstrust.layout.pic.foundry_lvs_sealed import run_foundry_lvs_sealed
from photonstrust.layout.pic.foundry_pex_sealed import run_foundry_pex_sealed
from photonstrust.workflow.schema import (
    pic_foundry_drc_sealed_summary_schema_path,
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "foundry_sealed"
CASES_PATH = FIXTURES_ROOT / "generic_cli_golden_cases.json"

COPY_FIXTURE_SCRIPT = (
    "import pathlib, sys; "
    "src = pathlib.Path(sys.argv[1]); "
    "out = pathlib.Path(sys.argv[2]); "
    "out.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')"
)


def _fixed_clock() -> str:
    return "2026-02-16T12:00:00+00:00"


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _golden_cases() -> list[dict]:
    catalog = _load_json(CASES_PATH)
    raw_cases = catalog.get("cases")
    assert isinstance(raw_cases, list)
    out: list[dict] = []
    for case in raw_cases:
        if isinstance(case, dict):
            out.append(case)
    assert out
    return out


def _run_case(case: dict, *, tmp_path: Path) -> dict:
    case_id = str(case.get("id") or "golden_case")
    summary_fixture_rel = str(case.get("summary_fixture") or "")
    summary_fixture = FIXTURES_ROOT / summary_fixture_rel
    if not summary_fixture.exists():
        raise FileNotFoundError(summary_fixture)

    summary_out = tmp_path / f"{case_id}.summary.json"
    generic_cli = {
        "command": [
            sys.executable,
            "-c",
            COPY_FIXTURE_SCRIPT,
            str(summary_fixture),
            "{summary_json_path}",
        ],
        "summary_json_path": "{summary_out}",
        "output_paths": {"summary_out": str(summary_out)},
    }
    if isinstance(case.get("check_status_map"), dict):
        generic_cli["check_status_map"] = case.get("check_status_map")

    request = {
        "backend": "generic_cli",
        "deck_fingerprint": "sha256:golden-fixture",
        "generic_cli": generic_cli,
    }

    runner = str(case.get("runner") or "").strip().lower()
    if runner == "drc":
        report = run_foundry_drc_sealed(request, now_fn=_fixed_clock)
        validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    elif runner == "lvs":
        report = run_foundry_lvs_sealed(request, now_fn=_fixed_clock)
        validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    elif runner == "pex":
        report = run_foundry_pex_sealed(request, now_fn=_fixed_clock)
        validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    else:
        raise ValueError(f"unsupported golden case runner: {runner}")
    return report


@pytest.mark.parametrize("case", _golden_cases(), ids=lambda c: str(c.get("id") or "case"))
def test_foundry_sealed_generic_cli_golden_cases(case: dict, tmp_path: Path) -> None:
    report = _run_case(case, tmp_path=tmp_path)

    expected = case.get("expected") if isinstance(case.get("expected"), dict) else {}
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == expected.get("status")
    assert report["check_counts"] == expected.get("check_counts")
    assert report["failed_check_ids"] == expected.get("failed_check_ids")
    assert report["failed_check_names"] == expected.get("failed_check_names")
    assert report["error_code"] == expected.get("error_code")

    serialized = json.dumps(report, sort_keys=True)
    forbidden_values = case.get("forbidden_values") if isinstance(case.get("forbidden_values"), list) else []
    for value in forbidden_values:
        assert str(value) not in serialized


def test_foundry_lvs_generic_cli_nonzero_exit_maps_error_code() -> None:
    report = run_foundry_lvs_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": [
                sys.executable,
                "-c",
                "import sys; raise SystemExit(7)",
            ],
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_nonzero_exit"
    assert report["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}


def test_foundry_pex_generic_cli_invalid_stdout_maps_error_code() -> None:
    report = run_foundry_pex_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": [
                sys.executable,
                "-c",
                "print('not-json')",
            ],
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_invalid_json"
    assert report["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}


def test_foundry_pex_generic_cli_empty_stdout_maps_error_code() -> None:
    report = run_foundry_pex_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": [
                sys.executable,
                "-c",
                "import sys",
            ],
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_empty_output"
    assert report["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}
