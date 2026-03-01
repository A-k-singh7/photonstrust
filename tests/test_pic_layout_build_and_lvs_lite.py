from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from photonstrust.layout.pic.build_layout import build_pic_layout_artifacts
from photonstrust.verification.lvs_lite import run_pic_lvs_lite


def _demo_pic_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "demo_layout_graph",
        "profile": "pic_circuit",
        "metadata": {"title": "demo", "created_at": "2026-02-14"},
        "circuit": {"id": "c1", "wavelength_nm": 1550.0},
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
                "ui": {"position": {"x": 100.0, "y": 0.0}},
            },
        ],
        "edges": [
            {"id": "e1", "from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in", "kind": "optical"},
        ],
    }


def test_pic_layout_build_report_schema_and_lvs_lite_pass(tmp_path: Path):
    graph = _demo_pic_graph()
    report = build_pic_layout_artifacts(
        {"graph": graph, "pdk": {"name": "generic_silicon_photonics"}},
        tmp_path,
    )

    schema_path = Path("schemas") / "photonstrust.pic_layout_build.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)

    routes = json.loads((tmp_path / "routes.json").read_text(encoding="utf-8"))
    ports = json.loads((tmp_path / "ports.json").read_text(encoding="utf-8"))
    assert routes.get("kind") == "pic.routes"
    assert ports.get("kind") == "pic.ports"

    port_by_ref = {(p["node"], p["port"]): p for p in (ports.get("ports") or [])}
    route0 = (routes.get("routes") or [])[0]
    a = route0["points_um"][0]
    b = route0["points_um"][-1]
    assert a == [port_by_ref[("wg1", "out")]["x_um"], port_by_ref[("wg1", "out")]["y_um"]]
    assert b == [port_by_ref[("ps1", "in")]["x_um"], port_by_ref[("ps1", "in")]["y_um"]]

    lvs = run_pic_lvs_lite({"graph": graph, "ports": ports, "routes": routes, "settings": {"coord_tol_um": 1e-6}})
    lvs_schema_path = Path("schemas") / "photonstrust.pic_lvs_lite.v0.schema.json"
    lvs_schema = json.loads(lvs_schema_path.read_text(encoding="utf-8"))
    validate(instance=lvs, schema=lvs_schema)
    assert lvs["summary"]["pass"] is True
    assert isinstance(lvs.get("violations_annotated", []), list)


def test_pic_lvs_lite_detects_dangling_route_endpoint(tmp_path: Path):
    graph = _demo_pic_graph()
    build_pic_layout_artifacts({"graph": graph}, tmp_path)
    routes = json.loads((tmp_path / "routes.json").read_text(encoding="utf-8"))
    ports = json.loads((tmp_path / "ports.json").read_text(encoding="utf-8"))

    # Break the route endpoint so it no longer snaps to the intended port.
    routes = json.loads(json.dumps(routes))
    routes["routes"][0]["points_um"][-1][0] = float(routes["routes"][0]["points_um"][-1][0]) + 123.456

    lvs = run_pic_lvs_lite({"graph": graph, "ports": ports, "routes": routes, "settings": {"coord_tol_um": 1e-6}})
    assert lvs["summary"]["pass"] is False
    assert lvs["summary"]["missing_edges"] >= 1
    assert len(lvs["observed"]["dangling_routes"]) >= 1


def test_pic_lvs_lite_includes_signoff_bundle_summary(tmp_path: Path):
    graph = _demo_pic_graph()
    build_pic_layout_artifacts({"graph": graph}, tmp_path)
    routes = json.loads((tmp_path / "routes.json").read_text(encoding="utf-8"))
    ports = json.loads((tmp_path / "ports.json").read_text(encoding="utf-8"))

    signoff_bundle = {
        "resonance_alignment": {
            "channels": [
                {
                    "id": "ch0",
                    "target_wavelength_nm": 1550.0,
                    "observed_wavelength_nm": 1550.005,
                    "linewidth_pm": 35.0,
                }
            ],
            "max_detune_pm": 10.0,
            "min_linewidth_pm": 20.0,
            "max_linewidth_pm": 80.0,
        },
        "phase_shifter_range": {
            "shifters": [
                {
                    "id": "ps1",
                    "tuning_efficiency_rad_per_mw": 0.2,
                    "max_power_mw": 20.0,
                    "required_phase_span_rad": 3.0,
                }
            ],
            "max_total_power_mw": 25.0,
        },
    }

    lvs = run_pic_lvs_lite(
        {
            "graph": graph,
            "ports": ports,
            "routes": routes,
            "settings": {"coord_tol_um": 1e-6},
            "signoff_bundle": signoff_bundle,
        }
    )

    lvs_schema_path = Path("schemas") / "photonstrust.pic_lvs_lite.v0.schema.json"
    lvs_schema = json.loads(lvs_schema_path.read_text(encoding="utf-8"))
    validate(instance=lvs, schema=lvs_schema)

    assert "signoff_bundle" in lvs
    assert lvs["summary"]["signoff_pass"] is True
    assert lvs["summary"]["signoff_total_checks"] == 2
    assert lvs["summary"]["signoff_failed_checks"] == 0
    assert isinstance(lvs.get("violations_annotated", []), list)


def test_pic_layout_build_gds_is_deterministic_with_fixed_env_timestamp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pytest.importorskip("gdstk")
    graph = _demo_pic_graph()
    monkeypatch.setenv("PT_GDS_TIMESTAMP", "2026-02-14T12:34:56Z")

    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"
    rep_a = build_pic_layout_artifacts({"graph": graph}, out_a)
    rep_b = build_pic_layout_artifacts({"graph": graph}, out_b)

    assert rep_a["summary"]["gds_emitted"] is True
    assert rep_b["summary"]["gds_emitted"] is True
    assert (out_a / "layout.gds").read_bytes() == (out_b / "layout.gds").read_bytes()


def test_pic_layout_build_gds_is_deterministic_with_settings_timestamp(tmp_path: Path):
    pytest.importorskip("gdstk")
    graph = _demo_pic_graph()
    req = {"graph": graph, "settings": {"gds_timestamp": "2026-02-14T12:34:56Z"}}

    out_a = tmp_path / "run_a"
    out_b = tmp_path / "run_b"
    rep_a = build_pic_layout_artifacts(req, out_a)
    rep_b = build_pic_layout_artifacts(req, out_b)

    assert rep_a["summary"]["gds_emitted"] is True
    assert rep_b["summary"]["gds_emitted"] is True
    assert (out_a / "layout.gds").read_bytes() == (out_b / "layout.gds").read_bytes()
