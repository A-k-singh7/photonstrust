"""Tests for Phase A satellite realism hardening.

Covers turbulence fading distributions, pointing bias+jitter decomposition,
Hufnagel-Valley Cn2 profiles, orbit pass envelope, and extended background
models.
"""

from __future__ import annotations

import math

from photonstrust.satellite.turbulence import (
    compute_rytov_variance,
    gamma_gamma_fading,
    hufnagel_valley_cn2,
    lognormal_fading,
    select_fading_model,
)
from photonstrust.satellite.pointing import (
    joint_pointing_turbulence_outage,
    pointing_budget,
)
from photonstrust.satellite.orbit import (
    compute_orbit_pass_envelope,
    elevation_profile,
    slant_range_km,
)
from photonstrust.satellite.background import estimate_background_counts_cps


# ---- Lognormal fading tests ------------------------------------------------

def test_lognormal_fading_weak_turbulence():
    result = lognormal_fading(scintillation_index=0.1, seed=42)
    assert result.model == "lognormal"
    assert abs(result.eta_mean - 1.0) < 0.1
    assert result.outage_probability < 0.1


def test_lognormal_fading_zero_scintillation():
    result = lognormal_fading(scintillation_index=0.0, seed=42)
    assert abs(result.eta_mean - 1.0) < 1e-6
    assert result.outage_probability == 0.0


def test_lognormal_fading_outage_increases_with_scintillation():
    r_weak = lognormal_fading(scintillation_index=0.1, seed=42, outage_threshold_eta=0.5)
    r_strong = lognormal_fading(scintillation_index=0.9, seed=42, outage_threshold_eta=0.5)
    assert r_strong.outage_probability >= r_weak.outage_probability


# ---- Gamma-gamma fading tests ----------------------------------------------

def test_gamma_gamma_fading_mean_near_unity():
    result = gamma_gamma_fading(
        scintillation_index=1.5, rytov_variance=2.0, n_samples=8192, seed=42,
    )
    assert result.model == "gamma_gamma"
    assert abs(result.eta_mean - 1.0) < 0.15


def test_gamma_gamma_fading_with_explicit_params():
    result = gamma_gamma_fading(
        scintillation_index=1.0, alpha=4.0, beta=2.0, seed=42,
    )
    assert result.distribution_params["alpha"] == 4.0
    assert result.distribution_params["beta"] == 2.0


def test_gamma_gamma_outage_higher_than_lognormal_for_strong():
    ln = lognormal_fading(scintillation_index=0.5, seed=42, outage_threshold_eta=0.3)
    gg = gamma_gamma_fading(
        scintillation_index=2.0, rytov_variance=3.0, seed=42, outage_threshold_eta=0.3,
    )
    assert gg.outage_probability > ln.outage_probability


# ---- Auto model selection ---------------------------------------------------

def test_select_fading_model_weak_uses_lognormal():
    result = select_fading_model(scintillation_index=0.3, seed=42)
    assert result.model == "lognormal"


def test_select_fading_model_strong_uses_gamma_gamma():
    result = select_fading_model(scintillation_index=1.5, seed=42)
    assert result.model == "gamma_gamma"


# ---- Serialization ----------------------------------------------------------

def test_fading_result_serialization():
    result = lognormal_fading(scintillation_index=0.2, seed=42)
    d = result.as_dict()
    assert isinstance(d, dict)
    assert "eta_mean" in d
    assert "distribution_params" in d
    assert d["model"] == "lognormal"


# ---- Hufnagel-Valley Cn2 tests ---------------------------------------------

def test_hv_cn2_ground_level():
    cn2 = hufnagel_valley_cn2(0.0)
    # At ground level, dominant term is A*exp(0) = A = 1.7e-14
    assert cn2 > 1e-14


def test_hv_cn2_decreases_with_altitude():
    cn2_ground = hufnagel_valley_cn2(100.0)
    cn2_high = hufnagel_valley_cn2(10000.0)
    assert cn2_ground > cn2_high


def test_hv_cn2_tropopause_bump():
    """The tropopause layer (~10km) shows elevated Cn2 from the wind term."""
    cn2_5km = hufnagel_valley_cn2(5000.0)
    cn2_10km = hufnagel_valley_cn2(10000.0, rms_wind_speed_m_s=30.0)
    # Wind-enhanced tropopause can exceed lower altitudes
    assert cn2_10km > 0


# ---- Rytov variance computation --------------------------------------------

def test_rytov_variance_increases_with_zenith():
    rv_zenith = compute_rytov_variance(wavelength_nm=810, zenith_angle_deg=0)
    rv_60 = compute_rytov_variance(wavelength_nm=810, zenith_angle_deg=60)
    assert rv_60.rytov_variance > rv_zenith.rytov_variance


def test_rytov_fried_parameter_positive():
    hv = compute_rytov_variance(wavelength_nm=810, zenith_angle_deg=30)
    assert hv.fried_parameter_m > 0
    assert hv.isoplanatic_angle_urad > 0


def test_rytov_variance_serialization():
    hv = compute_rytov_variance(wavelength_nm=1550, zenith_angle_deg=20)
    d = hv.as_dict()
    assert "rytov_variance" in d
    assert "fried_parameter_m" in d
    assert d["wavelength_nm"] == 1550


# ---- Pointing budget tests -------------------------------------------------

def test_pointing_budget_no_bias():
    result = pointing_budget(bias_urad=0.0, jitter_urad=2.0, beam_divergence_urad=10.0, seed=42)
    assert result.distribution_model == "rayleigh"
    assert result.eta_boresight == 1.0  # No bias -> perfect boresight
    assert 0.0 < result.eta_mean <= 1.0


