"""Tests for adaptive optics models."""

from __future__ import annotations

import math

import pytest

from photonstrust.satellite.adaptive_optics import (
    NOLL_ALPHA_COEFFICIENTS,
    compute_ao_correction,
    greenwood_frequency,
    noll_residual_variance,
    smf_coupling_with_ao,
    strehl_ratio,
)


# ---- Noll residual variance tests -----------------------------------------

def test_noll_no_correction():
    """No correction (J=0) gives full turbulence variance."""
    sigma2 = noll_residual_variance(1.0, 0.1, J=0)
    expected = 1.0299 * (1.0 / 0.1) ** (5.0 / 3.0)
    assert sigma2 == pytest.approx(expected, rel=1e-4)


def test_noll_tip_tilt_removal():
    """Removing tip-tilt (J=3) significantly reduces variance."""
    sigma2_full = noll_residual_variance(0.5, 0.1, J=0)
    sigma2_tt = noll_residual_variance(0.5, 0.1, J=3)
    assert sigma2_tt < sigma2_full
    # Tip-tilt is ~87% of total variance
    assert sigma2_tt < 0.2 * sigma2_full


def test_noll_more_modes_less_variance():
    """More corrected modes -> less residual variance."""
    sigma_3 = noll_residual_variance(1.0, 0.1, J=3)
    sigma_10 = noll_residual_variance(1.0, 0.1, J=10)
    sigma_20 = noll_residual_variance(1.0, 0.1, J=20)
    assert sigma_3 > sigma_10 > sigma_20


def test_noll_scales_with_d_over_r0():
    """Variance scales as (D/r0)^(5/3)."""
    s1 = noll_residual_variance(0.5, 0.1, J=3)
    s2 = noll_residual_variance(1.0, 0.1, J=3)
    ratio = s2 / s1
    expected_ratio = (1.0 / 0.5) ** (5.0 / 3.0)
    assert ratio == pytest.approx(expected_ratio, rel=1e-4)


# ---- Strehl ratio tests ---------------------------------------------------

def test_strehl_zero_variance():
    """Perfect wavefront gives Strehl = 1."""
    assert strehl_ratio(0.0) == pytest.approx(1.0, rel=1e-6)


def test_strehl_one_radian():
    sr = strehl_ratio(1.0)
    assert sr == pytest.approx(math.exp(-1.0), rel=1e-6)


def test_strehl_decreases_with_variance():
    assert strehl_ratio(0.5) > strehl_ratio(1.0) > strehl_ratio(2.0)


# ---- SMF coupling tests ---------------------------------------------------

def test_smf_perfect_strehl():
    eta = smf_coupling_with_ao(1.0, eta_0=0.81)
    assert eta == pytest.approx(0.81, rel=1e-4)


def test_smf_zero_strehl():
    eta = smf_coupling_with_ao(0.0)
    assert eta == pytest.approx(0.0, abs=1e-10)


def test_smf_proportional_to_strehl():
    eta1 = smf_coupling_with_ao(0.5)
    eta2 = smf_coupling_with_ao(0.25)
    assert eta1 / eta2 == pytest.approx(2.0, rel=1e-4)


# ---- Greenwood frequency tests --------------------------------------------

def test_greenwood_formula():
    f_G = greenwood_frequency(10.0, 0.1)
    expected = 0.4265 * 10.0 / 0.1
    assert f_G == pytest.approx(expected, rel=1e-4)


def test_greenwood_increases_with_wind():
    f1 = greenwood_frequency(5.0, 0.1)
    f2 = greenwood_frequency(20.0, 0.1)
    assert f2 > f1


def test_greenwood_increases_with_worse_seeing():
    f1 = greenwood_frequency(10.0, 0.2)  # good seeing
    f2 = greenwood_frequency(10.0, 0.05)  # poor seeing
    assert f2 > f1


# ---- Full AO correction tests ---------------------------------------------

def test_ao_correction_improves_coupling():
    """AO correction should improve SMF coupling over uncorrected."""
    r_no_ao = compute_ao_correction(1.0, 0.1, J=0)
    r_ao = compute_ao_correction(1.0, 0.1, J=20)
    assert r_ao.smf_coupling > r_no_ao.smf_coupling


def test_ao_correction_bandwidth_error():
    """Insufficient bandwidth adds temporal error."""
    r_fast = compute_ao_correction(0.5, 0.1, J=10, ao_bandwidth_hz=5000.0)
    r_slow = compute_ao_correction(0.5, 0.1, J=10, ao_bandwidth_hz=10.0)
    assert r_fast.total_strehl > r_slow.total_strehl
    assert r_slow.bandwidth_error_rad2 > r_fast.bandwidth_error_rad2


def test_ao_good_seeing_high_strehl():
    """Good seeing (large r0) should give high Strehl even with few modes."""
    r = compute_ao_correction(0.3, 0.3, J=10)  # D/r0 = 1
    assert r.strehl_ratio > 0.5


def test_ao_diagnostics():
    r = compute_ao_correction(1.0, 0.1, J=20)
    assert "D_over_r0" in r.diagnostics
    assert r.diagnostics["D_over_r0"] == pytest.approx(10.0, rel=0.01)
    assert r.greenwood_freq_hz > 0
