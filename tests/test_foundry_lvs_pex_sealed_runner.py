from __future__ import annotations

import json
from pathlib import Path
import sys

from photonstrust.benchmarks.schema import validate_instance
import photonstrust.layout.pic.foundry_lvs_sealed as foundry_lvs_sealed_module
from photonstrust.layout.pic.build_layout import build_pic_layout_artifacts
from photonstrust.layout.pic.foundry_lvs_sealed import run_foundry_lvs_sealed
from photonstrust.layout.pic.foundry_pex_sealed import run_foundry_pex_sealed
from photonstrust.workflow.schema import (
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
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


def _local_lvs_demo_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "local_lvs_runner_demo",
        "profile": "pic_circuit",
        "metadata": {"title": "local_lvs_runner_demo", "created_at": "2026-02-16"},
        "circuit": {"id": "lvs_demo", "wavelength_nm": 1550.0},
        "nodes": [
            {
                "id": "wg1",
                "kind": "pic.waveguide",
                "params": {"length_um": 100.0, "loss_db_per_cm": 2.0},
                "ui": {"position": {"x": 0.0, "y": 0.0}},
            },
            {
                "id": "ps1",
                "kind": "pic.phase_shifter",
                "params": {"phase_rad": 0.0, "insertion_loss_db": 0.2},
                "ui": {"position": {"x": 120.0, "y": 0.0}},
            },
        ],
        "edges": [
            {"id": "e1", "from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in", "kind": "optical"},
        ],
    }


def _local_pex_demo_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "local_pex_runner_demo",
        "profile": "pic_circuit",
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler"},
            {"id": "wg_1", "kind": "pic.waveguide"},
            {"id": "ec_out", "kind": "pic.edge_coupler"},
        ],
        "edges": [
            {"id": "e1", "from": "gc_in", "from_port": "out", "to": "wg_1", "to_port": "in", "kind": "optical"},
            {"id": "e2", "from": "wg_1", "from_port": "out", "to": "ec_out", "to_port": "in", "kind": "optical"},
        ],
    }


def _local_pex_demo_routes() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "pic.routes",
        "routes": [
            {
                "route_id": "e1:gc_in.out->wg_1.in",
                "points_um": [[-20.0, 0.0], [80.0, 0.0]],
                "coupling_coeff": 0.01,
                "source": {"edge": {"from": "gc_in", "from_port": "out", "to": "wg_1", "to_port": "in", "kind": "optical"}},
            },
            {
                "route_id": "e2:wg_1.out->ec_out.in",
                "points_um": [[120.0, 0.0], [220.0, 0.0]],
                "coupling_coeff": 0.02,
                "source": {
                    "edge": {"from": "wg_1", "from_port": "out", "to": "ec_out", "to_port": "in", "kind": "optical"}
                },
            },
        ],
    }


def _local_pex_demo_pdk() -> dict:
    return {
        "design_rules": {
            "resistance_ohm_per_um": 0.02,
            "capacitance_ff_per_um": 0.002,
            "max_total_resistance_ohm": 5000.0,
            "max_total_capacitance_ff": 10000.0,
            "max_rc_delay_ps": 50000.0,
            "max_coupling_coeff": 0.10,
            "min_net_coverage_ratio": 1.0,
        }
    }


