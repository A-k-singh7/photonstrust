from __future__ import annotations

import copy

import pytest

from photonstrust.qkd import compute_point


def _base_bbm92_scenario() -> dict:
    return {
        "source": {
            "type": "spdc",
            "rep_rate_mhz": 500.0,
            "collection_efficiency": 1.0,
            "coupling_efficiency": 1.0,
            "mu": 0.05,
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 22.0,
            "dispersion_ps_per_km": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.8,
            "dark_counts_cps": 5.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 0.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {
            "sync_drift_ps_rms": 10.0,
            "coincidence_window_ps": 100.0,
        },
        "protocol": {
            "name": "BBM92",
            "sifting_factor": 0.5,
            "ec_efficiency": 1.16,
            "misalignment_prob": 0.02,
        },
    }


def test_bbm92_default_topology_matches_explicit_direct_link() -> None:
    scenario_default = _base_bbm92_scenario()
    scenario_direct = _base_bbm92_scenario()
    scenario_direct["protocol"]["entanglement_topology"] = "direct_link"

    default_result = compute_point(scenario_default, distance_km=200.0)
    direct_result = compute_point(scenario_direct, distance_km=200.0)

    assert default_result.key_rate_bps == pytest.approx(direct_result.key_rate_bps, rel=0.0, abs=0.0)
    assert default_result.qber_total == pytest.approx(direct_result.qber_total, rel=0.0, abs=0.0)
    assert default_result.loss_db == pytest.approx(direct_result.loss_db, rel=0.0, abs=0.0)


def test_bbm92_midpoint_topology_can_raise_ultrabright_rate() -> None:
    scenario_direct = _base_bbm92_scenario()
    scenario_midpoint = _base_bbm92_scenario()
    scenario_midpoint["protocol"]["entanglement_topology"] = "midpoint_source"
    scenario_midpoint["protocol"]["relay_fraction"] = 0.5
    scenario_midpoint["protocol"]["split_connector_loss"] = True

    direct_result = compute_point(scenario_direct, distance_km=200.0)
    midpoint_result = compute_point(scenario_midpoint, distance_km=200.0)

    assert midpoint_result.key_rate_bps > direct_result.key_rate_bps * 1000.0
    assert isinstance(midpoint_result.protocol_diagnostics, dict)
    assert midpoint_result.protocol_diagnostics["entanglement_topology"] == "midpoint_source"
    assert midpoint_result.protocol_diagnostics["distance_a_km"] == pytest.approx(100.0)
    assert midpoint_result.protocol_diagnostics["distance_b_km"] == pytest.approx(100.0)


def test_bbm92_parallel_mode_count_scales_rate() -> None:
    single_mode = _base_bbm92_scenario()
    single_mode["protocol"]["entanglement_topology"] = "midpoint_source"
    single_mode["protocol"]["relay_fraction"] = 0.5
    single_mode["protocol"]["split_connector_loss"] = True
    single_mode["source"]["parallel_mode_count"] = 1.0

    many_mode = copy.deepcopy(single_mode)
    many_mode["source"]["parallel_mode_count"] = 64.0

    single = compute_point(single_mode, distance_km=200.0)
    many = compute_point(many_mode, distance_km=200.0)

    assert many.entanglement_rate_hz == pytest.approx(single.entanglement_rate_hz * 64.0, rel=1e-12, abs=0.0)
    assert many.key_rate_bps == pytest.approx(single.key_rate_bps * 64.0, rel=1e-12, abs=0.0)
    assert many.qber_total == pytest.approx(single.qber_total, rel=0.0, abs=0.0)
