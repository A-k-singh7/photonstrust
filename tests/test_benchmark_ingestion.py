from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from photonstrust.benchmarks.ingest import ingest_bundle_file
from photonstrust.benchmarks.open_benchmarks import check_open_benchmarks
from photonstrust.config import build_scenarios
from photonstrust.qkd import compute_sweep


def _minimal_qkd_config() -> dict:
    return {
        "scenario": {
            "id": "bench_demo",
            "distance_km": {"start": 0.0, "stop": 10.0, "step": 10.0},
            "band": "c_1550",
            "wavelength_nm": 1550,
        },
        "source": {
            "type": "emitter_cavity",
            "physics_backend": "analytic",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.60,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "pulse_window_ns": 5.0,
        },
        "channel": {"fiber_loss_db_per_km": 0.2, "connector_loss_db": 1.5, "dispersion_ps_per_km": 5.0},
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
        "uncertainty": {},
    }


def test_ingest_bundle_writes_registry_and_check_passes(tmp_path: Path):
    cfg = _minimal_qkd_config()
    scenarios = build_scenarios(cfg)
    assert len(scenarios) == 1
    sweep = compute_sweep(scenarios[0], include_uncertainty=False)
    results = sweep["results"]

    bundle = {
        "schema_version": "0",
        "benchmark_id": "bench_demo_001",
        "kind": "qkd_sweep",
        "title": "pytest fixture bundle",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": cfg,
        "defaults": {"rel_tol": 1e-6, "abs_tol": 1e-12},
        "expected": {
            "qkd_sweeps": [
                {
                    "scenario_id": scenarios[0]["scenario_id"],
                    "band": scenarios[0]["band"],
                    "distances_km": [r.distance_km for r in results],
                    "key_rate_bps": [r.key_rate_bps for r in results],
                }
            ]
        },
    }

    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    open_root = tmp_path / "open"
    ingested_path = ingest_bundle_file(bundle_path, open_root=open_root)
    assert ingested_path.exists()
    assert (open_root / "index.json").exists()

    # Check open benchmark runner accepts it.
    ok, failures = check_open_benchmarks(open_root)
    assert ok, "\n".join(failures)


def test_ingest_bundle_overwrite_guard(tmp_path: Path):
    bundle = {
        "schema_version": "0",
        "benchmark_id": "bench_demo_002",
        "kind": "qkd_sweep",
        "config": {"scenario": {"id": "x", "distance_km": 1.0, "band": "c_1550", "wavelength_nm": 1550}},
        "expected": {"qkd_sweeps": [{"scenario_id": "x", "band": "c_1550", "distances_km": [1.0], "key_rate_bps": [0.0]}]},
    }
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    open_root = tmp_path / "open"

    ingest_bundle_file(bundle_path, open_root=open_root)
    with pytest.raises(FileExistsError):
        ingest_bundle_file(bundle_path, open_root=open_root, overwrite=False)

