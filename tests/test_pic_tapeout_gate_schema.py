from __future__ import annotations

import copy

import pytest

from photonstrust.benchmarks.schema import SchemaValidationError, validate_instance
from photonstrust.workflow.schema import (
    pic_foundry_drc_sealed_summary_schema_path,
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
    pic_tapeout_gate_schema_path,
)


def _minimal_pic_tapeout_gate_report() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_tapeout_gate",
        "generated_at": "2026-02-26T00:00:00Z",
        "run_dir": "results/day10/run_pkg",
        "required_artifacts": [
            "inputs/graph.json",
        ],
        "checks": [
            {
                "name": "required_artifacts",
                "passed": True,
            }
        ],
        "all_passed": True,
    }


def _minimal_foundry_summary(*, kind: str, execution_backend: str, run_id: str = "phase57_01") -> dict:
    return {
        "schema_version": "0.1",
        "kind": kind,
        "run_id": run_id,
        "status": "pass",
        "execution_backend": execution_backend,
        "started_at": "2026-02-26T00:00:00Z",
        "finished_at": "2026-02-26T00:00:01Z",
        "check_counts": {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "errored": 0,
        },
        "failed_check_ids": [],
        "failed_check_names": [],
        "deck_fingerprint": "sha256:foundry_summary",
        "error_code": None,
    }


_FOUNDRY_SCHEMA_CASES = (
    ("pic.foundry_drc_sealed_summary", pic_foundry_drc_sealed_summary_schema_path, "mock"),
    ("pic.foundry_lvs_sealed_summary", pic_foundry_lvs_sealed_summary_schema_path, "mock"),
    ("pic.foundry_pex_sealed_summary", pic_foundry_pex_sealed_summary_schema_path, "mock"),
)


def test_pic_tapeout_gate_schema_accepts_minimal_valid_instance() -> None:
    validate_instance(_minimal_pic_tapeout_gate_report(), pic_tapeout_gate_schema_path())


@pytest.mark.parametrize(("kind", "schema_path_fn", "execution_backend"), _FOUNDRY_SCHEMA_CASES)
@pytest.mark.parametrize("run_id", ["phase57_01", "runid_123456", "abc12345"])
def test_foundry_sealed_summary_schemas_accept_valid_run_id(
    kind: str,
    schema_path_fn,
    execution_backend: str,
    run_id: str,
) -> None:
    summary = _minimal_foundry_summary(kind=kind, execution_backend=execution_backend, run_id=run_id)
    validate_instance(summary, schema_path_fn())


@pytest.mark.parametrize(("kind", "schema_path_fn", "execution_backend"), _FOUNDRY_SCHEMA_CASES)
@pytest.mark.parametrize(
    "run_id",
    [
        "short7",
        "has-hyphen",
        "UPPERCASE_1",
        "a" * 65,
    ],
)
def test_foundry_sealed_summary_schemas_reject_invalid_run_id(
    kind: str,
    schema_path_fn,
    execution_backend: str,
    run_id: str,
) -> None:
    summary = _minimal_foundry_summary(kind=kind, execution_backend=execution_backend, run_id=run_id)
    with pytest.raises(SchemaValidationError):
        validate_instance(summary, schema_path_fn())


@pytest.mark.parametrize(
    ("kind", "schema_path_fn", "invalid_backend"),
    [
        ("pic.foundry_drc_sealed_summary", pic_foundry_drc_sealed_summary_schema_path, "local_lvs"),
        ("pic.foundry_lvs_sealed_summary", pic_foundry_lvs_sealed_summary_schema_path, "local_rules"),
        ("pic.foundry_pex_sealed_summary", pic_foundry_pex_sealed_summary_schema_path, "local"),
    ],
)
def test_foundry_sealed_summary_schemas_reject_unsupported_execution_backend(
    kind: str,
    schema_path_fn,
    invalid_backend: str,
) -> None:
    summary = _minimal_foundry_summary(kind=kind, execution_backend="mock")
    bad = copy.deepcopy(summary)
    bad["execution_backend"] = invalid_backend

    with pytest.raises(SchemaValidationError):
        validate_instance(bad, schema_path_fn())