def test_pointing_budget_with_bias():
    result = pointing_budget(bias_urad=3.0, jitter_urad=2.0, beam_divergence_urad=10.0, seed=42)
    assert result.distribution_model == "rice"
    assert result.eta_boresight < 1.0
    assert result.rice_parameter_k > 0


def test_pointing_bias_degrades_efficiency():
    r_no_bias = pointing_budget(bias_urad=0.0, jitter_urad=2.0, beam_divergence_urad=10.0, seed=42)
    r_with_bias = pointing_budget(bias_urad=5.0, jitter_urad=2.0, beam_divergence_urad=10.0, seed=42)
    assert r_with_bias.eta_mean < r_no_bias.eta_mean


def test_pointing_budget_serialization():
    result = pointing_budget(bias_urad=1.0, jitter_urad=1.5, beam_divergence_urad=8.0, seed=42)
    d = result.as_dict()
    assert isinstance(d, dict)
    assert "bias_urad" in d
    assert "rice_parameter_k" in d


# ---- Joint pointing + turbulence outage ------------------------------------

def test_joint_outage_combines_distributions():
    import numpy as np
    rng = np.random.default_rng(42)
    p_samples = np.clip(rng.normal(0.9, 0.05, 1000), 0, 1)
    t_samples = np.clip(rng.lognormal(-0.05, 0.3, 1000), 0, 2)
    result = joint_pointing_turbulence_outage(
        pointing_samples=p_samples,
        turbulence_samples=t_samples,
        eta_geometric=0.01,
        eta_atmospheric=0.5,
        outage_threshold_eta=1e-6,
    )
    assert "outage_probability" in result
    assert "eta_mean" in result
    assert result["eta_mean"] > 0


# ---- Slant range tests -----------------------------------------------------

def test_slant_range_zenith():
    """At 90 deg elevation (zenith), slant range = orbit altitude."""
    sr = slant_range_km(orbit_altitude_km=500, elevation_deg=90)
    assert abs(sr - 500.0) < 1.0  # Should be ~orbit altitude


def test_slant_range_increases_with_lower_elevation():
    sr_high = slant_range_km(orbit_altitude_km=500, elevation_deg=70)
    sr_low = slant_range_km(orbit_altitude_km=500, elevation_deg=20)
    assert sr_low > sr_high


# ---- Elevation profile tests -----------------------------------------------

def test_elevation_profile_peaks_at_midpoint():
    profile = elevation_profile(pass_duration_s=300, max_elevation_deg=70, time_step_s=10)
    times, elevations = zip(*profile)
    mid_idx = len(elevations) // 2
    # Elevation near midpoint should be close to max
    assert elevations[mid_idx] > 60


def test_elevation_profile_symmetric():
    profile = elevation_profile(pass_duration_s=300, max_elevation_deg=70, time_step_s=10)
    _, elevations = zip(*profile)
    n = len(elevations)
    for i in range(n // 4):
        assert abs(elevations[i] - elevations[n - 1 - i]) < 2.0


# ---- Orbit pass envelope tests --------------------------------------------

def test_orbit_pass_envelope_basic():
    env = compute_orbit_pass_envelope(
        orbit_altitude_km=500,
        max_elevation_deg=70,
        pass_duration_s=300,
        time_step_s=30,
    )
    assert len(env.time_steps_s) > 0
    assert env.total_key_bits >= 0
    assert env.pass_duration_s == 300.0
    assert env.orbit_altitude_km == 500.0


def test_orbit_pass_key_rate_peaks_at_high_elevation():
    env = compute_orbit_pass_envelope(
        orbit_altitude_km=500,
        max_elevation_deg=70,
        pass_duration_s=300,
        time_step_s=10,
    )
    n = len(env.key_rate_bps)
    mid_rate = env.key_rate_bps[n // 2]
    edge_rate = env.key_rate_bps[0]
    assert mid_rate >= edge_rate


def test_orbit_pass_cumulative_monotonic():
    env = compute_orbit_pass_envelope(
        orbit_altitude_km=500,
        max_elevation_deg=60,
        pass_duration_s=200,
        time_step_s=20,
    )
    for i in range(1, len(env.cumulative_key_bits)):
        assert env.cumulative_key_bits[i] >= env.cumulative_key_bits[i - 1]


def test_orbit_pass_serialization():
    env = compute_orbit_pass_envelope(
        orbit_altitude_km=400,
        max_elevation_deg=50,
        pass_duration_s=180,
        time_step_s=60,
    )
    d = env.as_dict()
    assert isinstance(d, dict)
    assert "total_key_bits" in d
    assert "outage_fraction" in d


# ---- Extended background model tests ---------------------------------------

def test_background_twilight():
    common = dict(
        wavelength_nm=810.0,
        fov_urad=100.0,
        rx_aperture_m=0.3,
        filter_bandwidth_nm=1.0,
        detector_efficiency=0.5,
    )
    night = estimate_background_counts_cps(day_night="night", **common)
    twilight = estimate_background_counts_cps(day_night="twilight", **common)
    day = estimate_background_counts_cps(day_night="day", **common)
    # Twilight should be between night and day
    assert night.counts_cps < twilight.counts_cps < day.counts_cps


def test_background_full_moon():
    common = dict(
        wavelength_nm=810.0,
        fov_urad=100.0,
        rx_aperture_m=0.3,
        filter_bandwidth_nm=1.0,
        detector_efficiency=0.5,
    )
    night = estimate_background_counts_cps(day_night="night", **common)
    moon = estimate_background_counts_cps(day_night="full_moon", **common)
    # Full moon should be > new moon night
    assert moon.counts_cps > night.counts_cps
