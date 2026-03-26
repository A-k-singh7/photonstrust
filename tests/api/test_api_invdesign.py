from __future__ import annotations

import json
from pathlib import Path

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402
from photonstrust.benchmarks.schema import validate_instance  # noqa: E402
from photonstrust.invdesign.schema import invdesign_report_schema_path  # noqa: E402


def _pic_mzi_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "phase58_api_mzi_graph",
        "profile": "pic_circuit",
        "metadata": {"title": "phase58_api_mzi_graph", "description": "", "created_at": "2026-02-16"},
        "circuit": {
            "id": "phase58_api_mzi_graph",
            "wavelength_nm": 1550,
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 1.0, "insertion_loss_db": 0.1}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in", "kind": "optical"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in", "kind": "optical"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1", "kind": "optical"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2", "kind": "optical"},
        ],
    }


def _pic_coupler_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "phase58_api_cpl_graph",
        "profile": "pic_circuit",
        "metadata": {"title": "phase58_api_cpl_graph", "description": "", "created_at": "2026-02-16"},
        "circuit": {
            "id": "phase58_api_cpl_graph",
            "wavelength_nm": 1550.0,
            "inputs": [
                {"node": "cpl", "port": "in1", "amplitude": 1.0},
                {"node": "cpl", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [{"id": "cpl", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.0}}],
        "edges": [],
    }


def _robustness_cases() -> list[dict]:
    return [
        {"id": "nominal", "label": "Nominal", "overrides": {}},
        {"id": "corner_slow", "label": "Slow", "overrides": {"cpl": {"coupling_ratio": 0.60}}},
    ]


def test_invdesign_certification_rejects_missing_robustness_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    res = client.post(
        "/v0/pic/invdesign/mzi_phase",
        json={
            "graph": _pic_mzi_graph(),
            "phase_node_id": "ps1",
            "target_output_node": "cpl_out",
            "target_output_port": "out1",
            "target_power_fraction": 0.9,
            "execution_mode": "certification",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "robustness_required" in detail or "robustness_cases" in detail or "evidence" in detail


def test_workflow_certification_rejects_incomplete_invdesign_evidence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    res = client.post(
        "/v0/pic/workflow/invdesign_chain",
        json={
            "graph": _pic_mzi_graph(),
            "execution_mode": "certification",
            "invdesign": {
                "kind": "mzi_phase",
                "phase_node_id": "ps1",
                "target_output_node": "cpl_out",
                "target_output_port": "out1",
                "target_power_fraction": 0.9,
                "steps": 24,
            },
            "layout": {"pdk": {"name": "generic_silicon_photonics"}},
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "robustness_required" in detail or "robustness_cases" in detail or "evidence" in detail


def test_invdesign_certification_emits_worst_case_and_thresholds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    res = client.post(
        "/v0/pic/invdesign/coupler_ratio",
        json={
            "graph": _pic_coupler_graph(),
            "coupler_node_id": "cpl",
            "target_output_node": "cpl",
            "target_output_port": "out1",
            "target_power_fraction": 0.85,
            "steps": 32,
            "execution_mode": "certification",
            "robustness_cases": _robustness_cases(),
            "robustness_thresholds": {
                "min_worst_case_fraction": 0.30,
                "max_objective": 1.0,
                "max_degradation_from_nominal": 0.80,
            },
        },
    )
    assert res.status_code == 200
    payload = res.json()

    report = payload.get("report") or {}
    validate_instance(report, invdesign_report_schema_path())

    assert (report.get("execution") or {}).get("mode") == "certification"
    robust_eval = ((report.get("best") or {}).get("robustness_eval") or {})
    assert isinstance(robust_eval.get("worst_case"), dict)
    assert isinstance(robust_eval.get("metrics"), dict)
    assert (robust_eval.get("threshold_eval") or {}).get("required") is True
    assert isinstance((robust_eval.get("threshold_eval") or {}).get("pass"), bool)

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest.get("input", {}).get("execution_mode") == "certification"


def test_plugin_boundary_preserves_core_parity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    base_payload = {
        "graph": _pic_coupler_graph(),
        "coupler_node_id": "cpl",
        "target_output_node": "cpl",
        "target_output_port": "out1",
        "target_power_fraction": 0.85,
        "steps": 31,
        "execution_mode": "preview",
        "robustness_cases": [{"id": "nominal", "label": "Nominal", "overrides": {}}],
    }

    res_core = client.post("/v0/pic/invdesign/coupler_ratio", json=base_payload)
    assert res_core.status_code == 200
    p_core = res_core.json()

    plugin_payload = dict(base_payload)
    plugin_payload["solver_backend"] = "adjoint_gpl"
    plugin_payload["solver_plugin"] = {
        "plugin_id": "ext.adjoint.demo",
        "plugin_version": "0.1",
        "license_class": "copyleft",
        "available": False,
    }
    res_plugin = client.post("/v0/pic/invdesign/coupler_ratio", json=plugin_payload)
    assert res_plugin.status_code == 200
    p_plugin = res_plugin.json()

    best_core = (p_core.get("report") or {}).get("best") or {}
    best_plugin = (p_plugin.get("report") or {}).get("best") or {}
    assert float(best_core.get("value")) == pytest.approx(float(best_plugin.get("value")), rel=0.0, abs=1e-12)
    assert float(best_core.get("objective")) == pytest.approx(float(best_plugin.get("objective")), rel=0.0, abs=1e-12)

    solver = (((p_plugin.get("report") or {}).get("execution") or {}).get("solver") or {})
    assert solver.get("backend_requested") == "adjoint_gpl"
    assert solver.get("backend_used") == "core"
    assert (solver.get("applicability") or {}).get("status") == "fallback"
    assert solver.get("fallback_reason") == "plugin_unavailable"
    assert solver.get("license_class") == "copyleft"


def test_api_lvs_lite_accepts_signoff_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    build = client.post(
        "/v0/pic/layout/build",
        json={"graph": _pic_mzi_graph(), "pdk": {"name": "generic_silicon_photonics"}},
    )
    assert build.status_code == 200
    build_payload = build.json()

    signoff_bundle = {
        "design_rule_envelope": {
            "waveguides": [{"id": "wg_ok", "width_um": 0.5}],
        }
    }
    lvs = client.post(
        "/v0/pic/layout/lvs_lite",
        json={
            "graph": _pic_mzi_graph(),
            "layout_run_id": build_payload["run_id"],
            "signoff_bundle": signoff_bundle,
        },
    )
    assert lvs.status_code == 200
    report = (lvs.json() or {}).get("report") or {}
    summary = report.get("summary") or {}
    assert summary.get("signoff_pass") is True
    assert int(summary.get("signoff_total_checks") or 0) >= 1
