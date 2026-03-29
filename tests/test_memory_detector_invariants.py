from __future__ import annotations

from photonstrust.physics.detector import simulate_detector
from photonstrust.physics.memory import simulate_memory


def test_memory_fidelity_is_monotonic_with_wait_time():
    cfg = {
        "t1_ms": 50.0,
        "t2_ms": 10.0,
        "store_efficiency": 0.95,
        "retrieval_efficiency": 0.8,
        "physics_backend": "analytic",
    }
    waits = [0.0, 1e5, 1e7, 1e9]
    stats = [simulate_memory(cfg, wait_time_ns=w) for w in waits]

    for idx in range(1, len(stats)):
        assert stats[idx].fidelity <= stats[idx - 1].fidelity
        assert 0.0 <= stats[idx].p_store <= 1.0
        assert 0.0 <= stats[idx].p_retrieve <= 1.0
        assert 0.0 <= stats[idx].fidelity <= 1.0


def test_memory_retrieval_probability_decreases_with_wait_time():
    cfg = {
        "t1_ms": 25.0,
        "t2_ms": 8.0,
        "store_efficiency": 0.9,
        "retrieval_efficiency": 0.85,
        "physics_backend": "analytic",
    }
    short = simulate_memory(cfg, wait_time_ns=1e3)
    long = simulate_memory(cfg, wait_time_ns=2e9)

    assert long.p_retrieve <= short.p_retrieve


def test_detector_click_probability_monotonic_with_pde_for_fixed_seed():
    arrivals = [float(v) for v in range(0, 4000, 10)]
    low_cfg = {
        "pde": 0.2,
        "dark_counts_cps": 0.0,
        "jitter_ps_fwhm": 0.0,
        "dead_time_ns": 0.0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 10.0,
        "seed": 21,
    }
    high_cfg = dict(low_cfg)
    high_cfg["pde"] = 0.8

    low = simulate_detector(low_cfg, arrivals)
    high = simulate_detector(high_cfg, arrivals)

    assert high.p_click >= low.p_click
    assert 0.0 <= low.p_click <= 1.0
    assert 0.0 <= high.p_click <= 1.0
    assert 0.0 <= low.p_false <= 1.0
    assert 0.0 <= high.p_false <= 1.0


def test_detector_dead_time_reduces_click_rate():
    arrivals = [float(v) for v in range(0, 2000, 5)]
    cfg_no_dead = {
        "pde": 1.0,
        "dark_counts_cps": 0.0,
        "jitter_ps_fwhm": 0.0,
        "dead_time_ns": 0.0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 5.0,
        "seed": 9,
    }
    cfg_dead = dict(cfg_no_dead)
    cfg_dead["dead_time_ns"] = 0.5

    no_dead = simulate_detector(cfg_no_dead, arrivals)
    dead = simulate_detector(cfg_dead, arrivals)

    assert dead.p_click <= no_dead.p_click


def test_detector_deterministic_for_fixed_seed():
    arrivals = [float(v) for v in range(0, 2500, 25)]
    cfg = {
        "pde": 0.55,
        "dark_counts_cps": 200.0,
        "jitter_ps_fwhm": 30.0,
        "dead_time_ns": 10.0,
        "afterpulsing_prob": 0.01,
        "afterpulse_delay_ns": 50.0,
        "time_bin_ps": 10.0,
        "seed": 1234,
    }
    a = simulate_detector(cfg, arrivals)
    b = simulate_detector(cfg, arrivals)

    assert a.p_click == b.p_click
    assert a.p_false == b.p_false
    assert a.variance_p_click == b.variance_p_click
    assert a.click_time_hist == b.click_time_hist
    assert a.click_time_edges_ps == b.click_time_edges_ps
