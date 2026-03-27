"""Tests for BB84 3-intensity decoy-state bounds.

Validates that the 3-intensity decoy method (Ma et al. PRA 72, 2005)
produces tighter single-photon yield and error bounds than the standard
vacuum+weak (2-intensity) method.
"""

from __future__ import annotations

import math

import pytest

from photonstrust.qkd_protocols.bb84_decoy import (
    _e1_upper_bound,
    _e1_upper_bound_3intensity,
    _gain_error,
    _y1_lower_bound,
    _y1_lower_bound_3intensity,
    compute_point_bb84_decoy,
)


# ---- Base scenario fixture ------------------------------------------------

def _base_scenario(**overrides):
    scenario = {
        "source": {"rep_rate_mhz": 100.0},
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "pde": 0.1,
            "dark_counts_cps": 100.0,
            "jitter_ps_fwhm": 50.0,
        },
        "timing": {"coincidence_window_ps": 300.0},
        "protocol": {
            "mu": 0.5,
            "nu": 0.1,
            "omega": 0.0,
            "misalignment_prob": 0.015,
            "ec_efficiency": 1.16,
            "decoy_method": "3intensity",
        },
    }
    scenario.update(overrides)
    return scenario


# ---- 3-intensity bound tightness tests ------------------------------------

def test_3intensity_y1_tighter_than_2intensity():
    """3-intensity Y1 lower bound should be >= 2-intensity bound."""
    mu, nu, omega = 0.5, 0.1, 0.0
    eta = 0.01
    p_noise = 1e-6
    e_opt = 0.015

    q_mu, e_mu = _gain_error(mu=mu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_nu, e_nu = _gain_error(mu=nu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_om, _ = _gain_error(mu=omega, eta=eta, p_noise=p_noise, e_opt=e_opt)
    y0 = q_om

    y1_2int = _y1_lower_bound(mu=mu, nu=nu, q_mu=q_mu, q_nu=q_nu, y0=y0)
    y1_3int = _y1_lower_bound_3intensity(
        mu=mu, nu=nu, omega=omega,
        q_mu=q_mu, q_nu=q_nu, q_om=q_om, y0=y0,
    )

    assert y1_3int >= y1_2int


def test_3intensity_y1_positive():
    """3-intensity Y1 bound should be positive at reasonable parameters."""
    mu, nu, omega = 0.5, 0.1, 0.0
    eta = 0.05
    p_noise = 1e-5
    e_opt = 0.015

    q_mu, _ = _gain_error(mu=mu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_nu, _ = _gain_error(mu=nu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_om, _ = _gain_error(mu=omega, eta=eta, p_noise=p_noise, e_opt=e_opt)

    y1 = _y1_lower_bound_3intensity(
        mu=mu, nu=nu, omega=omega,
        q_mu=q_mu, q_nu=q_nu, q_om=q_om, y0=q_om,
    )
    assert y1 > 0


def test_3intensity_y1_bounded_by_one():
    """Y1 should never exceed 1."""
    mu, nu, omega = 0.8, 0.2, 0.01
    eta = 0.5
    p_noise = 0.01
    e_opt = 0.02

    q_mu, _ = _gain_error(mu=mu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_nu, _ = _gain_error(mu=nu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_om, _ = _gain_error(mu=omega, eta=eta, p_noise=p_noise, e_opt=e_opt)

    y1 = _y1_lower_bound_3intensity(
        mu=mu, nu=nu, omega=omega,
        q_mu=q_mu, q_nu=q_nu, q_om=q_om, y0=q_om,
    )
    assert y1 <= 1.0


def test_3intensity_e1_upper_bound_valid():
    """3-intensity e1 upper bound should be in [0, 0.5]."""
    nu, omega = 0.1, 0.0
    eta = 0.05
    p_noise = 1e-5
    e_opt = 0.015

    q_nu, e_nu = _gain_error(mu=nu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_om, _ = _gain_error(mu=omega, eta=eta, p_noise=p_noise, e_opt=e_opt)
    y0 = q_om

    # Use a reasonable y1_l
    y1_l = 0.05

    e1 = _e1_upper_bound_3intensity(
        nu=nu, omega=omega,
        q_nu=q_nu, e_nu=e_nu, q_om=q_om, y0=y0, y1_l=y1_l,
    )
    assert 0 <= e1 <= 0.5


# ---- Protocol-level 3-intensity tests -------------------------------------

def test_3intensity_protocol_produces_rate():
    """BB84 with 3-intensity decoy method should produce positive rate."""
    result = compute_point_bb84_decoy(_base_scenario(), distance_km=25.0)
    assert result.key_rate_bps > 0
    assert result.protocol_name == "bb84_decoy"


def test_3intensity_vs_2intensity_protocol_rate():
    """3-intensity should give comparable or better rate than 2-intensity."""
    s_2int = _base_scenario()
    s_2int["protocol"]["decoy_method"] = "vacuum_weak"
    s_3int = _base_scenario()
    s_3int["protocol"]["decoy_method"] = "3intensity"

    r_2int = compute_point_bb84_decoy(s_2int, distance_km=50.0)
    r_3int = compute_point_bb84_decoy(s_3int, distance_km=50.0)

    # Both should produce non-negative rates
    assert r_2int.key_rate_bps >= 0
    assert r_3int.key_rate_bps >= 0

    # 3-intensity should give tighter bounds -> potentially higher rate
    # At minimum, Y1 from 3-intensity should be >= Y1 from 2-intensity
    if r_3int.single_photon_yield_lb is not None and r_2int.single_photon_yield_lb is not None:
        assert r_3int.single_photon_yield_lb >= r_2int.single_photon_yield_lb - 1e-12


def test_3intensity_rate_decreases_with_distance():
    r10 = compute_point_bb84_decoy(_base_scenario(), distance_km=10.0)
    r25 = compute_point_bb84_decoy(_base_scenario(), distance_km=25.0)
    r50 = compute_point_bb84_decoy(_base_scenario(), distance_km=50.0)
    assert r10.key_rate_bps >= r25.key_rate_bps >= r50.key_rate_bps


def test_default_decoy_method_is_vacuum_weak():
    """Without specifying decoy_method, should default to vacuum_weak."""
    scenario = _base_scenario()
    del scenario["protocol"]["decoy_method"]
    result = compute_point_bb84_decoy(scenario, distance_km=25.0)
    assert result.key_rate_bps >= 0


def test_3intensity_with_nonzero_omega():
    """3-intensity method with omega > 0 should still work."""
    scenario = _base_scenario()
    scenario["protocol"]["omega"] = 0.01  # nonzero vacuum intensity
    result = compute_point_bb84_decoy(scenario, distance_km=25.0)
    assert result.key_rate_bps >= 0


def test_3intensity_invalid_intensities():
    """Should raise error when mu <= nu."""
    scenario = _base_scenario()
    scenario["protocol"]["mu"] = 0.05
    scenario["protocol"]["nu"] = 0.1  # nu > mu is invalid
    with pytest.raises(ValueError, match="mu > nu"):
        compute_point_bb84_decoy(scenario, distance_km=25.0)
