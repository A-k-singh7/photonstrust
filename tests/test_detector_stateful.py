from __future__ import annotations

from photonstrust.physics.detector import simulate_detector


def test_detector_gating_reduces_click_probability():
    arrivals = [float(v) for v in range(0, 5000, 10)]
    base_cfg = {
        "pde": 1.0,
        "dark_counts_cps": 0.0,
        "jitter_ps_fwhm": 0.0,
        "dead_time_ns": 0.0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 10.0,
        "seed": 100,
    }
    ungated = simulate_detector(base_cfg, arrivals)
    gated = simulate_detector(
        {**base_cfg, "gate_width_ns": 0.01, "gate_period_ns": 0.05},
        arrivals,
    )
    assert gated.diagnostics["events_processed"] < ungated.diagnostics["events_processed"]
    assert gated.diagnostics["duty_cycle"] < ungated.diagnostics["duty_cycle"]


def test_detector_saturation_reduces_effective_clicks():
    arrivals = [float(v) for v in range(0, 2000, 2)]
    cfg_no_sat = {
        "pde": 0.8,
        "dark_counts_cps": 0.0,
        "jitter_ps_fwhm": 0.0,
        "dead_time_ns": 0.0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 5.0,
        "seed": 11,
    }
    cfg_sat = {**cfg_no_sat, "saturation_count_rate_cps": 5e7}

    no_sat = simulate_detector(cfg_no_sat, arrivals)
    sat = simulate_detector(cfg_sat, arrivals)

    assert sat.p_click <= no_sat.p_click
    assert sat.diagnostics["pde_effective"] <= no_sat.diagnostics["pde_effective"]


def test_detector_afterpulse_and_dead_time_remain_bounded():
    arrivals = [float(v) for v in range(0, 3000, 20)]
    cfg = {
        "pde": 0.7,
        "dark_counts_cps": 200.0,
        "jitter_ps_fwhm": 30.0,
        "dead_time_ns": 5.0,
        "afterpulsing_prob": 0.05,
        "afterpulse_delay_ns": 50.0,
        "time_bin_ps": 10.0,
        "seed": 123,
    }
    stats = simulate_detector(cfg, arrivals)
    assert 0.0 <= stats.p_click <= 1.0
    assert 0.0 <= stats.p_false <= 1.0
    assert 0.0 <= stats.diagnostics["duty_cycle"] <= 1.0


def test_detector_dead_time_reduces_click_probability_for_dense_arrivals():
    arrivals = [float(v) for v in range(0, 30000, 10)]
    base_cfg = {
        "pde": 1.0,
        "dark_counts_cps": 0.0,
        "jitter_ps_fwhm": 0.0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 10.0,
        "seed": 7,
    }
    fast = simulate_detector({**base_cfg, "dead_time_ns": 0.0}, arrivals)
    dead = simulate_detector({**base_cfg, "dead_time_ns": 2.0}, arrivals)
    assert dead.p_click < fast.p_click


def test_detector_afterpulse_increases_false_fraction_without_signal():
    cfg_no_ap = {
        "pde": 0.0,
        "dark_counts_cps": 5e8,
        "jitter_ps_fwhm": 0.0,
        "dead_time_ns": 0.0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 10.0,
        "seed": 99,
    }
    cfg_ap = {**cfg_no_ap, "afterpulsing_prob": 0.3, "afterpulse_delay_ns": 10.0}
    arrivals = [0.0, 1000.0]

    no_ap = simulate_detector(cfg_no_ap, arrivals)
    with_ap = simulate_detector(cfg_ap, arrivals)
    assert with_ap.p_false >= no_ap.p_false