def test_foundry_lvs_sealed_mock_pass_schema_and_counts() -> None:
    report = run_foundry_lvs_sealed(
        {
            "backend": "mock",
            "run_id": "phase57_lvs_pass_001",
            "deck_fingerprint": "sha256:lvs001",
            "mock_result": {
                "checks": [
                    {"id": "LVS.DEVICE.MATCH", "name": "device_match", "status": "pass"},
                    {"id": "LVS.NET.MATCH", "name": "net_match", "status": "pass"},
                ]
            },
            "deck_path": "/secret/foundry/lvs.deck",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["status"] == "pass"
    assert report["check_counts"] == {"total": 2, "passed": 2, "failed": 0, "errored": 0}
    assert report["failed_check_ids"] == []
    assert report["failed_check_names"] == []
    _assert_no_leakage(report, forbidden_values=["/secret/foundry/lvs.deck"])


def test_foundry_pex_sealed_mock_fail_schema_and_failed_lists() -> None:
    report = run_foundry_pex_sealed(
        {
            "backend": "mock",
            "deck_fingerprint": "sha256:pex001",
            "mock_result": {
                "checks": [
                    {"id": "PEX.RC.BOUNDS", "name": "rc_bounds", "status": "fail"},
                    {"id": "PEX.COUPLING.BOUNDS", "name": "coupling_bounds", "status": "pass"},
                    {"id": "PEX.NET.COVERAGE", "name": "net_coverage", "status": "fail"},
                ]
            },
            "deck_content": "proprietary pex deck",
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["status"] == "fail"
    assert report["check_counts"] == {"total": 3, "passed": 1, "failed": 2, "errored": 0}
    assert report["failed_check_ids"] == ["PEX.NET.COVERAGE", "PEX.RC.BOUNDS"]
    assert report["failed_check_names"] == ["net_coverage", "rc_bounds"]
    _assert_no_leakage(report, forbidden_values=["proprietary pex deck"])


def test_foundry_lvs_sealed_generic_cli_pass_schema() -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import json;"
            "payload={'status':'pass','checks':["
            "{'id':'LVS.DEVICE.MATCH','name':'device_match','status':'pass'},"
            "{'id':'LVS.NET.MATCH','name':'net_match','status':'pass'}]};"
            "print(json.dumps(payload))"
        ),
    ]
    report = run_foundry_lvs_sealed(
        {
            "backend": "generic_cli",
            "deck_fingerprint": "sha256:lvs_cli_ok",
            "generic_cli_command": command,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "pass"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 2, "passed": 2, "failed": 0, "errored": 0}


def test_foundry_lvs_sealed_generic_cli_empty_checks_cannot_pass() -> None:
    command = [sys.executable, "-c", "import json; print(json.dumps({'status':'pass','checks':[]}))"]
    report = run_foundry_lvs_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": command,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_empty_checks"
    assert report["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}


def test_foundry_lvs_sealed_generic_cli_pass_status_conflict_is_error() -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import json; "
            "payload={'status':'pass','checks':[{'id':'LVS.NET.MATCH','name':'net_match','status':'fail'}]}; "
            "print(json.dumps(payload))"
        ),
    ]
    report = run_foundry_lvs_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": command,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_status_checks_conflict"
    assert report["check_counts"] == {"total": 1, "passed": 0, "failed": 1, "errored": 0}
    assert report["failed_check_ids"] == ["LVS.NET.MATCH"]


def test_foundry_lvs_sealed_local_lvs_pass_schema_and_counts(tmp_path: Path) -> None:
    graph = _local_lvs_demo_graph()
    build_pic_layout_artifacts({"graph": graph}, tmp_path)

    routes = json.loads((tmp_path / "routes.json").read_text(encoding="utf-8"))
    ports = json.loads((tmp_path / "ports.json").read_text(encoding="utf-8"))

    report = run_foundry_lvs_sealed(
        {
            "backend": "local_lvs",
            "deck_fingerprint": "sha256:lvs_local_ok",
            "graph": graph,
            "routes": routes,
            "ports": ports,
            "coord_tol_um": 1e-6,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_lvs"
    assert report["status"] == "pass"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 4, "passed": 4, "failed": 0, "errored": 0}
    assert report["failed_check_ids"] == []
    assert report["failed_check_names"] == []


def test_foundry_lvs_sealed_local_alias_fail_reports_deterministic_checks(tmp_path: Path) -> None:
    graph = _local_lvs_demo_graph()
    build_pic_layout_artifacts({"graph": graph}, tmp_path)

    routes = json.loads((tmp_path / "routes.json").read_text(encoding="utf-8"))
    ports = json.loads((tmp_path / "ports.json").read_text(encoding="utf-8"))

    routes["routes"][0]["points_um"][-1][0] = float(routes["routes"][0]["points_um"][-1][0]) + 123.0

    report = run_foundry_lvs_sealed(
        {
            "backend": "local",
            "deck_fingerprint": "sha256:lvs_local_fail",
            "graph": graph,
            "routes": routes,
            "ports": ports,
            "coord_tol_um": 1e-6,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "local"
    assert report["status"] == "fail"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 4, "passed": 2, "failed": 2, "errored": 0}
    assert report["failed_check_ids"] == ["LVS.NET.MISSING", "LVS.PORT.UNCONNECTED"]
    assert report["failed_check_names"] == ["missing_connections", "unconnected_ports"]


def test_foundry_lvs_sealed_local_lvs_extra_fail_reports_deterministic_checks(monkeypatch) -> None:
    def _fake_compare(**_: object) -> dict:
        return {
            "mismatches": {
                "missing_connections": [],
                "extra_connections": [{"route_id": "extra_route"}],
                "port_mapping_mismatches": [],
                "unconnected_ports": [],
            }
        }

    monkeypatch.setattr(foundry_lvs_sealed_module, "compare_schematic_vs_routes", _fake_compare)

    report = run_foundry_lvs_sealed(
        {
            "backend": "local_lvs",
            "deck_fingerprint": "sha256:lvs_local_extra",
            "graph": _local_lvs_demo_graph(),
            "routes": {"routes": []},
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_lvs"
    assert report["status"] == "fail"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 4, "passed": 3, "failed": 1, "errored": 0}
    assert report["failed_check_ids"] == ["LVS.NET.EXTRA"]
    assert report["failed_check_names"] == ["extra_connections"]


def test_foundry_lvs_sealed_local_lvs_port_mapping_fail_reports_deterministic_checks(monkeypatch) -> None:
    def _fake_compare(**_: object) -> dict:
        return {
            "mismatches": {
                "missing_connections": [],
                "extra_connections": [],
                "port_mapping_mismatches": [{"reason": "direction_mismatch"}],
                "unconnected_ports": [],
            }
        }

    monkeypatch.setattr(foundry_lvs_sealed_module, "compare_schematic_vs_routes", _fake_compare)

    report = run_foundry_lvs_sealed(
        {
            "backend": "local_lvs",
            "deck_fingerprint": "sha256:lvs_local_port_map",
            "graph": _local_lvs_demo_graph(),
            "routes": {"routes": []},
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_lvs_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_lvs"
    assert report["status"] == "fail"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 4, "passed": 3, "failed": 1, "errored": 0}
    assert report["failed_check_ids"] == ["LVS.PORT.MAPPING"]
    assert report["failed_check_names"] == ["port_mapping_mismatches"]


def test_foundry_pex_sealed_error_for_unsupported_backend_and_schema() -> None:
    req = {
        "backend": "unknown_backend",
        "deck_fingerprint": "sha256:pex_bad_backend",
        "rule_deck": "top_secret_rule_set",
    }
    report_a = run_foundry_pex_sealed(req, now_fn=_fixed_clock)
    report_b = run_foundry_pex_sealed(req, now_fn=_fixed_clock)

    validate_instance(report_a, pic_foundry_pex_sealed_summary_schema_path())
    assert report_a["status"] == "error"
    assert report_a["error_code"] == "unsupported_backend"
    assert report_a["check_counts"] == {"total": 0, "passed": 0, "failed": 0, "errored": 0}
    assert report_a["run_id"] == report_b["run_id"]
    _assert_no_leakage(report_a, forbidden_values=["top_secret_rule_set"])


def test_foundry_pex_sealed_generic_cli_nested_contract_with_summary_json(tmp_path: Path) -> None:
    summary_path = tmp_path / "pex_summary.json"
    report = run_foundry_pex_sealed(
        {
            "backend": "generic_cli",
            "generic_cli": {
                "command": [
                    sys.executable,
                    "-c",
                    (
                        "import json, pathlib, sys; "
                        "out = pathlib.Path(sys.argv[1]); "
                        "out.write_text(json.dumps({'checks':[{'id':'PEX.RC.BOUNDS','name':'rc_bounds','status':'violation'}]}), encoding='utf-8')"
                    ),
                    "{summary_json_path}",
                ],
                "summary_json_path": "{out}",
                "output_paths": {"out": str(summary_path)},
                "check_status_map": {"violation": "fail"},
            },
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "fail"
    assert report["failed_check_ids"] == ["PEX.RC.BOUNDS"]


def test_foundry_pex_sealed_generic_cli_pass_status_conflict_is_error() -> None:
    command = [
        sys.executable,
        "-c",
        (
            "import json; "
            "payload={'status':'pass','checks':[{'id':'PEX.RC.BOUNDS','name':'rc_bounds','status':'error'}]}; "
            "print(json.dumps(payload))"
        ),
    ]
    report = run_foundry_pex_sealed(
        {
            "backend": "generic_cli",
            "generic_cli_command": command,
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "generic_cli"
    assert report["status"] == "error"
    assert report["error_code"] == "generic_cli_status_checks_conflict"
    assert report["check_counts"] == {"total": 1, "passed": 0, "failed": 0, "errored": 1}


def test_foundry_pex_sealed_local_pex_pass_schema_and_counts() -> None:
    report = run_foundry_pex_sealed(
        {
            "backend": "local_pex",
            "deck_fingerprint": "sha256:pex_local_pass",
            "graph": _local_pex_demo_graph(),
            "routes": _local_pex_demo_routes(),
            "pdk": _local_pex_demo_pdk(),
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_pex"
    assert report["status"] == "pass"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 3, "passed": 3, "failed": 0, "errored": 0}
    assert report["failed_check_ids"] == []
    assert report["failed_check_names"] == []


def test_foundry_pex_sealed_local_alias_fail_reports_deterministic_checks() -> None:
    routes = _local_pex_demo_routes()
    routes["routes"][0]["coupling_coeff"] = 0.5
    routes["routes"][0]["resistance_ohm"] = 9000.0
    routes["routes"] = [routes["routes"][0]]

    report = run_foundry_pex_sealed(
        {
            "backend": "local",
            "deck_fingerprint": "sha256:pex_local_fail",
            "graph": _local_pex_demo_graph(),
            "routes": routes,
            "pdk": _local_pex_demo_pdk(),
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "local"
    assert report["status"] == "fail"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 3, "passed": 0, "failed": 3, "errored": 0}
    assert report["failed_check_ids"] == ["PEX.COUPLING.BOUNDS", "PEX.NET.COVERAGE", "PEX.RC.BOUNDS"]
    assert report["failed_check_names"] == ["coupling_bounds", "net_coverage", "rc_bounds"]


def test_foundry_pex_sealed_local_pex_errors_without_coupling_evidence() -> None:
    routes = _local_pex_demo_routes()
    for row in routes["routes"]:
        row.pop("coupling_coeff", None)

    report = run_foundry_pex_sealed(
        {
            "backend": "local_pex",
            "deck_fingerprint": "sha256:pex_local_missing_coupling",
            "graph": _local_pex_demo_graph(),
            "routes": routes,
            "pdk": _local_pex_demo_pdk(),
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_pex"
    assert report["status"] == "error"
    assert report["error_code"] is None
    assert report["check_counts"] == {"total": 3, "passed": 2, "failed": 0, "errored": 1}
    assert report["failed_check_ids"] == []


def test_foundry_pex_sealed_local_pex_require_explicit_rules_fails_closed() -> None:
    report = run_foundry_pex_sealed(
        {
            "backend": "local_pex",
            "require_explicit_pex_rules": True,
            "graph": _local_pex_demo_graph(),
            "routes": _local_pex_demo_routes(),
            "pdk": {"design_rules": {"max_total_resistance_ohm": 5000.0}},
        },
        now_fn=_fixed_clock,
    )

    validate_instance(report, pic_foundry_pex_sealed_summary_schema_path())
    assert report["execution_backend"] == "local_pex"
    assert report["status"] == "error"
    assert report["error_code"] == "local_pex_missing_required_pdk_rules"
    assert report["check_counts"] == {"total": 3, "passed": 0, "failed": 0, "errored": 3}
