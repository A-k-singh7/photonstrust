"""Tests for device-independent QKD protocol."""

from __future__ import annotations

import math

import pytest

from photonstrust.qkd_protocols.di_qkd import (
    chsh_value,
    compute_point_di_qkd,
    detection_loophole_threshold,
    di_qkd_finite_key_rate,
    di_qkd_key_rate,
)


# ---- CHSH value tests -----------------------------------------------------

def test_chsh_perfect_state():
    """Perfect visibility + efficiency -> 2*sqrt(2)."""
    S = chsh_value(1.0, 1.0)
    assert S == pytest.approx(2 * math.sqrt(2), rel=1e-6)


def test_chsh_below_classical_with_loss():
    """Low efficiency drops S below classical bound."""
    S = chsh_value(1.0, 0.5)
    assert S < 2.0


def test_chsh_zero_visibility():
    S = chsh_value(0.0, 1.0)
    assert S == pytest.approx(0.0, abs=1e-6)


# ---- Detection loophole tests ---------------------------------------------

def test_loophole_threshold():
    """Threshold should be 2/(1+sqrt(2)) ~ 82.84%."""
    threshold = detection_loophole_threshold()
    assert threshold == pytest.approx(0.8284, abs=0.001)


# ---- Key rate tests --------------------------------------------------------

def test_key_rate_no_violation():
    """S <= 2 -> no key."""
    r = di_qkd_key_rate(2.0, 0.05)
    assert r == 0.0


def test_key_rate_max_violation():
    """S = 2*sqrt(2), Q = 0 -> r = 1 bit/pair."""
    r = di_qkd_key_rate(2 * math.sqrt(2), 0.0)
    assert r == pytest.approx(1.0, abs=0.01)


def test_key_rate_positive_with_violation():
    """CHSH violation with moderate QBER should give positive rate."""
    r = di_qkd_key_rate(2.6, 0.05)
    assert r > 0


def test_key_rate_decreases_with_qber():
    r_low = di_qkd_key_rate(2.7, 0.01)
    r_high = di_qkd_key_rate(2.7, 0.10)
    assert r_low > r_high


def test_key_rate_increases_with_S():
    r_low = di_qkd_key_rate(2.2, 0.05)
    r_high = di_qkd_key_rate(2.7, 0.05)
    assert r_high > r_low


# ---- Finite key rate tests -------------------------------------------------

def test_finite_key_penalty():
    """Finite-key rate should be less than asymptotic."""
    r_asymp = di_qkd_key_rate(2.7, 0.05)
    r_finite = di_qkd_finite_key_rate(2.7, 0.05, n_rounds=10**6)
    assert r_finite < r_asymp
    assert r_finite >= 0


def test_finite_key_converges():
    """Large n should approach asymptotic rate."""
    r_asymp = di_qkd_key_rate(2.7, 0.05)
    r_large_n = di_qkd_finite_key_rate(2.7, 0.05, n_rounds=10**12)
    assert abs(r_large_n - r_asymp) < 0.01


# ---- Full protocol tests ---------------------------------------------------

def test_compute_point_short_distance():
    """Short distance with high-efficiency detectors."""
    scenario = {
        "protocol": {"name": "di_qkd", "visibility": 0.99},
        "source": {"rep_rate_mhz": 1.0},
        "detector": {"pde": 0.90, "dark_counts_cps": 1.0},
        "channel": {"fiber_loss_db_per_km": 0.2},
    }
    result = compute_point_di_qkd(scenario, 1.0)
    assert result.key_rate_bps > 0
    assert result.protocol_name == "di_qkd"
    assert result.protocol_diagnostics["chsh_S"] > 2.0


def test_compute_point_long_distance_zero():
    """At long distance, CHSH violation lost -> zero key."""
    scenario = {
        "protocol": {"name": "di_qkd", "visibility": 0.99},
        "source": {"rep_rate_mhz": 1.0},
        "detector": {"pde": 0.90, "dark_counts_cps": 1.0},
        "channel": {"fiber_loss_db_per_km": 0.2},
    }
    result = compute_point_di_qkd(scenario, 100.0)
    # At 100km: 20dB loss, eta ~ 0.01, sqrt(eta)*0.9 ~ 0.09
    # S = 2*sqrt(2)*0.99*0.09^2 ~ 0.023 << 2
    assert result.key_rate_bps == 0.0


def test_compute_point_diagnostics():
    scenario = {
        "protocol": {"name": "di_qkd"},
        "source": {"rep_rate_mhz": 1.0},
        "detector": {"pde": 0.90},
        "channel": {},
    }
    result = compute_point_di_qkd(scenario, 0.0)
    diag = result.protocol_diagnostics
    assert "chsh_S" in diag
    assert "eta_per_side" in diag
    assert "detection_loophole_closed" in diag


def test_chsh_threshold_zero_rate():
    """S exactly 2 should give zero key rate."""
    r = di_qkd_key_rate(2.0, 0.0)
    assert r == 0.0


def test_high_qber_zero_rate():
    """Very high QBER with marginal violation -> zero rate."""
    r = di_qkd_key_rate(2.1, 0.3)
    assert r == 0.0
