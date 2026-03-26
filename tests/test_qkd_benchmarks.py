"""Tests for QKD benchmark and fundamental bounds."""

from __future__ import annotations

import math

import pytest

from photonstrust.benchmarks.qkd_benchmarks import (
    direct_transmission_bound,
    fiber_transmittance,
    plob_bound,
    tgw_bound,
)


# ---- PLOB bound tests -----------------------------------------------------

def test_plob_zero_loss():
    """eta = 1 -> C = infinity (log2 diverges) but we clamp."""
    # At eta very close to 1
    c = plob_bound(0.999)
    assert c > 5.0


def test_plob_zero_transmittance():
    c = plob_bound(0.0)
    assert c == 0.0


def test_plob_formula():
    """C = -log2(1-eta)."""
    eta = 0.5
    expected = -math.log2(1.0 - eta)
    assert plob_bound(eta) == pytest.approx(expected, rel=1e-6)


def test_plob_monotonic():
    """Higher transmittance -> higher capacity."""
    assert plob_bound(0.1) < plob_bound(0.5) < plob_bound(0.9)


def test_plob_low_eta_approx():
    """For small eta, PLOB ~ eta / ln(2)."""
    eta = 0.001
    c = plob_bound(eta)
    approx = eta / math.log(2)
    assert abs(c - approx) / approx < 0.01


# ---- TGW bound tests ------------------------------------------------------

def test_tgw_zero():
    assert tgw_bound(0.0) == 0.0


def test_tgw_formula():
    eta = 0.3
    expected = math.log2((1 + eta) / (1 - eta))
    assert tgw_bound(eta) == pytest.approx(expected, rel=1e-6)


def test_tgw_greater_than_plob():
    """TGW >= PLOB for all eta."""
    for eta in [0.01, 0.1, 0.3, 0.5, 0.7, 0.9]:
        assert tgw_bound(eta) >= plob_bound(eta) - 1e-10


# ---- Direct transmission bound tests --------------------------------------

def test_direct_bound():
    assert direct_transmission_bound(0.5) == pytest.approx(0.5, rel=1e-6)
    assert direct_transmission_bound(0.0) == 0.0
    assert direct_transmission_bound(1.0) == 1.0


# ---- Fiber transmittance tests --------------------------------------------

def test_fiber_zero_distance():
    assert fiber_transmittance(0.0) == pytest.approx(1.0, rel=1e-6)


def test_fiber_formula():
    """eta = 10^(-0.2 * 50 / 10) = 10^(-1) = 0.1."""
    assert fiber_transmittance(50.0, 0.2) == pytest.approx(0.1, rel=1e-6)


def test_fiber_decreases_with_distance():
    assert fiber_transmittance(10.0) > fiber_transmittance(100.0)
