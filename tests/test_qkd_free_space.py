from photonstrust.qkd import compute_point


def _free_space_scenario(background_counts_cps: float) -> dict:
    return {
        "scenario_id": "free_space_case",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [500.0],
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
            "model": "free_space",
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 0.0,
            "elevation_deg": 45.0,
            "tx_aperture_m": 0.12,
            "rx_aperture_m": 0.30,
            "beam_divergence_urad": 12.0,
            "pointing_jitter_urad": 1.5,
            "atmospheric_extinction_db_per_km": 0.02,
            "turbulence_scintillation_index": 0.12,
            "background_counts_cps": background_counts_cps,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 100.0,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10.0, "coincidence_window_ps": 200.0},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
    }


def test_free_space_qkd_distance_penalty():
    scenario = _free_space_scenario(background_counts_cps=100.0)
    near = compute_point(scenario, distance_km=300.0)
    far = compute_point(scenario, distance_km=800.0)

    assert far.key_rate_bps <= near.key_rate_bps
    assert far.loss_db >= near.loss_db


def test_free_space_background_penalty():
    low_bg = _free_space_scenario(background_counts_cps=10.0)
    high_bg = _free_space_scenario(background_counts_cps=5000.0)

    low = compute_point(low_bg, distance_km=500.0)
    high = compute_point(high_bg, distance_km=500.0)

    assert high.qber_total >= low.qber_total
    assert high.key_rate_bps <= low.key_rate_bps
