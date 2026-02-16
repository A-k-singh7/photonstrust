from photonstrust.physics.detector import simulate_detector


def test_detector_click_prob_bounds():
    cfg = {
        "pde": 0.5,
        "dark_counts_cps": 100,
        "jitter_ps_fwhm": 50,
        "dead_time_ns": 0,
        "afterpulsing_prob": 0.0,
        "time_bin_ps": 10.0,
    }
    stats = simulate_detector(cfg, arrival_times_ps=[10, 20, 30, 40])
    assert 0.0 <= stats.p_click <= 1.0
