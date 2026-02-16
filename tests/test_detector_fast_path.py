from __future__ import annotations

from photonstrust.physics.detector import simulate_detector


def _base_cfg() -> dict:
    return {
        "pde": 0.7,
        "dark_counts_cps": 100.0,
        "jitter_ps_fwhm": 20.0,
        "dead_time_ns": 2.0,
        "afterpulsing_prob": 0.0,
        "afterpulse_delay_ns": 50.0,
        "time_bin_ps": 10.0,
        "seed": 123,
    }


def test_fast_path_selected_when_afterpulse_disabled():
    cfg = _base_cfg()
    stats = simulate_detector(cfg, arrival_times_ps=[float(v) for v in range(0, 1000, 20)])
    assert stats.diagnostics["path"] == "fast_no_afterpulse"


def test_legacy_path_selected_when_afterpulse_enabled():
    cfg = {**_base_cfg(), "afterpulsing_prob": 0.05}
    stats = simulate_detector(cfg, arrival_times_ps=[float(v) for v in range(0, 1000, 20)])
    assert stats.diagnostics["path"] == "heap_legacy"


def test_forcing_legacy_path_overrides_fast_path():
    cfg = {**_base_cfg(), "force_legacy_path": True}
    stats = simulate_detector(cfg, arrival_times_ps=[float(v) for v in range(0, 1000, 20)])
    assert stats.diagnostics["path"] == "heap_legacy"


def test_fast_path_deterministic_for_fixed_seed():
    cfg = _base_cfg()
    arrivals = [float(v) for v in range(0, 1000, 20)]
    a = simulate_detector(cfg, arrival_times_ps=arrivals)
    b = simulate_detector(cfg, arrival_times_ps=arrivals)

    assert a.p_click == b.p_click
    assert a.p_false == b.p_false
    assert a.click_time_hist == b.click_time_hist
    assert a.click_time_edges_ps == b.click_time_edges_ps
    assert a.variance_p_click == b.variance_p_click
    assert a.diagnostics == b.diagnostics
