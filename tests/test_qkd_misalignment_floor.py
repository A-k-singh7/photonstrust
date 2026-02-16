from __future__ import annotations

import copy

import pytest

from photonstrust.qkd import compute_point


def _scenario() -> dict:
    return {
        "scenario_id": "misalignment_test",
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


def test_misalignment_prob_increases_qber_and_decreases_key_rate():
    aligned = _scenario()
    misaligned = copy.deepcopy(aligned)
    misaligned["protocol"]["misalignment_prob"] = 0.02

    a = compute_point(aligned, distance_km=20.0)
    b = compute_point(misaligned, distance_km=20.0)

    assert b.q_misalignment > a.q_misalignment
    assert b.qber_total >= a.qber_total
    assert b.key_rate_bps <= a.key_rate_bps


def test_optical_visibility_maps_to_qber_floor():
    scenario = _scenario()
    # Remove accidental/false-coincidence contributions so the visibility mapping
    # is directly observable in QBER.
    scenario["source"]["g2_0"] = 0.0
    scenario["detector"]["dark_counts_cps"] = 0.0
    scenario["detector"]["background_counts_cps"] = 0.0
    scenario["channel"]["background_counts_cps"] = 0.0
    scenario["protocol"]["optical_visibility"] = 0.90
    res = compute_point(scenario, distance_km=20.0)
    expected = (1.0 - 0.90) / 2.0
    assert res.qber_total == pytest.approx(expected, rel=0, abs=1e-12)
    assert res.q_misalignment == pytest.approx(expected, rel=0, abs=1e-12)


def test_source_visibility_penalizes_qkd_metrics():
    base = _scenario()
    degraded = copy.deepcopy(base)
    degraded["source"]["hom_visibility"] = 0.90

    a = compute_point(base, distance_km=20.0)
    b = compute_point(degraded, distance_km=20.0)

    assert b.q_source > a.q_source
    assert b.qber_total >= a.qber_total
    assert b.key_rate_bps <= a.key_rate_bps
