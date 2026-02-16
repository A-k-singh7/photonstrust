from __future__ import annotations

import math

import pytest

from photonstrust.qkd import compute_point
from photonstrust.qkd_protocols.common import apply_dead_time, per_pulse_prob_from_rate


def test_per_pulse_prob_from_rate_matches_poisson_at_least_one() -> None:
    # lambda = 1 -> p = 1 - exp(-1)
    rate_cps = 1e6
    window_s = 1e-6
    expected = 1.0 - math.exp(-1.0)
    got = per_pulse_prob_from_rate(rate_cps, window_s)
    assert got == pytest.approx(expected, rel=0.0, abs=1e-15)
    assert 0.0 <= got <= 1.0


def test_apply_dead_time_nonparalyzable_default_matches_formula() -> None:
    rate_in = 1.0e6
    tau = 1.0e-6
    expected = rate_in / (1.0 + rate_in * tau)
    out, scale = apply_dead_time(rate_in, tau)
    assert out == pytest.approx(expected, rel=0.0, abs=1e-9)
    assert scale == pytest.approx(expected / rate_in, rel=0.0, abs=1e-15)


def test_direct_link_uses_poisson_noise_probability_and_dead_time() -> None:
    # Choose lambda = rate*window = 1 to distinguish from linear approximation.
    # Kill signal so p_false is easy to reason about.
    scenario = {
        "scenario_id": "phase44_poisson_semantics",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [0.0],
        "source": {
            "type": "spdc",
            "rep_rate_mhz": 1.0,
            "collection_efficiency": 1.0,
            "coupling_efficiency": 1.0,
            "mu": 0.0,
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.0,
            "connector_loss_db": 0.0,
            "dispersion_ps_per_km": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 1.0,
            "dark_counts_cps": 1e6,
            "jitter_ps_fwhm": 0.0,
            "dead_time_ns": 1000.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {
            "sync_drift_ps_rms": 0.0,
            "coincidence_window_ps": 1e6,
        },
        "protocol": {"name": "BBM92", "sifting_factor": 1.0, "ec_efficiency": 1.0},
    }

    res = compute_point(scenario, distance_km=0.0)

    window_s = scenario["timing"]["coincidence_window_ps"] * 1e-12
    lam = scenario["detector"]["dark_counts_cps"] * window_s
    # In the coincidence-based BBM92 model, a "false" coincidence requires a
    # click on both sides. With no signal present, p_false becomes the pure
    # noise-coincidence probability.
    expected_p_false = (1.0 - math.exp(-lam)) ** 2
    assert res.p_pair == 0.0
    assert res.p_false == pytest.approx(expected_p_false, rel=0.0, abs=1e-12)

    rep_rate_hz = scenario["source"]["rep_rate_mhz"] * 1e6
    r_in = rep_rate_hz * expected_p_false
    tau_s = scenario["detector"]["dead_time_ns"] * 1e-9
    expected_r_out = r_in / (1.0 + r_in * tau_s)
    assert res.entanglement_rate_hz == pytest.approx(expected_r_out, rel=1e-12, abs=0.0)
