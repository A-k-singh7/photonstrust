from photonstrust.qkd import compute_point


def test_qkd_key_rate_non_negative():
    scenario = {
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "physics_backend": "analytic",
        },
        "channel": {
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"sifting_factor": 0.5, "ec_efficiency": 1.16},
    }

    result = compute_point(scenario, distance_km=10)
    assert result.key_rate_bps >= 0
