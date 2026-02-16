from __future__ import annotations

from photonstrust.physics import build_detector_profile, build_source_profile
from photonstrust.qkd import compute_point


def _base_scenario() -> dict:
    return {
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.2,
            "g2_0": 0.02,
            "physics_backend": "analytic",
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 5,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.6,
            "dark_counts_cps": 50,
            "background_counts_cps": 25,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.0,
            "model_tier": 0,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"name": "bbm92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
    }


def test_structured_profiles_are_constructible():
    scenario = _base_scenario()
    det = build_detector_profile(scenario["detector"])
    src = build_source_profile(scenario["source"])

    assert det.tier == 0
    assert 0.0 <= det.pde <= 1.0
    assert 0.0 <= src.emission_prob <= 1.0
    assert 0.0 <= src.p_multi <= 1.0


def test_tier1_jitter_window_capture_reduces_key_rate():
    scenario = _base_scenario()
    scenario["detector"]["model_tier"] = 1
    scenario["detector"]["jitter_ps_fwhm"] = 800.0
    scenario["timing"]["coincidence_window_ps"] = 40.0

    tier1 = compute_point(scenario, distance_km=10)

    scenario_t0 = _base_scenario()
    scenario_t0["detector"]["model_tier"] = 0
    scenario_t0["detector"]["jitter_ps_fwhm"] = 800.0
    scenario_t0["timing"]["coincidence_window_ps"] = 40.0
    tier0 = compute_point(scenario_t0, distance_km=10)

    assert tier1.key_rate_bps < tier0.key_rate_bps


def test_dead_time_limits_event_rate():
    scenario_fast = _base_scenario()
    scenario_fast["detector"]["dead_time_ns"] = 0.0
    fast = compute_point(scenario_fast, distance_km=5)

    scenario_slow = _base_scenario()
    scenario_slow["detector"]["dead_time_ns"] = 3000.0
    slow = compute_point(scenario_slow, distance_km=5)

    assert slow.entanglement_rate_hz < fast.entanglement_rate_hz
    assert slow.key_rate_bps <= fast.key_rate_bps


def test_tier1_afterpulse_inflates_false_clicks():
    scenario = _base_scenario()
    scenario["detector"]["model_tier"] = 1
    scenario["detector"]["afterpulsing_prob"] = 0.2
    with_afterpulse = compute_point(scenario, distance_km=20)

    no_afterpulse = _base_scenario()
    no_afterpulse["detector"]["model_tier"] = 1
    no_afterpulse["detector"]["afterpulsing_prob"] = 0.0
    baseline = compute_point(no_afterpulse, distance_km=20)

    assert with_afterpulse.p_false >= baseline.p_false
