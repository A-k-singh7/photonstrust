"""Tests for enhanced finite-key composable security models."""

from __future__ import annotations

import math

import pytest

from photonstrust.qkd_protocols.finite_key_composable import (
    de_finetti_coherent_correction,
    source_imperfection_penalty,
)


# ---- de Finetti correction tests -------------------------------------------

def test_de_finetti_polynomial_overhead():
    """eps_coherent = (n+1)^3 * eps_collective."""
    n = 1000
    eps_coll = 1e-10
    eps_coh = de_finetti_coherent_correction(n_signals=n, epsilon_collective=eps_coll)
    expected = (n + 1) ** 3 * eps_coll
    assert eps_coh == pytest.approx(expected, rel=1e-6)


def test_de_finetti_increases_with_n():
    """Larger n -> larger coherent epsilon (more overhead)."""
    eps1 = de_finetti_coherent_correction(n_signals=100, epsilon_collective=1e-10)
    eps2 = de_finetti_coherent_correction(n_signals=10000, epsilon_collective=1e-10)
    assert eps2 > eps1


def test_de_finetti_scales_with_epsilon():
    eps1 = de_finetti_coherent_correction(n_signals=1000, epsilon_collective=1e-10)
    eps2 = de_finetti_coherent_correction(n_signals=1000, epsilon_collective=1e-8)
    assert eps2 / eps1 == pytest.approx(100.0, rel=1e-4)


def test_de_finetti_small_n():
    """Small n should still work."""
    eps = de_finetti_coherent_correction(n_signals=1, epsilon_collective=1e-10)
    assert eps == pytest.approx(8 * 1e-10, rel=1e-6)  # (1+1)^3 = 8


# ---- Source imperfection penalty tests -------------------------------------

def test_source_no_flaw():
    """Zero flaw parameter -> no penalty."""
    r = source_imperfection_penalty(
        key_rate_ideal=0.5, source_flaw_parameter=0.0, n_signals=1000,
    )
    assert r == pytest.approx(0.5, rel=1e-6)


def test_source_flaw_reduces_rate():
    """Positive flaw should reduce rate."""
    r_ideal = 0.5
    r = source_imperfection_penalty(
        key_rate_ideal=r_ideal, source_flaw_parameter=0.01, n_signals=1000,
    )
    assert r < r_ideal
    assert r > 0


def test_source_flaw_vanishes_large_n():
    """For large n, penalty -> 0."""
    r = source_imperfection_penalty(
        key_rate_ideal=0.5, source_flaw_parameter=0.01, n_signals=10**12,
    )
    assert r == pytest.approx(0.5, abs=1e-4)


def test_source_flaw_kills_rate_small_n():
    """For very small n and large flaw, rate -> 0."""
    r = source_imperfection_penalty(
        key_rate_ideal=0.1, source_flaw_parameter=0.5, n_signals=10,
    )
    assert r == 0.0


def test_source_flaw_formula():
    """r = r_ideal - 2*delta/sqrt(n)."""
    r_ideal = 0.5
    delta = 0.01
    n = 10000
    expected = r_ideal - 2 * delta / math.sqrt(n)
    r = source_imperfection_penalty(
        key_rate_ideal=r_ideal, source_flaw_parameter=delta, n_signals=n,
    )
    assert r == pytest.approx(expected, rel=1e-6)
