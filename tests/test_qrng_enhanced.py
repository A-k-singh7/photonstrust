"""Tests for enhanced QRNG sources and entropy estimators."""

from __future__ import annotations

import math

import numpy as np
import pytest

from photonstrust.qrng.entropy import (
    collision_entropy_estimator,
    markov_entropy_estimator,
)
from photonstrust.qrng.sources import di_qrng_source


# ---- DI-QRNG source tests -------------------------------------------------

def test_di_qrng_produces_bits():
    source, bits = di_qrng_source(chsh_violation=2.7, n_rounds=1000)
    assert len(bits) == 1000
    assert set(np.unique(bits)).issubset({0, 1})


def test_di_qrng_source_type():
    source, _ = di_qrng_source()
    assert source.source_type == "di_qrng"


def test_di_qrng_min_entropy_positive():
    source, _ = di_qrng_source(chsh_violation=2.5)
    assert source.raw_entropy_per_bit > 0


def test_di_qrng_max_entropy_at_tsirelson():
    """S = 2*sqrt(2) should give H_min = 1."""
    source, _ = di_qrng_source(chsh_violation=2 * math.sqrt(2))
    assert source.raw_entropy_per_bit == pytest.approx(1.0, abs=0.01)


def test_di_qrng_no_entropy_at_classical():
    """S = 2 gives H_min = 0 (no certified randomness)."""
    source, _ = di_qrng_source(chsh_violation=2.0)
    assert source.raw_entropy_per_bit == pytest.approx(0.0, abs=0.01)


def test_di_qrng_parameters_stored():
    source, _ = di_qrng_source(chsh_violation=2.6, detection_efficiency=0.85)
    assert source.parameters["chsh_violation"] == pytest.approx(2.6, abs=0.01)
    assert source.parameters["detection_efficiency"] == 0.85


# ---- Collision entropy estimator tests -------------------------------------

def test_collision_uniform_binary():
    """Uniform binary should have H_collision near 1."""
    rng = np.random.default_rng(42)
    samples = rng.integers(0, 2, size=10000)
    est = collision_entropy_estimator(samples)
    assert est.min_entropy_per_bit > 0.5
    assert est.estimator == "collision"


def test_collision_biased():
    """Biased source should have lower Shannon entropy than uniform."""
    rng = np.random.default_rng(42)
    # 90% zeros
    samples = (rng.random(10000) > 0.9).astype(int)
    est = collision_entropy_estimator(samples)
    assert est.shannon_entropy_per_bit < 0.6  # H(0.1) ~ 0.469


def test_collision_small_sample():
    est = collision_entropy_estimator(np.array([0, 1]))
    assert est.sample_size == 2


# ---- Markov entropy estimator tests ----------------------------------------

def test_markov_iid_binary():
    """IID uniform binary: Markov entropy ~ 1 bit."""
    rng = np.random.default_rng(42)
    samples = rng.integers(0, 2, size=10000)
    est = markov_entropy_estimator(samples)
    assert est.min_entropy_per_bit > 0.8
    assert est.estimator == "markov"


def test_markov_correlated():
    """Correlated sequence should have lower Markov entropy."""
    # Create correlated sequence: each bit 90% likely to match previous
    rng = np.random.default_rng(42)
    samples = np.zeros(10000, dtype=int)
    samples[0] = 0
    for i in range(1, len(samples)):
        if rng.random() < 0.9:
            samples[i] = samples[i - 1]
        else:
            samples[i] = 1 - samples[i - 1]
    est = markov_entropy_estimator(samples)
    assert est.min_entropy_per_bit < 0.7


def test_markov_small_sample():
    est = markov_entropy_estimator(np.array([0, 1, 0]))
    assert est.sample_size == 3
    assert est.min_entropy_per_bit >= 0


def test_markov_constant_sequence():
    """All-zero sequence should have near-zero entropy."""
    samples = np.zeros(1000, dtype=int)
    est = markov_entropy_estimator(samples)
    assert est.min_entropy_per_bit == pytest.approx(0.0, abs=0.01)
