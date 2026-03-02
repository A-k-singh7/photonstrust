from __future__ import annotations

import json
import sys
from pathlib import Path

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.layout.pic.foundry_drc_sealed import run_foundry_drc_sealed
from photonstrust.workflow.schema import pic_foundry_drc_sealed_summary_schema_path

_MANDATORY_DRC_RULE_IDS = (
    "DRC.WG.MIN_WIDTH",
    "DRC.WG.MIN_SPACING",
    "DRC.WG.MIN_BEND_RADIUS",
    "DRC.WG.MIN_ENCLOSURE",
)


def _fixed_clock() -> str:
    return "2026-02-16T12:00:00+00:00"


def _assert_no_leakage(payload: dict, *, forbidden_values: list[str]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    forbidden_keys = ["deck_path", "deck_content", "rule_text", "rule_deck", "rules"]
    for key in forbidden_keys:
        assert key not in serialized
    for value in forbidden_values:
        assert value not in serialized


def _assert_mandatory_rule_results_keys(report: dict) -> None:
    rule_results = report.get("rule_results") if isinstance(report.get("rule_results"), dict) else {}
    assert sorted(rule_results.keys()) == sorted(_MANDATORY_DRC_RULE_IDS)


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
                    {"id": "DRC.WG.MIN_BEND_RADIUS", "name": "wg_min_bend_radius", "status": "pass"},
                    {"id": "DRC.WG.MIN_ENCLOSURE", "name": "wg_min_enclosure", "status": "pass"},
                ]
            },
            "deck_path": "/secret/foundry/proprietary.drc",
            "rule_text": "WIDTH >= 0.5um",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "pass"
    assert report["check_counts"] == {"total": 4, "passed": 4, "failed": 0, "errored": 0}
    assert report["failed_check_ids"] == []
    assert report["failed_check_names"] == []
    _assert_mandatory_rule_results_keys(report)
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
                    {"id": "DRC.WG.MIN_ENCLOSURE", "name": "wg_min_enclosure", "status": "pass"},
                ]
            },
            "deck_content": "proprietary deck lines here",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "fail"
    assert report["check_counts"] == {"total": 4, "passed": 2, "failed": 2, "errored": 0}
    assert report["failed_check_ids"] == ["DRC.WG.MIN_BEND_RADIUS", "DRC.WG.MIN_WIDTH"]
    assert report["failed_check_names"] == ["wg_min_bend_radius", "wg_min_width"]
    _assert_mandatory_rule_results_keys(report)
    _assert_no_leakage(report, forbidden_values=["proprietary deck lines here"])


