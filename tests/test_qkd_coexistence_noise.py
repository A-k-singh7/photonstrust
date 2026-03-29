from __future__ import annotations

import copy

from photonstrust.qkd import compute_point


def _scenario() -> dict:
    return {
        "scenario_id": "raman_test",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [50.0],
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100.0,
            "collection_efficiency": 0.60,
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
            "coexistence": {
                "enabled": True,
                "classical_launch_power_dbm": 0.0,
                "classical_channel_count": 1,
                "direction": "co",
                "filter_bandwidth_nm": 0.2,
                "raman_coeff_cps_per_km_per_mw_per_nm": 1200.0,
                "raman_spectral_factor": 1.0,
            },
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


def test_raman_launch_power_penalizes_qkd_metrics():
    base = _scenario()
    low_power = copy.deepcopy(base)
    high_power = copy.deepcopy(base)
    low_power["channel"]["coexistence"]["classical_launch_power_dbm"] = 0.0
    high_power["channel"]["coexistence"]["classical_launch_power_dbm"] = 10.0

    low = compute_point(low_power, distance_km=50.0)
    high = compute_point(high_power, distance_km=50.0)

    assert high.raman_counts_cps > low.raman_counts_cps
    assert high.qber_total >= low.qber_total
    assert high.key_rate_bps <= low.key_rate_bps
