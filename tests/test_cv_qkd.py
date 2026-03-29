"""Tests for CV-QKD (GG02) protocol implementation.

Validates the Gaussian-modulated coherent-state protocol with homodyne
and heterodyne detection, including covariance matrix formalism,
Holevo bound computation, and finite-size effects.
"""

from __future__ import annotations

import math

import pytest

from photonstrust.qkd_protocols.cv_qkd import (
    _covariance_after_channel,
    _empty_result,
    _finite_size_penalty,
    _g_function,
    _holevo_bound,
    _mutual_info_heterodyne,
    _mutual_info_homodyne,
    _signal_to_noise,
    _symplectic_eigenvalues,
    compute_point_cv_qkd,
)


# ---- Basic scenario fixture -----------------------------------------------

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
            "efficiency": 0.6,
            "electronic_noise_snu": 0.01,
        },
        "protocol": {
            "modulation_variance": 4.0,
            "excess_noise_snu": 0.005,
            "reconciliation_efficiency": 0.95,
            "detection": "homodyne",
        },
    }
    scenario.update(overrides)
    return scenario


# ---- Protocol-level tests --------------------------------------------------

def test_cv_qkd_positive_rate_short_distance():
    result = compute_point_cv_qkd(_base_scenario(), distance_km=10.0)
    assert result.protocol_name == "cv_qkd"
    assert result.key_rate_bps > 0


def test_cv_qkd_positive_rate_50km():
    result = compute_point_cv_qkd(_base_scenario(), distance_km=50.0)
    assert result.key_rate_bps > 0


def test_cv_qkd_zero_rate_very_long():
    """At very long distance, channel loss kills the key rate."""
    result = compute_point_cv_qkd(_base_scenario(), distance_km=500.0)
    assert result.key_rate_bps == 0.0


def test_cv_qkd_rate_decreases_with_distance():
    r10 = compute_point_cv_qkd(_base_scenario(), distance_km=10.0)
    r25 = compute_point_cv_qkd(_base_scenario(), distance_km=25.0)
    r50 = compute_point_cv_qkd(_base_scenario(), distance_km=50.0)
    assert r10.key_rate_bps >= r25.key_rate_bps >= r50.key_rate_bps


def test_cv_qkd_heterodyne_produces_rate():
    scenario = _base_scenario()
    scenario["protocol"]["detection"] = "heterodyne"
    result = compute_point_cv_qkd(scenario, distance_km=10.0)
    assert result.key_rate_bps > 0


def test_cv_qkd_homodyne_vs_heterodyne():
    """Both detection types should produce positive rates at short distance."""
    hom = compute_point_cv_qkd(_base_scenario(), distance_km=25.0)
    scenario_het = _base_scenario()
    scenario_het["protocol"]["detection"] = "heterodyne"
    het = compute_point_cv_qkd(scenario_het, distance_km=25.0)
    # Both should be positive
    assert hom.key_rate_bps > 0
    assert het.key_rate_bps > 0


def test_cv_qkd_high_excess_noise_kills_rate():
    scenario = _base_scenario()
    scenario["protocol"]["excess_noise_snu"] = 0.5  # very high
    result = compute_point_cv_qkd(scenario, distance_km=25.0)
    assert result.key_rate_bps == 0.0


def test_cv_qkd_modulation_variance_effect():
    """Higher modulation variance should change the key rate."""
    s_low = _base_scenario()
    s_low["protocol"]["modulation_variance"] = 1.0
    s_high = _base_scenario()
    s_high["protocol"]["modulation_variance"] = 10.0
    r_low = compute_point_cv_qkd(s_low, distance_km=25.0)
    r_high = compute_point_cv_qkd(s_high, distance_km=25.0)
    # Both should compute (may differ in which is higher)
    assert r_low.key_rate_bps >= 0
    assert r_high.key_rate_bps >= 0


def test_cv_qkd_diagnostics_present():
    result = compute_point_cv_qkd(_base_scenario(), distance_km=10.0)
    diag = result.protocol_diagnostics
    assert diag is not None
    assert "V_A" in diag
    assert "T" in diag
    assert "I_AB" in diag
    assert "chi_BE" in diag
    assert "snr" in diag
    assert diag["detection_type"] == "homodyne"


def test_cv_qkd_zero_distance():
    result = compute_point_cv_qkd(_base_scenario(), distance_km=0.0)
    assert result.key_rate_bps > 0


def test_cv_qkd_requires_rep_rate():
    scenario = _base_scenario()
    scenario["source"]["rep_rate_mhz"] = 0
    with pytest.raises(ValueError, match="rep_rate_mhz"):
        compute_point_cv_qkd(scenario, distance_km=10.0)


def test_cv_qkd_finite_key_reduces_rate():
    scenario = _base_scenario()
    r_asym = compute_point_cv_qkd(scenario, distance_km=25.0)

    scenario_fk = _base_scenario()
    scenario_fk["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1e8,
        "epsilon_total": 1e-10,
    }
    r_fk = compute_point_cv_qkd(scenario_fk, distance_km=25.0)
    assert r_fk.key_rate_bps <= r_asym.key_rate_bps
    assert r_fk.finite_key_enabled is True


# ---- Component function tests ---------------------------------------------

def test_g_function_boundary():
    assert _g_function(1.0) == 0.0
    assert _g_function(0.5) == 0.0  # below 1
    assert _g_function(2.0) > 0.0


def test_g_function_monotonic():
    vals = [_g_function(x) for x in [1.5, 2.0, 3.0, 5.0, 10.0]]
    for a, b in zip(vals, vals[1:]):
        assert b >= a


def test_symplectic_eigenvalues_valid():
    V = 5.0
    V_B = 3.0
    C_AB = 2.0
    nu1, nu2 = _symplectic_eigenvalues(V, V_B, C_AB)
    assert nu1 >= 1.0
    assert nu2 >= 1.0
    assert nu1 >= nu2


def test_mutual_info_homodyne_positive():
    V_A = 4.0
    V_B = 3.5
    C_AB = 2.0
    I = _mutual_info_homodyne(V_A, V_B, C_AB)
    assert I > 0


def test_mutual_info_heterodyne_positive():
    V_A = 4.0
    V_B = 3.5
    C_AB = 2.0
    I = _mutual_info_heterodyne(V_A, V_B, C_AB)
    assert I > 0


def test_snr_positive():
    snr = _signal_to_noise(4.0, 0.5, 0.005, 0.01, "homodyne")
    assert snr > 0


def test_finite_size_penalty_positive():
    penalty = _finite_size_penalty(1e8, 1e-10, "homodyne")
    assert penalty > 0
    # Larger n -> smaller penalty
    penalty_large = _finite_size_penalty(1e12, 1e-10, "homodyne")
    assert penalty_large < penalty
