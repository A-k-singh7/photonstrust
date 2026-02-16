from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.config import build_scenarios
from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.spec import load_graph_file
from photonstrust.qkd import compute_sweep


def test_compile_qkd_link_graph_runs_through_engine():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test_qkd_graph",
        "profile": "qkd_link",
        "scenario": {
            "id": "test_qkd_graph",
            "distance_km": {"start": 0.0, "stop": 20.0, "step": 10.0},
            "band": "c_1550",
            "wavelength_nm": 1550,
            "execution_mode": "preview",
        },
        "uncertainty": {},
        "nodes": [
            {"id": "s", "kind": "qkd.source", "params": {"type": "emitter_cavity", "physics_backend": "analytic"}},
            {"id": "c", "kind": "qkd.channel", "params": {"model": "fiber", "fiber_loss_db_per_km": None, "connector_loss_db": 1.5, "dispersion_ps_per_km": None}},
            {"id": "d", "kind": "qkd.detector", "params": {"class": "snspd"}},
            {"id": "t", "kind": "qkd.timing", "params": {"sync_drift_ps_rms": 10, "coincidence_window_ps": None}},
            {"id": "p", "kind": "qkd.protocol", "params": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16}},
        ],
        "edges": [],
    }

    compiled = compile_graph(graph)
    assert compiled.profile == "qkd_link"

    config = compiled.compiled
    scenarios = build_scenarios(config)
    assert len(scenarios) == 1
    sweep = compute_sweep(scenarios[0], include_uncertainty=False)
    assert len(sweep["results"]) == 3


def test_compile_pic_circuit_graph_has_deterministic_topology_order():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test_pic_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "test_pic_graph", "wavelength_nm": 1550},
        "nodes": [
            {"id": "a", "kind": "pic.waveguide", "params": {"length_um": 100}},
            {"id": "b", "kind": "pic.waveguide", "params": {"length_um": 200}},
            {"id": "c", "kind": "pic.waveguide", "params": {"length_um": 300}},
            {"id": "d", "kind": "pic.waveguide", "params": {"length_um": 400}},
        ],
        "edges": [
            {"from": "a", "to": "b", "kind": "optical"},
            {"from": "b", "to": "c", "kind": "optical"},
        ],
    }

    compiled = compile_graph(graph)
    assert compiled.profile == "pic_circuit"
    order = compiled.compiled["topology"]["topological_order"]
    assert order == ["a", "b", "c", "d"]


def test_compile_pic_circuit_graph_rejects_cycles():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test_pic_cycle",
        "profile": "pic_circuit",
        "circuit": {"id": "test_pic_cycle"},
        "nodes": [
            {"id": "a", "kind": "pic.waveguide", "params": {}},
            {"id": "b", "kind": "pic.waveguide", "params": {}},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
    }
    with pytest.raises(ValueError, match="cycle"):
        compile_graph(graph)


def test_compile_pic_circuit_graph_allows_cycles_in_scattering_mode():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test_pic_cycle_scattering",
        "profile": "pic_circuit",
        "circuit": {"id": "test_pic_cycle_scattering", "solver": "scattering"},
        "nodes": [
            {"id": "a", "kind": "pic.waveguide", "params": {}},
            {"id": "b", "kind": "pic.waveguide", "params": {}},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}],
    }

    compiled = compile_graph(graph)
    assert compiled.profile == "pic_circuit"
    assert compiled.compiled["topology"]["is_dag"] is False


def test_compile_pic_circuit_graph_rejects_missing_endpoints():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test_pic_missing",
        "profile": "pic_circuit",
        "circuit": {"id": "test_pic_missing"},
        "nodes": [{"id": "a", "kind": "pic.waveguide", "params": {}}],
        "edges": [{"from": "a", "to": "b"}],
    }
    with pytest.raises(ValueError, match="missing node"):
        compile_graph(graph)


def test_cli_graph_compile_smoke(tmp_path: Path):
    # Verify the CLI can compile the demo graph file.
    root = Path(__file__).resolve().parents[1]
    graph_path = root / "graphs" / "demo8_qkd_link_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    out = tmp_path / "compiled"

    from photonstrust.graph.compiler import compile_graph_artifacts

    artifacts = compile_graph_artifacts(graph, out)
    assert (out / "graph.json").exists()
    assert (out / "compiled_config.yml").exists()
    assert (out / "compile_provenance.json").exists()
    assert (out / "assumptions.md").exists()
    assert artifacts["compiled_path"] is not None


def test_compile_pic_circuit_graph_rejects_kind_domain_mismatch():
    graph = {
        "schema_version": "0.1",
        "graph_id": "test_pic_domain_mismatch",
        "profile": "pic_circuit",
        "circuit": {"id": "test_pic_domain_mismatch", "solver": "dag"},
        "nodes": [
            {"id": "a", "kind": "pic.waveguide", "params": {"length_um": 100}},
            {"id": "b", "kind": "pic.waveguide", "params": {"length_um": 100}},
        ],
        "edges": [
            {"from": "a", "to": "b", "from_port": "out", "to_port": "in", "kind": "electrical"},
        ],
    }

    with pytest.raises(ValueError, match="incompatible"):
        compile_graph(graph)


def test_load_graph_file_toml_compile_path(tmp_path: Path):
    src = """
schema_version = "0.1"
graph_id = "test_toml_qkd"
profile = "qkd_link"
scenario = { id = "test_toml_qkd", distance_km = 1, band = "c_1550", wavelength_nm = 1550 }

[[nodes]]
id = "source_1"
kind = "qkd.source"
params = { type = "emitter_cavity" }

[[nodes]]
id = "channel_1"
kind = "qkd.channel"
params = { model = "fiber" }

[[nodes]]
id = "detector_1"
kind = "qkd.detector"
params = { class = "snspd" }

[[nodes]]
id = "timing_1"
kind = "qkd.timing"
params = { sync_drift_ps_rms = 10 }

[[nodes]]
id = "protocol_1"
kind = "qkd.protocol"
params = { name = "BBM92" }
""".strip()
    path = tmp_path / "graph.ptg.toml"
    path.write_text(src + "\n", encoding="utf-8")

    graph = load_graph_file(path)
    compiled = compile_graph(graph)
    assert compiled.profile == "qkd_link"
