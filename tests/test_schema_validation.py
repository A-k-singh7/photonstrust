from pathlib import Path

import json

from jsonschema import validate

from photonstrust.qkd import compute_point
from photonstrust.report import build_reliability_card


def test_reliability_card_schema():
    scenario = {
        "scenario_id": "test_schema",
        "band": "c_1550",
        "wavelength_nm": 1550,
        "distances_km": [10.0],
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "physics_backend": "analytic",
        },
        "channel": {
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
    }

    result = compute_point(scenario, distance_km=10)
    card = build_reliability_card(scenario, [result], None, Path("."))

    schema_path = Path("schemas") / "photonstrust.reliability_card.v1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=card, schema=schema)


def test_benchmark_bundle_schema_minimal_instance():
    bundle = {
        "schema_version": "0",
        "benchmark_id": "bench_demo_001",
        "kind": "qkd_sweep",
        "config": {"scenario": {"id": "x", "distance_km": 1.0, "band": "c_1550", "wavelength_nm": 1550}},
        "expected": {
            "qkd_sweeps": [
                {
                    "scenario_id": "x",
                    "band": "c_1550",
                    "distances_km": [1.0],
                    "key_rate_bps": [0.0],
                }
            ]
        },
    }
    schema_path = Path("schemas") / "photonstrust.benchmark_bundle.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=bundle, schema=schema)


def test_repro_pack_manifest_schema_minimal_instance():
    manifest = {
        "schema_version": "0",
        "generated_at": "2026-02-13T00:00:00Z",
        "pack_id": "pack_demo_001",
        "benchmark_bundle_path": "benchmark_bundle.json",
        "reference_outputs_dir": "reference_outputs",
        "env": {"python": "3.11.0", "platform": "test", "pip_freeze_path": "env/pip_freeze.txt"},
        "scripts": {"run_ps1": "run.ps1", "run_sh": "run.sh", "verify_py": "verify.py"},
        "provenance": {"config_hash": "0" * 64},
    }
    schema_path = Path("schemas") / "photonstrust.repro_pack_manifest.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=manifest, schema=schema)


def test_graph_schema_minimal_instances():
    qkd_graph = {
        "schema_version": "0.1",
        "graph_id": "graph_demo_qkd",
        "profile": "qkd_link",
        "scenario": {"id": "x", "distance_km": 1.0, "band": "c_1550", "wavelength_nm": 1550},
        "nodes": [
            {"id": "s", "kind": "qkd.source", "params": {"type": "emitter_cavity"}},
            {"id": "c", "kind": "qkd.channel", "params": {"model": "fiber"}},
            {"id": "d", "kind": "qkd.detector", "params": {"class": "snspd"}},
            {"id": "t", "kind": "qkd.timing", "params": {"sync_drift_ps_rms": 10}},
            {"id": "p", "kind": "qkd.protocol", "params": {"name": "BBM92"}},
        ],
        "edges": [],
    }

    pic_graph = {
        "schema_version": "0.1",
        "graph_id": "graph_demo_pic",
        "profile": "pic_circuit",
        "circuit": {"id": "pic_x", "wavelength_nm": 1550},
        "nodes": [
            {"id": "n1", "kind": "pic.waveguide", "params": {"length_um": 1000}},
            {"id": "n2", "kind": "pic.waveguide", "params": {"length_um": 2000}},
        ],
        "edges": [{"from": "n1", "to": "n2", "kind": "optical"}],
    }

    # Optional edge params should be accepted by the schema.
    pic_graph_with_edge_params = {
        **pic_graph,
        "graph_id": "graph_demo_pic_params",
        "edges": [{"from": "n1", "to": "n2", "kind": "optical", "params": {"length_um": 1000.0}}],
    }

    schema_path = Path("schemas") / "photonstrust.graph.v0_1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=qkd_graph, schema=schema)
    validate(instance=pic_graph, schema=schema)
    validate(instance=pic_graph_with_edge_params, schema=schema)
