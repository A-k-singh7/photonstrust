import math

import pytest

from photonstrust.qkd import compute_point


def _plob_bound_bits_per_channel_use(eta: float) -> float:
    # PLOB repeaterless secret-key capacity bound for a pure-loss channel.
    # Reference: Pirandola et al. (2017), DOI: 10.1038/ncomms15043
    eta = float(eta)
    if not math.isfinite(eta) or eta <= 0.0:
        return 0.0
    if eta >= 1.0:
        return float("inf")
    return -math.log2(1.0 - eta)


@pytest.mark.parametrize("distance_km", [0.0, 10.0, 50.0, 100.0, 200.0])
def test_qkd_key_rate_does_not_exceed_plob_bound(distance_km: float) -> None:
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
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
    }

    result = compute_point(scenario, distance_km=distance_km)

    eta_channel = 10 ** (-float(result.loss_db) / 10.0)
    plob_bps = _plob_bound_bits_per_channel_use(eta_channel) * (scenario["source"]["rep_rate_mhz"] * 1e6)

    assert math.isfinite(result.key_rate_bps)
    assert result.key_rate_bps >= 0.0
    assert result.key_rate_bps <= plob_bps * 1.01