def test_foundry_drc_sealed_mock_missing_mandatory_rule_results_fails_closed() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "mock",
            "mock_result": {
                "checks": [
                    {"id": "DRC.WG.MIN_WIDTH", "name": "wg_min_width", "status": "pass"},
                    {"id": "DRC.WG.MIN_SPACING", "name": "wg_min_spacing", "status": "pass"},
                ]
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "error"
    assert report["error_code"] == "mandatory_rule_results_incomplete"
    assert report["check_counts"] == {"total": 4, "passed": 2, "failed": 0, "errored": 2}
    _assert_mandatory_rule_results_keys(report)


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
    assert report_a["check_counts"] == {"total": 4, "passed": 0, "failed": 0, "errored": 4}
    _assert_mandatory_rule_results_keys(report_a)
    assert report_a["run_id"] == report_b["run_id"]
    _assert_no_leakage(report_a, forbidden_values=["top_secret_rule_set"])


def test_foundry_drc_sealed_generic_cli_success_with_summary_json(tmp_path: Path, monkeypatch) -> None:
    summary_path = tmp_path / "drc_summary.json"
    monkeypatch.setenv("PT_DRC_MODE", "STRICT")

    report = run_foundry_drc_sealed(
        {
            "backend": "generic_cli",
            "deck_fingerprint": "sha256:cli123",
            "generic_cli": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, os, pathlib, sys; "
                        "out = pathlib.Path(sys.argv[1]); "
                        "mode = os.environ.get('PT_DRC_MODE', ''); "
                        "checks = ["
                        "{'id':'DRC.WG.MIN_WIDTH','name':'wg_min_width','status':'clean'},"
                        "{'id':'DRC.WG.MIN_GAP','name':'wg_min_gap','status':'violation'},"
                        "{'id':'DRC.WG.MIN_BEND_RADIUS','name':'wg_min_bend_radius','status':'clean'},"
                        "{'id':'DRC.WG.MIN_ENCLOSURE','name':'wg_min_enclosure','status':'clean'}"
                        "]; "
                        "out.write_text(json.dumps({'checks': checks}), encoding='utf-8')"
                    ),
                    "{summary_json_path}",
                ],
                "cwd": str(tmp_path),
                "env_allowlist": ["PT_DRC_MODE"],
                "timeout_s": 10,
                "summary_json_path": "{output_summary}",
                "output_paths": {"output_summary": str(summary_path)},
                "check_status_map": {"clean": "pass", "violation": "fail"},
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "fail"
    assert report["check_counts"] == {"total": 4, "passed": 3, "failed": 1, "errored": 0}
    assert report["failed_check_ids"] == ["DRC.WG.MIN_SPACING"]
    assert report["failed_check_names"] == ["wg_min_spacing"]
    assert report["error_code"] is None
    _assert_mandatory_rule_results_keys(report)
    _assert_no_leakage(
        report,
        forbidden_values=[
            str(summary_path),
            "PT_DRC_MODE",
            "STRICT",
        ],
    )


def test_foundry_drc_sealed_generic_cli_error_when_command_fails(tmp_path: Path) -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "generic_cli",
            "generic_cli": {
                "command": [
                    sys.executable,
                    "-c",
                    "import sys; print('top_secret_deck_path'); sys.stderr.write('fatal_rule_text'); raise SystemExit(3)",
                ],
                "cwd": str(tmp_path),
                "timeout_s": 10,
            },
            "deck_path": "C:/private/proprietary_deck.drc",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "command_failed"
    assert report["check_counts"] == {"total": 4, "passed": 0, "failed": 0, "errored": 4}
    _assert_mandatory_rule_results_keys(report)
    _assert_no_leakage(
        report,
        forbidden_values=[
            "top_secret_deck_path",
            "fatal_rule_text",
            "C:/private/proprietary_deck.drc",
        ],
    )


def test_foundry_drc_sealed_generic_cli_missing_summary_json_fails_closed(tmp_path: Path) -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "generic_cli",
            "generic_cli": {
                "command": [sys.executable, "-c", "print('safe')"],
                "cwd": str(tmp_path),
                "timeout_s": 10,
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_summary_json_required"
    assert report["check_counts"] == {"total": 4, "passed": 0, "failed": 0, "errored": 4}
    _assert_mandatory_rule_results_keys(report)


def test_foundry_drc_sealed_generic_cli_empty_checks_cannot_pass(tmp_path: Path) -> None:
    summary_path = tmp_path / "drc_empty_checks.json"
    report = run_foundry_drc_sealed(
        {
            "backend": "generic_cli",
            "generic_cli": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, pathlib, sys; "
                        "pathlib.Path(sys.argv[1]).write_text(json.dumps({'status':'pass','checks':[]}), encoding='utf-8')"
                    ),
                    "{summary_json_path}",
                ],
                "summary_json_path": "{out}",
                "output_paths": {"out": str(summary_path)},
                "timeout_s": 10,
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_empty_checks"
    assert report["check_counts"] == {"total": 4, "passed": 0, "failed": 0, "errored": 4}
    _assert_mandatory_rule_results_keys(report)


def test_foundry_drc_sealed_generic_cli_pass_status_conflicts_with_failing_checks(tmp_path: Path) -> None:
    summary_path = tmp_path / "drc_conflict.json"
    report = run_foundry_drc_sealed(
        {
            "backend": "generic_cli",
            "generic_cli": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, pathlib, sys; "
                        "payload={'status':'pass','checks':["
                        "{'id':'DRC.WG.MIN_WIDTH','name':'wg_min_width','status':'fail'},"
                        "{'id':'DRC.WG.MIN_SPACING','name':'wg_min_spacing','status':'pass'},"
                        "{'id':'DRC.WG.MIN_BEND_RADIUS','name':'wg_min_bend_radius','status':'pass'},"
                        "{'id':'DRC.WG.MIN_ENCLOSURE','name':'wg_min_enclosure','status':'pass'}"
                        "]}; "
                        "pathlib.Path(sys.argv[1]).write_text(json.dumps(payload), encoding='utf-8')"
                    ),
                    "{summary_json_path}",
                ],
                "summary_json_path": "{out}",
                "output_paths": {"out": str(summary_path)},
                "timeout_s": 10,
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_status_checks_conflict"
    assert report["check_counts"] == {"total": 4, "passed": 3, "failed": 1, "errored": 0}
    assert report["failed_check_ids"] == ["DRC.WG.MIN_WIDTH"]
    _assert_mandatory_rule_results_keys(report)


def test_foundry_drc_sealed_local_rules_pass_schema_and_counts() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "local_rules",
            "deck_fingerprint": "sha256:local-pass",
            "routes": {
                "schema_version": "0.1",
                "kind": "pic.routes",
                "routes": [
                    {
                        "route_id": "r1",
                        "width_um": 0.50,
                        "enclosure_um": 1.30,
                        "points_um": [[0.0, 0.0], [20.0, 0.0]],
                        "bends": [{"radius_um": 9.0}],
                    },
                    {
                        "route_id": "r2",
                        "width_um": 0.50,
                        "enclosure_um": 1.10,
                        "points_um": [[0.0, 2.0], [20.0, 2.0]],
                        "bends": [{"radius_um": 7.0}],
                    },
                ],
            },
            "pdk": {
                "design_rules": {
                    "min_waveguide_width_um": 0.45,
                    "min_waveguide_spacing_um": 0.20,
                    "min_bend_radius_um": 5.0,
                    "min_waveguide_enclosure_um": 1.0,
                }
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_rules"
    assert report["status"] == "pass"
    assert report["check_counts"] == {"total": 4, "passed": 4, "failed": 0, "errored": 0}
    assert report["failed_check_ids"] == []
    assert report["failed_check_names"] == []

    rule_results = report.get("rule_results") if isinstance(report.get("rule_results"), dict) else {}
    assert sorted(rule_results.keys()) == sorted(
        [
            "DRC.WG.MIN_WIDTH",
            "DRC.WG.MIN_SPACING",
            "DRC.WG.MIN_BEND_RADIUS",
            "DRC.WG.MIN_ENCLOSURE",
        ]
    )
    assert rule_results["DRC.WG.MIN_WIDTH"]["status"] == "pass"
    assert rule_results["DRC.WG.MIN_SPACING"]["status"] == "pass"
    assert rule_results["DRC.WG.MIN_BEND_RADIUS"]["status"] == "pass"
    assert rule_results["DRC.WG.MIN_ENCLOSURE"]["status"] == "pass"


def test_foundry_drc_sealed_local_spacing_errors_when_width_unknown() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "local_rules",
            "routes": {
                "routes": [
                    {
                        "route_id": "known_width",
                        "width_um": 0.50,
                        "enclosure_um": 1.20,
                        "points_um": [[0.0, 0.0], [10.0, 0.0]],
                        "bends": [{"radius_um": 8.0}],
                    },
                    {
                        "route_id": "unknown_width",
                        "enclosure_um": 1.20,
                        "points_um": [[0.0, 1.0], [10.0, 1.0]],
                        "bends": [{"radius_um": 8.0}],
                    },
                ]
            },
            "pdk": {
                "design_rules": {
                    "min_waveguide_width_um": 0.0,
                    "min_waveguide_spacing_um": 0.20,
                    "min_bend_radius_um": 5.0,
                    "min_waveguide_enclosure_um": 1.0,
                }
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_rules"
    assert report["status"] == "error"
    assert report["check_counts"] == {"total": 4, "passed": 3, "failed": 0, "errored": 1}
    rule_results = report.get("rule_results") if isinstance(report.get("rule_results"), dict) else {}
    assert rule_results["DRC.WG.MIN_SPACING"]["status"] == "error"


def test_foundry_drc_sealed_local_bend_radius_errors_without_evidence() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "local_rules",
            "routes": {
                "routes": [
                    {
                        "route_id": "r1",
                        "width_um": 0.50,
                        "enclosure_um": 1.20,
                        "points_um": [[0.0, 0.0], [10.0, 0.0]],
                    },
                    {
                        "route_id": "r2",
                        "width_um": 0.50,
                        "enclosure_um": 1.20,
                        "points_um": [[0.0, 2.0], [10.0, 2.0]],
                    },
                ]
            },
            "pdk": {
                "design_rules": {
                    "min_waveguide_width_um": 0.45,
                    "min_waveguide_spacing_um": 0.20,
                    "min_bend_radius_um": 5.0,
                    "min_waveguide_enclosure_um": 1.0,
                }
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_rules"
    assert report["status"] == "error"
    assert report["check_counts"] == {"total": 4, "passed": 3, "failed": 0, "errored": 1}
    rule_results = report.get("rule_results") if isinstance(report.get("rule_results"), dict) else {}
    assert rule_results["DRC.WG.MIN_BEND_RADIUS"]["status"] == "error"


def test_foundry_drc_sealed_local_rules_fail_with_specific_failed_ids() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "local",
            "deck_fingerprint": "sha256:local-fail",
            "mock_result": {
                "routes": {
                    "schema_version": "0.1",
                    "kind": "pic.routes",
                    "routes": [
                        {
                            "route_id": "bad_a",
                            "width_um": 0.30,
                            "enclosure_um": 0.20,
                            "points_um": [[0.0, 0.0], [10.0, 0.0]],
                            "bends": [{"radius_um": 2.0}],
                        },
                        {
                            "route_id": "bad_b",
                            "width_um": 0.30,
                            "enclosure_um": 0.20,
                            "points_um": [[0.0, 0.5], [10.0, 0.5]],
                            "bends": [{"radius_um": 2.5}],
                        },
                    ],
                }
            },
            "pdk": {
                "design_rules": {
                    "min_waveguide_width_um": 0.45,
                    "min_waveguide_spacing_um": 0.40,
                    "min_bend_radius_um": 5.0,
                    "min_waveguide_enclosure_um": 1.0,
                }
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["execution_backend"] == "local"
    assert report["status"] == "fail"
    assert report["check_counts"] == {"total": 4, "passed": 0, "failed": 4, "errored": 0}
    assert report["failed_check_ids"] == [
        "DRC.WG.MIN_BEND_RADIUS",
        "DRC.WG.MIN_ENCLOSURE",
        "DRC.WG.MIN_SPACING",
        "DRC.WG.MIN_WIDTH",
    ]
    assert report["failed_check_names"] == [
        "wg_min_bend_radius",
        "wg_min_enclosure",
        "wg_min_spacing",
        "wg_min_width",
    ]

    rule_results = report.get("rule_results") if isinstance(report.get("rule_results"), dict) else {}
    assert rule_results["DRC.WG.MIN_WIDTH"]["violation_count"] == 2
    assert rule_results["DRC.WG.MIN_SPACING"]["violation_count"] == 1
    assert rule_results["DRC.WG.MIN_BEND_RADIUS"]["violation_count"] == 2
    assert rule_results["DRC.WG.MIN_ENCLOSURE"]["violation_count"] == 2


def test_foundry_drc_sealed_local_rules_uses_arc_radius_evidence() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "local_rules",
            "routes": {
                "schema_version": "0.1",
                "kind": "pic.routes",
                "routes": [
                    {
                        "route_id": "arc_route",
                        "width_um": 0.50,
                        "enclosure_um": 1.10,
                        "points_um": [[0.0, 0.0], [10.0, 0.0]],
                        "segments": [{"type": "arc", "radius_um": 8.0}],
                    },
                    {
                        "route_id": "ref_route",
                        "width_um": 0.50,
                        "enclosure_um": 1.10,
                        "points_um": [[0.0, 2.0], [10.0, 2.0]],
                        "segments": [{"kind": "circular_arc", "radius": 7.5}],
                    },
                ],
            },
            "pdk": {
                "design_rules": {
                    "min_waveguide_width_um": 0.45,
                    "min_waveguide_spacing_um": 0.20,
                    "min_bend_radius_um": 5.0,
                    "min_waveguide_enclosure_um": 1.0,
                }
            },
        },
        now_fn=_fixed_clock,
    )
    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "pass"
    bend = (report.get("rule_results") or {}).get("DRC.WG.MIN_BEND_RADIUS") or {}
    assert bend.get("status") == "pass"
    assert float(bend.get("observed_um") or 0.0) >= 7.5


def test_foundry_drc_sealed_local_rules_require_explicit_pdk_rules() -> None:
    report = run_foundry_drc_sealed(
        {
            "backend": "local_rules",
            "require_explicit_pdk_rules": True,
            "routes": {
                "schema_version": "0.1",
                "kind": "pic.routes",
                "routes": [
                    {
                        "route_id": "r1",
                        "width_um": 0.50,
                        "enclosure_um": 1.20,
                        "points_um": [[0.0, 0.0], [20.0, 0.0]],
                        "segments": [{"type": "arc", "radius_um": 8.0}],
                    },
                    {
                        "route_id": "r2",
                        "width_um": 0.50,
                        "enclosure_um": 1.20,
                        "points_um": [[0.0, 2.0], [20.0, 2.0]],
                        "segments": [{"type": "arc", "radius_um": 8.0}],
                    },
                ],
            },
            "pdk": {
                "design_rules": {
                    "min_waveguide_width_um": 0.45,
                }
            },
        },
        now_fn=_fixed_clock,
    )
    validate_instance(report, pic_foundry_drc_sealed_summary_schema_path())
    assert report["status"] == "error"
    assert report["error_code"] == "local_rules_missing_required_pdk_rules"
    assert int((report.get("check_counts") or {}).get("errored") or 0) >= 3
    rule_results = report.get("rule_results") if isinstance(report.get("rule_results"), dict) else {}
    assert (rule_results.get("DRC.WG.MIN_SPACING") or {}).get("status") == "error"
    assert (rule_results.get("DRC.WG.MIN_BEND_RADIUS") or {}).get("status") == "error"
    assert (rule_results.get("DRC.WG.MIN_ENCLOSURE") or {}).get("status") == "error"
