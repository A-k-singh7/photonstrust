from __future__ import annotations

import copy
import math

from photonstrust.qkd import compute_point


def _scenario() -> dict:
    return {
        "scenario_id": "bb84_decoy_test",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [10.0],
        "source": {
            "type": "wcp",
            "rep_rate_mhz": 200.0,
            "collection_efficiency": 1.0,
            "coupling_efficiency": 0.9,
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.75,
            "dark_counts_cps": 50.0,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 20.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {"sync_drift_ps_rms": 5.0, "coincidence_window_ps": 300.0},
        "protocol": {
            "name": "BB84_DECOY",
            "mu": 0.5,
            "nu": 0.1,
            "omega": 0.0,
            "sifting_factor": 0.5,
            "ec_efficiency": 1.16,
            "misalignment_prob": 0.015,
        },
    }


def test_bb84_decoy_surface_runs_and_populates_bounds() -> None:
    res = compute_point(_scenario(), distance_km=10.0)

    assert math.isfinite(res.key_rate_bps)
    assert res.key_rate_bps >= 0.0
    assert 0.0 <= res.qber_total <= 0.5
    assert res.protocol_name == "bb84_decoy"
    assert 0.0 <= res.single_photon_yield_lb <= 1.0
    assert 0.0 <= res.single_photon_error_ub <= 0.5


def test_bb84_decoy_key_rate_decreases_with_distance() -> None:
    scenario = _scenario()
    r10 = compute_point(scenario, distance_km=10.0).key_rate_bps
    r80 = compute_point(scenario, distance_km=80.0).key_rate_bps
    assert r10 >= r80


def test_bb84_decoy_finite_key_monotonicity() -> None:
    base = _scenario()

    loose = copy.deepcopy(base)
    loose["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1e10,
        "security_epsilon": 1e-6,
        "parameter_estimation_fraction": 0.1,
    }

    strict = copy.deepcopy(base)
    strict["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1e8,
        "security_epsilon": 1e-12,
        "parameter_estimation_fraction": 0.1,
    }

    asym = compute_point(base, distance_km=20.0)
    loose_res = compute_point(loose, distance_km=20.0)
    strict_res = compute_point(strict, distance_km=20.0)

    assert loose_res.finite_key_enabled is True
    assert loose_res.key_rate_bps <= asym.key_rate_bps
    assert strict_res.key_rate_bps <= loose_res.key_rate_bps
    assert loose_res.finite_key_epsilon > strict_res.finite_key_epsilon
