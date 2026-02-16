import math

import pytest

from photonstrust.channels.free_space import atmospheric_transmission
from photonstrust.channels.free_space import total_free_space_efficiency


def test_free_space_efficiency_decreases_with_distance():
    cfg = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 45.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 12.0,
        "pointing_jitter_urad": 1.0,
        "atmospheric_extinction_db_per_km": 0.02,
        "turbulence_scintillation_index": 0.10,
        "background_counts_cps": 100.0,
    }
    near = total_free_space_efficiency(distance_km=50.0, wavelength_nm=1550.0, channel_cfg=cfg)
    far = total_free_space_efficiency(distance_km=600.0, wavelength_nm=1550.0, channel_cfg=cfg)

    assert 0.0 <= near["eta_channel"] <= 1.0
    assert 0.0 <= far["eta_channel"] <= 1.0
    assert far["eta_channel"] < near["eta_channel"]
    assert far["total_loss_db"] > near["total_loss_db"]


def test_pointing_jitter_reduces_efficiency():
    base = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 45.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 10.0,
        "atmospheric_extinction_db_per_km": 0.02,
        "turbulence_scintillation_index": 0.10,
        "background_counts_cps": 100.0,
    }
    low = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "pointing_jitter_urad": 0.5},
    )
    high = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "pointing_jitter_urad": 6.0},
    )

    assert high["eta_pointing"] < low["eta_pointing"]
    assert high["eta_channel"] < low["eta_channel"]


def test_airmass_low_elevation_is_finite_and_reasonable():
    with pytest.warns(UserWarning):
        eta, airmass = atmospheric_transmission(
            distance_km=10.0,
            elevation_deg=1.0,
            extinction_db_per_km=0.02,
        )

    assert 0.0 < eta <= 1.0
    assert math.isfinite(airmass)
    assert 1.0 < airmass < 40.0


def test_atmospheric_path_effective_thickness_is_range_bounded():
    near_eta, near_airmass = atmospheric_transmission(
        distance_km=100.0,
        elevation_deg=30.0,
        extinction_db_per_km=0.02,
        atmosphere_effective_thickness_km=20.0,
        path_model="effective_thickness",
    )
    far_eta, far_airmass = atmospheric_transmission(
        distance_km=1500.0,
        elevation_deg=30.0,
        extinction_db_per_km=0.02,
        atmosphere_effective_thickness_km=20.0,
        path_model="effective_thickness",
    )

    assert near_airmass == pytest.approx(far_airmass, rel=0.0, abs=1e-12)
    assert near_eta == pytest.approx(far_eta, rel=0.0, abs=1e-12)


def test_atmospheric_legacy_slant_range_still_scales_with_distance():
    near_eta, _ = atmospheric_transmission(
        distance_km=100.0,
        elevation_deg=30.0,
        extinction_db_per_km=0.02,
        path_model="legacy_slant_range",
    )
    far_eta, _ = atmospheric_transmission(
        distance_km=1500.0,
        elevation_deg=30.0,
        extinction_db_per_km=0.02,
        path_model="legacy_slant_range",
    )

    assert far_eta < near_eta


def test_turbulence_distribution_monotonic_outage_with_scintillation():
    base = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 45.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 12.0,
        "pointing_jitter_urad": 1.0,
        "pointing_model": "deterministic",
        "atmospheric_extinction_db_per_km": 0.02,
        "background_counts_cps": 100.0,
        "turbulence_model": "lognormal",
        "turbulence_sample_count": 512,
        "turbulence_seed": 7,
        "turbulence_outage_threshold_eta": 0.15,
        "outage_eta_threshold": 1.0e-6,
    }
    low = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "turbulence_scintillation_index": 0.05},
    )
    high = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "turbulence_scintillation_index": 0.40},
    )

    assert high["turbulence_diagnostics"]["outage_probability"] >= low["turbulence_diagnostics"]["outage_probability"]


def test_pointing_distribution_reproducible_and_jitter_sensitive():
    base = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 45.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 12.0,
        "atmospheric_extinction_db_per_km": 0.02,
        "turbulence_scintillation_index": 0.10,
        "turbulence_model": "deterministic",
        "background_counts_cps": 100.0,
        "pointing_model": "gaussian",
        "pointing_sample_count": 512,
        "pointing_seed": 11,
        "pointing_outage_threshold_eta": 0.15,
        "outage_eta_threshold": 1.0e-6,
    }
    low = total_free_space_efficiency(
        distance_km=600.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "pointing_jitter_urad": 0.5},
    )
    high = total_free_space_efficiency(
        distance_km=600.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "pointing_jitter_urad": 3.0},
    )
    repeat = total_free_space_efficiency(
        distance_km=600.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "pointing_jitter_urad": 3.0},
    )

    assert high["pointing_diagnostics"]["outage_probability"] >= low["pointing_diagnostics"]["outage_probability"]
    assert repeat["pointing_diagnostics"]["outage_probability"] == pytest.approx(
        high["pointing_diagnostics"]["outage_probability"], rel=0.0, abs=0.0
    )


def test_radiance_proxy_background_day_exceeds_night() -> None:
    base = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 45.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 12.0,
        "pointing_jitter_urad": 1.0,
        "atmospheric_extinction_db_per_km": 0.02,
        "turbulence_scintillation_index": 0.10,
        "background_model": "radiance_proxy",
        "background_fov_urad": 120.0,
        "background_filter_bandwidth_nm": 1.0,
        "background_detector_gate_ns": 1.0,
        "background_site_light_pollution": 0.2,
    }
    night = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "background_day_night": "night"},
    )
    day = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "background_day_night": "day"},
    )

    assert day["background_counts_cps"] > night["background_counts_cps"]
    assert day["background_uncertainty_cps"]["sigma"] >= night["background_uncertainty_cps"]["sigma"]


def test_radiance_proxy_background_scales_with_optics() -> None:
    base = {
        "model": "free_space",
        "connector_loss_db": 1.0,
        "elevation_deg": 45.0,
        "tx_aperture_m": 0.12,
        "rx_aperture_m": 0.30,
        "beam_divergence_urad": 12.0,
        "pointing_jitter_urad": 1.0,
        "atmospheric_extinction_db_per_km": 0.02,
        "turbulence_scintillation_index": 0.10,
        "background_model": "radiance_proxy",
        "background_day_night": "day",
        "background_detector_gate_ns": 1.0,
        "background_site_light_pollution": 0.2,
    }
    low = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "background_fov_urad": 80.0, "background_filter_bandwidth_nm": 0.5},
    )
    high = total_free_space_efficiency(
        distance_km=500.0,
        wavelength_nm=1550.0,
        channel_cfg={**base, "background_fov_urad": 160.0, "background_filter_bandwidth_nm": 1.5},
    )

    assert high["background_counts_cps"] > low["background_counts_cps"]
