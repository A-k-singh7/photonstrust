from __future__ import annotations

import copy

import pytest

from photonstrust.benchmarks.schema import SchemaValidationError, validate_instance
from photonstrust.workflow.schema import multifidelity_report_schema_path


def _minimal_multifidelity_report() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "multifidelity.report",
        "generated_at": "2026-02-16T00:00:00Z",
        "run_id": "phase51_w05_demo",
        "backend_results": {
            "analytic": {
                "status": "pass",
                "summary": {
                    "component": "emitter",
                    "metric": "g2_0",
                    "value": 0.02,
                },
                "applicability": {
                    "status": "pass",
                    "reasons": [],
                },
                "provenance": {
                    "backend_name": "analytic",
                    "backend_version": "0.1",
                    "seed": 123,
                },
            }
        },
        "provenance": {
            "photonstrust_version": "0.1.0",
            "python": "3.12",
            "platform": "win32",
        },
    }


def test_multifidelity_report_schema_accepts_minimal_valid_instance() -> None:
    report = _minimal_multifidelity_report()
    validate_instance(report, multifidelity_report_schema_path())


def test_multifidelity_report_schema_rejects_missing_applicability() -> None:
    report = _minimal_multifidelity_report()
    bad = copy.deepcopy(report)
    del bad["backend_results"]["analytic"]["applicability"]

    with pytest.raises(SchemaValidationError):
        validate_instance(bad, multifidelity_report_schema_path())
