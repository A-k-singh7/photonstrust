from __future__ import annotations

import json

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.layout.pic.foundry_drc_sealed import run_foundry_drc_sealed
from photonstrust.workflow.schema import pic_foundry_drc_sealed_summary_schema_path


def _fixed_clock() -> str:
    return "2026-02-16T12:00:00+00:00"


def _assert_no_leakage(payload: dict, *, forbidden_values: list[str]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    forbidden_keys = ["deck_path", "deck_content", "rule_text", "rule_deck", "rules"]
    for key in forbidden_keys:
        assert key not in serialized
    for value in forbidden_values:
        assert value not in serialized


def test_foundry_drc_sealed_mock_pass_schema_and_counts() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "mock",
            "run_id": "phase57_pass_001",
            "deck_fingerprint": "sha256:abc123",
            "mock_result": {
                "checks": [
                    {"id": "DRC.WG.MIN_WIDTH", "name": "wg_min_width", "status": "pass"},
                    {"id": "DRC.WG.MIN_GAP", "name": "wg_min_gap", "status": "pass"},
                ]
            },
            "deck_path": "/secret/foundry/proprietary.drc",
            "rule_text": "WIDTH >= 0.5um",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "pass"
    assert report["check_counts"] == {"total": 2, "passed": 2, "failed": 0, "errored": 0}
    assert report["failed_check_ids"] == []
    assert report["failed_check_names"] == []
    _assert_no_leakage(
        report,
        forbidden_values=["/secret/foundry/proprietary.drc", "WIDTH >= 0.5um"],
    )


def test_foundry_drc_sealed_mock_fail_schema_and_failed_lists() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "mock",
            "deck_fingerprint": "sha256:def456",
            "mock_result": {
                "checks": [
                    {"id": "DRC.WG.MIN_WIDTH", "name": "wg_min_width", "status": "fail"},
                    {"id": "DRC.WG.MIN_GAP", "name": "wg_min_gap", "status": "pass"},
                    {"id": "DRC.BEND.MIN_RADIUS", "name": "bend_min_radius", "status": "fail"},
                ]
            },
            "deck_content": "proprietary deck lines here",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "fail"
    assert report["check_counts"] == {"total": 3, "passed": 1, "failed": 2, "errored": 0}
    assert report["failed_check_ids"] == ["DRC.BEND.MIN_RADIUS", "DRC.WG.MIN_WIDTH"]
    assert report["failed_check_names"] == ["bend_min_radius", "wg_min_width"]
    _assert_no_leakage(report, forbidden_values=["proprietary deck lines here"])


def test_foundry_drc_sealed_error_for_unsupported_backend_and_deterministic_id() -> None:
    req = {
        "backend": "foundry_cli",
        "deck_fingerprint": "sha256:fedcba",
        "rule_deck": "top_secret_rule_set",
    }
    report_a = run_foundry_drc_sealed(req, now_fn=_fixed_clock)
    report_b = run_foundry_drc_sealed(req, now_fn=_fixed_clock)

    validate_instance(report_a, pic_foundry_drc_sealed_summary_schema_path())
    assert report_a["status"] == "error"
    assert report_a["error_code"] == "backend_unavailable"
    assert report_a["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}
    assert report_a["run_id"] == report_b["run_id"]
    _assert_no_leakage(report_a, forbidden_values=["top_secret_rule_set"])
