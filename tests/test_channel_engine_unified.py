from __future__ import annotations

import pytest

from photonstrust.channels.engine import compute_channel_diagnostics
from photonstrust.qkd import compute_sweep


def test_fiber_channel_monotonic_and_physical_bounds() -> None:
    cfg = {
        "model": "fiber",
        "fiber_loss_db_per_km": 0.2,
        "connector_loss_db": 1.5,
        "polarization_coherence_length_km": 80.0,
    }

    near = compute_channel_diagnostics(distance_km=10.0, wavelength_nm=1550.0, channel_cfg=cfg)
    far = compute_channel_diagnostics(distance_km=80.0, wavelength_nm=1550.0, channel_cfg=cfg)

    assert 0.0 <= near["eta_channel"] <= 1.0
    assert 0.0 <= far["eta_channel"] <= 1.0
    assert far["eta_channel"] < near["eta_channel"]
    assert far["total_loss_db"] > near["total_loss_db"]


def test_fiber_polarization_coherence_does_not_change_loss_path() -> None:
    base_cfg = {
        "model": "fiber",
        "fiber_loss_db_per_km": 0.2,
        "connector_loss_db": 1.5,
    }
    pol_cfg = {
        **base_cfg,
        "polarization_coherence_length_km": 10.0,
    }

    base = compute_channel_diagnostics(distance_km=50.0, wavelength_nm=1550.0, channel_cfg=base_cfg)
    pol = compute_channel_diagnostics(distance_km=50.0, wavelength_nm=1550.0, channel_cfg=pol_cfg)

    assert pol["total_loss_db"] == pytest.approx(base["total_loss_db"], rel=0.0, abs=0.0)
    assert pol["eta_channel"] == pytest.approx(base["eta_channel"], rel=0.0, abs=0.0)
    assert pol["decomposition"]["eta_polarization"] < 1.0


def test_satellite_decomposition_composes_physically() -> None:
    cfg = {
        "model": "satellite",
        "satellite_uplink_fraction": 0.4,
        "connector_loss_db": 1.2,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 10.0,
        "pointing_jitter_urad": 1.5,
        "atmospheric_extinction_db_per_km": 0.02,
        "turbulence_scintillation_index": 0.12,
        "uplink_elevation_deg": 30.0,
        "downlink_elevation_deg": 60.0,
    }

    diag = compute_channel_diagnostics(distance_km=1000.0, wavelength_nm=1550.0, channel_cfg=cfg)
    decomp = diag["decomposition"]

    expected_eta = decomp["eta_uplink"] * decomp["eta_downlink"] * decomp["eta_connector"]
    assert diag["eta_channel"] == pytest.approx(expected_eta, rel=0.0, abs=1e-15)
    assert 0.0 <= diag["eta_channel"] <= 1.0
    assert diag["total_loss_db"] >= 0.0


def test_uncertainty_contains_channel_interval_summaries() -> None:
    scenario = {
        "scenario_id": "uq_channel_interval",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [200.0, 400.0],
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
            "background_counts_cps": 100.0,
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
        "uncertainty": {
            "seed": 7,
            "pointing_jitter_urad": 0.20,
            "atmospheric_extinction_db_per_km": 0.25,
        },
    }

    sweep = compute_sweep(scenario, include_uncertainty=True)
    uq = sweep["uncertainty"]

    for distance in scenario["distances_km"]:
        row = uq[distance]
        assert row["low"] <= row["high"]
        ch = row["channel_interval"]
        assert 0.0 <= ch["eta_channel"]["low"] <= ch["eta_channel"]["high"] <= 1.0
        assert 0.0 <= ch["total_loss_db"]["low"] <= ch["total_loss_db"]["high"]


def test_free_space_diag_includes_atmosphere_and_outage_fields() -> None:
    cfg = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 30.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 12.0,
        "pointing_jitter_urad": 1.5,
        "pointing_model": "gaussian",
        "pointing_sample_count": 128,
        "pointing_seed": 3,
        "turbulence_scintillation_index": 0.12,
        "turbulence_model": "lognormal",
        "turbulence_sample_count": 128,
        "turbulence_seed": 4,
        "atmospheric_extinction_db_per_km": 0.02,
        "atmosphere_effective_thickness_km": 20.0,
        "outage_eta_threshold": 1.0e-6,
    }
    diag = compute_channel_diagnostics(distance_km=800.0, wavelength_nm=1550.0, channel_cfg=cfg)

    decomp = diag["decomposition"]
    assert decomp["atmosphere_path_km"] > 0.0
    assert decomp["atmosphere_effective_thickness_km"] == pytest.approx(20.0)
    assert 0.0 <= diag["outage_probability"] <= 1.0
