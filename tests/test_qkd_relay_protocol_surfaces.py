import math

import pytest

from photonstrust.channels.coexistence import compute_raman_counts_cps
from photonstrust.qkd import compute_point
from photonstrust.qkd_protocols.common import fiber_segment_transmittance, relay_split_distances_km


def _base_scenario() -> dict:
    return {
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
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16, "misalignment_prob": 0.0},
    }


@pytest.mark.parametrize("distance_km", [0.0, 25.0, 100.0])
def test_mdi_qkd_surface_runs_and_is_finite(distance_km: float) -> None:
    scenario = _base_scenario()
    scenario["protocol"] = {
        "name": "MDI_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.4,
        "nu": 0.1,
        "omega": 0.0,
    }

    res = compute_point(scenario, distance_km=distance_km)

    assert math.isfinite(res.key_rate_bps)
    assert res.key_rate_bps >= 0.0
    assert math.isfinite(res.entanglement_rate_hz)
    assert res.entanglement_rate_hz >= 0.0
    assert 0.0 <= res.qber_total <= 0.5
    # MDI-QKD surface should not use direct-link multiphoton bookkeeping.
    assert res.q_multi == 0.0


def test_amdi_qkd_surface_exposes_pairing_gain_and_diagnostics() -> None:
    base_proto = {
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.3,
        "nu": 0.08,
        "omega": 0.0,
    }
    scenario_mdi = _base_scenario()
    scenario_mdi["protocol"] = {"name": "MDI_QKD", **base_proto}
    mdi = compute_point(scenario_mdi, distance_km=120.0)

    scenario_amdi = _base_scenario()
    scenario_amdi["protocol"] = {
        "name": "AMDI_QKD",
        **base_proto,
        "pairing_window_bins": 4096,
        "pairing_efficiency": 0.8,
        "pairing_error_prob": 0.0,
    }
    amdi = compute_point(scenario_amdi, distance_km=120.0)
    diag = amdi.protocol_diagnostics

    assert amdi.protocol_name == "amdi_qkd"
    assert math.isfinite(amdi.key_rate_bps)
    assert amdi.key_rate_bps >= 0.0
    assert amdi.entanglement_rate_hz >= mdi.entanglement_rate_hz
    assert amdi.key_rate_bps >= mdi.key_rate_bps
    assert isinstance(diag, dict)
    assert float(diag["pairing_gain"]) >= 1.0
    assert int(diag["pairing_window_bins"]) == 4096
    assert float(diag["pairing_efficiency"]) == pytest.approx(0.8)
    assert float(diag["pairing_error_prob"]) == pytest.approx(0.0)


def test_pm_tf_qkd_surfaces_dispatch_and_match() -> None:
    scenario = _base_scenario()
    base_proto = {
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.5,
        "phase_slices": 16,
    }

    scenario["protocol"] = {"name": "PM_QKD", **base_proto}
    pm = compute_point(scenario, distance_km=50.0)

    scenario["protocol"] = {"name": "TF_QKD", **base_proto}
    tf = compute_point(scenario, distance_km=50.0)

    assert math.isfinite(pm.key_rate_bps)
    assert pm.key_rate_bps >= 0.0
    assert math.isfinite(tf.key_rate_bps)
    assert tf.key_rate_bps >= 0.0
    assert pm.q_multi == 0.0
    assert tf.q_multi == 0.0

    # TF surface is currently an alias of the PM model.
    assert pm.key_rate_bps == pytest.approx(tf.key_rate_bps, rel=0.0, abs=0.0)
    assert pm.qber_total == pytest.approx(tf.qber_total, rel=0.0, abs=0.0)


def test_pm_tf_qkd_expose_sqrt_loss_diagnostics() -> None:
    scenario = _base_scenario()
    scenario["protocol"] = {
        "name": "TF_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.5,
        "phase_slices": 16,
    }

    result = compute_point(scenario, distance_km=80.0)
    diag = result.protocol_diagnostics
    assert isinstance(diag, dict)

    eta_channel_geom = float(diag["eta_channel_geometric_mean"])
    eta_expected_sqrt = float(diag["eta_expected_sqrt_total_loss"])
    eta_effective = float(diag["eta_effective_with_detector"])
    eta_detector = float(diag["eta_detector_window"])
    ratio = float(diag["sqrt_loss_consistency_ratio"])

    assert eta_channel_geom == pytest.approx(eta_expected_sqrt, rel=1e-12, abs=1e-15)
    assert ratio == pytest.approx(1.0, rel=1e-12, abs=1e-12)
    assert eta_effective == pytest.approx(eta_channel_geom * eta_detector, rel=1e-12, abs=1e-15)


