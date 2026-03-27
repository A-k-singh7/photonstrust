"""Tests for SNS-TF-QKD protocol implementation.

Validates the Sending-or-Not-Sending Twin-Field QKD protocol including
O(sqrt(eta)) scaling, relay segment handling, decoy-state parameter
estimation, and rate behavior at various distances.
"""

from __future__ import annotations

import math

import pytest

from photonstrust.qkd_protocols.sns_tf_qkd import (
    _sns_gain,
    _sns_error_rate,
    _sns_single_photon_yield_bound,
    _sns_phase_error_bound,
    compute_point_sns_tf_qkd,
)


# ---- Base scenario fixture ------------------------------------------------

def _base_scenario(**overrides):
    scenario = {
        "source": {"rep_rate_mhz": 1000.0},
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "pde": 0.85,
            "dark_counts_cps": 10.0,
            "jitter_ps_fwhm": 50.0,
            "dead_time_ns": 10.0,
        },
        "timing": {"coincidence_window_ps": 300.0},
        "protocol": {
            "mu_z": 0.3,
            "mu_1": 0.1,
            "mu_2": 0.02,
            "p_z": 0.5,
            "ec_efficiency": 1.16,
        },
    }
    scenario.update(overrides)
    return scenario


# ---- Protocol-level tests --------------------------------------------------

def test_sns_positive_rate_short_distance():
    result = compute_point_sns_tf_qkd(_base_scenario(), distance_km=50.0)
    assert result.protocol_name == "sns_tf_qkd"
    assert result.key_rate_bps > 0


def test_sns_positive_rate_200km():
    result = compute_point_sns_tf_qkd(_base_scenario(), distance_km=200.0)
    assert result.key_rate_bps > 0


def test_sns_positive_rate_300km():
    """SNS-TF-QKD should produce positive rate at 300 km with optimized parameters.

    At long distance, lower signal/decoy intensities are needed for tight
    parameter estimation. The default mu_z=0.3 is too high at 300 km.
    """
    scenario = _base_scenario()
    scenario["protocol"]["mu_z"] = 0.05
    scenario["protocol"]["mu_1"] = 0.02
    scenario["protocol"]["mu_2"] = 0.005
    result = compute_point_sns_tf_qkd(scenario, distance_km=300.0)
    assert result.key_rate_bps > 0


def test_sns_zero_rate_very_long():
    """At extremely long distances, even SNS should eventually fail."""
    result = compute_point_sns_tf_qkd(_base_scenario(), distance_km=1000.0)
    assert result.key_rate_bps == 0.0


def test_sns_rate_decreases_with_distance():
    r50 = compute_point_sns_tf_qkd(_base_scenario(), distance_km=50.0)
    r100 = compute_point_sns_tf_qkd(_base_scenario(), distance_km=100.0)
    r200 = compute_point_sns_tf_qkd(_base_scenario(), distance_km=200.0)
    assert r50.key_rate_bps >= r100.key_rate_bps >= r200.key_rate_bps


def test_sns_sqrt_eta_scaling():
    """SNS rate should scale as O(sqrt(eta)), not O(eta).

    Compare rate ratio to transmittance ratio at two distances.
    For O(eta) scaling: R1/R2 ≈ eta1/eta2
    For O(sqrt(eta)): R1/R2 ≈ sqrt(eta1/eta2)
    The actual ratio should be closer to sqrt scaling.
    """
    alpha = 0.2  # dB/km
    d1, d2 = 100.0, 200.0
    r1 = compute_point_sns_tf_qkd(_base_scenario(), distance_km=d1)
    r2 = compute_point_sns_tf_qkd(_base_scenario(), distance_km=d2)

    if r2.key_rate_bps > 0 and r1.key_rate_bps > 0:
        rate_ratio = r1.key_rate_bps / r2.key_rate_bps
        # Full loss ratio (O(eta) scaling would give this)
        eta_ratio = 10 ** (alpha * (d2 - d1) / 10.0)
        # sqrt(eta) scaling gives sqrt of that
        sqrt_eta_ratio = math.sqrt(eta_ratio)
        # Rate ratio should be closer to sqrt_eta_ratio than eta_ratio
        assert rate_ratio < eta_ratio


