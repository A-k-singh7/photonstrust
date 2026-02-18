from __future__ import annotations

import math
from pathlib import Path

from photonstrust.benchmarks.research_validation import run_research_validation_suite
from photonstrust.physics import build_source_profile
from photonstrust.qkd import compute_point


def test_spdc_source_profile_uses_thermal_geometric_statistics() -> None:
    mu = 0.5
    profile = build_source_profile({"type": "spdc", "mu": mu})
    expected = mu / (1.0 + mu)
    assert profile.emission_prob == expected
    assert profile.p_multi == expected
    assert profile.diagnostics["model"] == "spdc_thermal_geometric"


def test_pm_qkd_asymmetric_split_is_invariant_in_loss_only_setting() -> None:
    scenario = {
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
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 0.0,
            "dispersion_ps_per_km": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.8,
            "dark_counts_cps": 0.0,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 10,
            "dead_time_ns": 0.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {"sync_drift_ps_rms": 0.0, "coincidence_window_ps": 100.0},
        "protocol": {
            "name": "PM_QKD",
            "sifting_factor": 1.0,
            "ec_efficiency": 1.0,
            "misalignment_prob": 0.0,
            "mu": 0.2,
            "phase_slices": 16,
            "relay_fraction": 0.5,
        },
    }

    symmetric = compute_point(scenario, distance_km=100.0).key_rate_bps
    scenario["protocol"]["relay_fraction"] = 0.1
    asymmetric = compute_point(scenario, distance_km=100.0).key_rate_bps
    assert symmetric > 0.0
    assert math.isclose(asymmetric, symmetric, rel_tol=1e-12, abs_tol=1e-12)


def test_research_validation_suite_passes() -> None:
    report = run_research_validation_suite(repo_root=Path(__file__).resolve().parents[1])
    assert report["ok"] is True
    checks = {row["name"]: row for row in report["checks"]}
    assert checks["spdc_thermal_geometric_statistics"]["ok"] is True
    assert checks["pm_qkd_geometric_mean_asymmetry_scaling"]["ok"] is True
    assert checks["direct_link_plob_bound"]["ok"] is True
    assert checks["mdi_eq1_ec_efficiency_sensitivity"]["ok"] is True
