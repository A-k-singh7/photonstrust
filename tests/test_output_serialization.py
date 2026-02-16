from __future__ import annotations

import json
from pathlib import Path

from photonstrust.cli import _write_json
from photonstrust.optimize.optimizer import run_optimization
from photonstrust.repeater import run_repeater_optimization
from photonstrust.scenarios.source_benchmark import run_source_benchmark


def _qkd_scenario() -> dict:
    return {
        "band": "c_1550",
        "wavelength_nm": 1550,
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
            "pulse_window_ns": 5.0,
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
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
    }


def test_cli_write_json_outputs_valid_json(tmp_path):
    payload = {
        "summary": {"x": 1, "interval": [0.1, 0.9]},
        "best": {"alpha": 0.5},
        "weights": [0.2, 0.3, 0.5],
    }
    out = tmp_path / "calibration.json"
    _write_json(out, payload)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded == payload


def test_repeater_results_json_is_parseable(tmp_path):
    cfg = {
        "repeater_optimization": {
            "id": "repeater_json_test",
            "total_distance_km": [100.0],
            "spacing_km": {"start": 10.0, "stop": 20.0, "step": 10.0},
            "memory": {
                "t1_ms": 50.0,
                "t2_ms": 10.0,
                "retrieval_efficiency": 0.75,
                "store_efficiency": 0.95,
                "physics_backend": "analytic",
            },
            "link_scenario": _qkd_scenario(),
        }
    }
    run_repeater_optimization(cfg, tmp_path)
    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert "100.0" in payload or 100.0 in payload


def test_optimization_best_json_is_parseable(tmp_path):
    cfg = {
        "optimization": {
            "id": "opt_json_test",
            "type": "repeater_spacing",
            "total_distance_km": [100.0],
            "spacing_km": {"start": 10.0, "stop": 20.0, "step": 10.0},
            "memory": {
                "t1_ms": 50.0,
                "t2_ms": 10.0,
                "retrieval_efficiency": 0.75,
                "store_efficiency": 0.95,
                "physics_backend": "analytic",
            },
            "link_scenario": _qkd_scenario(),
        }
    }
    run_optimization(cfg, tmp_path)
    payload = json.loads((tmp_path / "best.json").read_text(encoding="utf-8"))
    key = next(iter(payload.keys()))
    assert "local_sensitivity" in payload[key]


def test_source_benchmark_json_is_parseable(tmp_path):
    cfg = {
        "source_benchmark": {
            "id": "source_json_test",
            "distance_km": 10.0,
            "source": {**_qkd_scenario()["source"]},
            "link_scenario": _qkd_scenario(),
        }
    }
    run_source_benchmark(cfg, tmp_path)
    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert "projected_key_rate_bps" in payload
    assert "projected_fidelity" in payload