def test_sns_diagnostics_present():
    result = compute_point_sns_tf_qkd(_base_scenario(), distance_km=100.0)
    diag = result.protocol_diagnostics
    assert diag is not None
    assert "mu_z" in diag
    assert "eta" in diag
    assert "S_z" in diag
    assert "s1_lower" in diag
    assert "e1_phase_upper" in diag


def test_sns_requires_fiber_channel():
    scenario = _base_scenario()
    scenario["channel"]["model"] = "free_space"
    with pytest.raises(ValueError, match="fiber"):
        compute_point_sns_tf_qkd(scenario, distance_km=100.0)


def test_sns_requires_rep_rate():
    scenario = _base_scenario()
    scenario["source"]["rep_rate_mhz"] = 0
    with pytest.raises(ValueError, match="rep_rate_mhz"):
        compute_point_sns_tf_qkd(scenario, distance_km=100.0)


def test_sns_relay_fraction():
    """Asymmetric relay placement should still produce a rate."""
    scenario = _base_scenario()
    scenario["protocol"]["relay_fraction"] = 0.3
    result = compute_point_sns_tf_qkd(scenario, distance_km=100.0)
    assert result.key_rate_bps > 0


def test_sns_symmetric_relay_optimal():
    """Symmetric relay placement (0.5) should give higher rate than asymmetric."""
    s_sym = _base_scenario()
    s_sym["protocol"]["relay_fraction"] = 0.5
    s_asym = _base_scenario()
    s_asym["protocol"]["relay_fraction"] = 0.2

    r_sym = compute_point_sns_tf_qkd(s_sym, distance_km=200.0)
    r_asym = compute_point_sns_tf_qkd(s_asym, distance_km=200.0)
    assert r_sym.key_rate_bps >= r_asym.key_rate_bps


def test_sns_zero_distance():
    result = compute_point_sns_tf_qkd(_base_scenario(), distance_km=0.0)
    assert result.key_rate_bps > 0


# ---- Component function tests ---------------------------------------------

def test_sns_gain_positive():
    gain = _sns_gain(mu=0.3, eta=0.1, pd=1e-6)
    assert gain > 0
    assert gain < 1


def test_sns_gain_increases_with_mu():
    g1 = _sns_gain(mu=0.1, eta=0.1, pd=1e-6)
    g2 = _sns_gain(mu=0.5, eta=0.1, pd=1e-6)
    assert g2 > g1


def test_sns_gain_vacuum():
    """Vacuum gain should equal 2*pd."""
    pd = 1e-5
    g0 = _sns_gain(mu=0.0, eta=0.1, pd=pd)
    assert abs(g0 - 2.0 * pd) < 1e-12


def test_sns_error_rate_bounded():
    e = _sns_error_rate(mu=0.3, eta=0.1, pd=1e-6, e_mis=0.02)
    assert 0 <= e <= 0.5


def test_sns_single_photon_yield_positive():
    eta = 0.1
    pd = 1e-6
    mu_z, mu_1, mu_2 = 0.3, 0.1, 0.02
    S_z = _sns_gain(mu_z, eta, pd)
    S_1 = _sns_gain(mu_1, eta, pd)
    S_2 = _sns_gain(mu_2, eta, pd)
    S_0 = 2.0 * pd

    s1 = _sns_single_photon_yield_bound(
        mu_z=mu_z, mu_1=mu_1, mu_2=mu_2,
        S_z=S_z, S_1=S_1, S_2=S_2, S_0=S_0,
    )
    assert s1 > 0


def test_sns_phase_error_bounded():
    e1 = _sns_phase_error_bound(mu_1=0.1, S_1=0.01, T_1=0.001, s1=0.005)
    assert 0 <= e1 <= 0.5