def test_relay_protocols_key_rate_decreases_with_distance() -> None:
    scenario_mdi = _base_scenario()
    scenario_mdi["protocol"] = {
        "name": "MDI_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.4,
        "nu": 0.1,
        "omega": 0.0,
    }
    r10 = compute_point(scenario_mdi, distance_km=10.0).key_rate_bps
    r200 = compute_point(scenario_mdi, distance_km=200.0).key_rate_bps
    assert r10 >= r200

    scenario_pm = _base_scenario()
    scenario_pm["protocol"] = {
        "name": "PM_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.5,
        "phase_slices": 16,
    }
    r10 = compute_point(scenario_pm, distance_km=10.0).key_rate_bps
    r200 = compute_point(scenario_pm, distance_km=200.0).key_rate_bps
    assert r10 >= r200


@pytest.mark.parametrize("proto_name", ["MDI_QKD", "PM_QKD"])
def test_relay_protocol_loss_matches_segment_product(proto_name: str) -> None:
    scenario = _base_scenario()
    scenario["protocol"] = {
        "name": proto_name,
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.35,
        "mu": 0.5,
        **({"nu": 0.1, "omega": 0.0} if proto_name == "MDI_QKD" else {"phase_slices": 16}),
    }

    distance_km = 120.0
    result = compute_point(scenario, distance_km=distance_km)

    da_km, db_km = relay_split_distances_km(distance_km, scenario["protocol"]["relay_fraction"])
    alpha = float(scenario["channel"]["fiber_loss_db_per_km"])
    connector_loss_db = float(scenario["channel"]["connector_loss_db"])
    ta = fiber_segment_transmittance(da_km, alpha, connector_loss_db)
    tb = fiber_segment_transmittance(db_km, alpha, connector_loss_db)
    expected_loss_db = -10.0 * math.log10(max(1e-300, ta * tb))

    assert result.loss_db == pytest.approx(expected_loss_db)


def test_mdi_relay_noise_budget_backwards_compatible() -> None:
    scenario = _base_scenario()
    scenario["channel"]["background_counts_cps"] = 30.0
    scenario["channel"]["coexistence"] = {
        "enabled": True,
        "classical_launch_power_dbm": 0.0,
        "classical_channel_count": 1,
        "direction": "co",
        "filter_bandwidth_nm": 0.2,
        "raman_coeff_cps_per_km_per_mw_per_nm": 1200.0,
        "raman_spectral_factor": 1.0,
    }
    scenario["protocol"] = {
        "name": "MDI_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.4,
        "mu": 0.4,
        "nu": 0.1,
        "omega": 0.0,
    }

    distance_km = 60.0
    result = compute_point(scenario, distance_km=distance_km)

    da_km, db_km = relay_split_distances_km(distance_km, scenario["protocol"]["relay_fraction"])
    alpha = float(scenario["channel"]["fiber_loss_db_per_km"])
    coexistence_cfg = scenario["channel"]["coexistence"]
    expected_raman = compute_raman_counts_cps(da_km, coexistence_cfg, fiber_loss_db_per_km=alpha) + compute_raman_counts_cps(
        db_km, coexistence_cfg, fiber_loss_db_per_km=alpha
    )
    # Channel background is an aggregate config term and should not be doubled
    # by relay segmenting.
    expected_background = (
        float(scenario["detector"].get("background_counts_cps", 0.0) or 0.0)
        + float(scenario["channel"].get("background_counts_cps", 0.0) or 0.0)
    )

    assert result.raman_counts_cps == pytest.approx(expected_raman)
    assert result.background_counts_cps == pytest.approx(expected_background)


def test_unknown_protocol_name_raises() -> None:
    scenario = _base_scenario()
    scenario["protocol"]["name"] = "UNKNOWN_PROTO"
    with pytest.raises(ValueError):
        compute_point(scenario, distance_km=10.0)
