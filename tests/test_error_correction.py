"""Tests for LDPC and Cascade error correction."""

from __future__ import annotations

import numpy as np
import pytest

from photonstrust.pipeline.error_correction import (
    build_ldpc_parity_check,
    cascade_error_correction,
    ldpc_error_correction,
    belief_propagation_decode,
)


def _make_noisy_pair(n: int, qber: float, seed: int = 0):
    """Create Alice/Bob bit strings with controlled QBER."""
    rng = np.random.default_rng(seed)
    alice = rng.integers(0, 2, size=n, dtype=np.int8)
    bob = alice.copy()
    n_errors = max(1, int(n * qber))
    error_positions = rng.choice(n, size=n_errors, replace=False)
    bob[error_positions] ^= 1
    actual_qber = float(np.mean(alice != bob))
    return alice, bob, actual_qber


# ---- LDPC parity-check matrix tests ----------------------------------------

def test_ldpc_parity_check_dimensions():
    n, rate = 100, 0.5
    H = build_ldpc_parity_check(n, rate)
    m = H.shape[0]
    assert H.shape[1] == n
    assert m == int(round(n * (1.0 - rate)))


def test_ldpc_parity_check_binary():
    H = build_ldpc_parity_check(50, 0.5, seed=1)
    assert set(np.unique(H)).issubset({0, 1})


def test_ldpc_parity_check_columns_nonzero():
    H = build_ldpc_parity_check(80, 0.5, seed=2)
    for col in range(H.shape[1]):
        assert H[:, col].sum() >= 1


def test_ldpc_invalid_params():
    with pytest.raises(ValueError):
        build_ldpc_parity_check(0, 0.5)
    with pytest.raises(ValueError):
        build_ldpc_parity_check(100, 0.0)
    with pytest.raises(ValueError):
        build_ldpc_parity_check(100, 1.0)


# ---- Cascade error correction tests ----------------------------------------

def test_cascade_corrects_errors_low_qber():
    """Cascade should correct all errors at QBER ~3%."""
    alice, bob, qber = _make_noisy_pair(5000, 0.03, seed=10)
    result = cascade_error_correction(alice, bob, qber, seed=10)
    assert result.method == "cascade"
    assert result.success is True
    assert result.corrected_errors > 0
    assert result.output_length == 5000


def test_cascade_no_errors():
    """With no errors, Cascade should succeed trivially."""
    alice = np.zeros(100, dtype=np.int8)
    bob = alice.copy()
    result = cascade_error_correction(alice, bob, 0.01, seed=0)
    assert result.success is True
    assert result.corrected_errors == 0


def test_cascade_reconciliation_efficiency():
    """Cascade efficiency should be reasonable at QBER=5%."""
    alice, bob, qber = _make_noisy_pair(2000, 0.05, seed=20)
    result = cascade_error_correction(alice, bob, qber, seed=20)
    # Cascade is not as efficient as LDPC but should be finite
    assert result.reconciliation_efficiency > 0
    assert result.reconciliation_efficiency < 5.0


def test_cascade_leaked_bits_positive():
    alice, bob, qber = _make_noisy_pair(500, 0.05, seed=30)
    result = cascade_error_correction(alice, bob, qber, seed=30)
    assert result.leaked_bits > 0


def test_cascade_empty_input():
    result = cascade_error_correction(
        np.array([], dtype=np.int8),
        np.array([], dtype=np.int8),
        0.05,
    )
    assert result.success is True
    assert result.output_length == 0


# ---- LDPC error correction tests -------------------------------------------

def test_ldpc_builds_and_runs():
    """LDPC should run without errors."""
    alice, bob, qber = _make_noisy_pair(200, 0.05, seed=40)
    result = ldpc_error_correction(alice, bob, qber, seed=40)
    assert result.method == "ldpc"
    assert result.output_length == 200


def test_ldpc_no_errors():
    """With identical inputs, LDPC should succeed."""
    alice = np.ones(100, dtype=np.int8)
    bob = alice.copy()
    result = ldpc_error_correction(alice, bob, 0.01, seed=0)
    assert result.success is True


def test_ldpc_empty_input():
    result = ldpc_error_correction(
        np.array([], dtype=np.int8),
        np.array([], dtype=np.int8),
        0.05,
    )
    assert result.success is False
    assert result.output_length == 0
