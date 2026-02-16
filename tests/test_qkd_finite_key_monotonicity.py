from __future__ import annotations

import copy

from photonstrust.qkd import compute_point


def _scenario() -> dict:
    return {
        "scenario_id": "finite_key_test",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [20.0],
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100.0,
            "collection_efficiency": 0.55,
            "coupling_efficiency": 0.70,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5.0,
            "dephasing_rate_per_ns": 0.2,
            "g2_0": 0.01,
            "physics_backend": "analytic",
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.8,
            "dark_counts_cps": 10.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 0.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {"sync_drift_ps_rms": 10.0, "coincidence_window_ps": 200.0},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
    }


def test_finite_key_enabled_reduces_key_rate_vs_asymptotic():
    base = _scenario()
    finite = copy.deepcopy(base)
    finite["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1.0e10,
        "security_epsilon": 1.0e-10,
        "parameter_estimation_fraction": 0.1,
    }

    asym = compute_point(base, distance_km=20.0)
    fk = compute_point(finite, distance_km=20.0)

    assert fk.finite_key_enabled is True
    assert fk.key_rate_bps <= asym.key_rate_bps


def test_finite_key_monotonic_with_block_size_and_epsilon():
    base = _scenario()

    big_n = copy.deepcopy(base)
    big_n["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1.0e12,
        "security_epsilon": 1.0e-10,
        "parameter_estimation_fraction": 0.1,
    }
    small_n = copy.deepcopy(base)
    small_n["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1.0e8,
        "security_epsilon": 1.0e-10,
        "parameter_estimation_fraction": 0.1,
    }

    strict_eps = copy.deepcopy(base)
    strict_eps["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1.0e10,
        "security_epsilon": 1.0e-12,
        "parameter_estimation_fraction": 0.1,
    }
    loose_eps = copy.deepcopy(base)
    loose_eps["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1.0e10,
        "security_epsilon": 1.0e-6,
        "parameter_estimation_fraction": 0.1,
    }

    res_big_n = compute_point(big_n, distance_km=20.0)
    res_small_n = compute_point(small_n, distance_km=20.0)
    assert res_small_n.key_rate_bps <= res_big_n.key_rate_bps

    res_strict_eps = compute_point(strict_eps, distance_km=20.0)
    res_loose_eps = compute_point(loose_eps, distance_km=20.0)
    assert res_strict_eps.key_rate_bps <= res_loose_eps.key_rate_bps

