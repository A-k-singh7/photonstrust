"""Tests for the full QKD post-processing pipeline."""

from __future__ import annotations

import numpy as np
import pytest

from photonstrust.pipeline.post_processing import run_post_processing_pipeline


def _simulate_bb84_raw(
    n: int, qber: float, sifting: float = 0.5, seed: int = 0,
):
    """Simulate raw BB84 data with given QBER and sifting ratio."""
    rng = np.random.default_rng(seed)

    # Alice's random bits and bases
    alice_raw = rng.integers(0, 2, size=n, dtype=np.int8)
    basis_alice = rng.integers(0, 2, size=n, dtype=np.int8)

    # Bob's bases: match with probability `sifting`
    basis_bob = basis_alice.copy()
    mismatch_mask = rng.random(n) > sifting
    basis_bob[mismatch_mask] = 1 - basis_bob[mismatch_mask]

    # Bob's bits: same as Alice where bases match, with QBER noise
    bob_raw = alice_raw.copy()
    matching = basis_alice == basis_bob
    n_matching = int(matching.sum())
    if n_matching > 0:
        n_errors = max(0, int(n_matching * qber))
        if n_errors > 0:
            match_indices = np.where(matching)[0]
            error_indices = rng.choice(match_indices, size=n_errors, replace=False)
            bob_raw[error_indices] ^= 1

    # Where bases don't match, Bob gets random results
    bob_raw[~matching] = rng.integers(0, 2, size=int((~matching).sum()), dtype=np.int8)

    return alice_raw, bob_raw, basis_alice, basis_bob


def test_pipeline_positive_key_at_low_qber():
    """Pipeline should produce a positive key at QBER ~3%."""
    alice, bob, ba, bb = _simulate_bb84_raw(20000, qber=0.03, seed=42)
    result = run_post_processing_pipeline(
        alice, bob, ba, bb,
        ec_method="cascade",
        seed=42,
    )
    assert result.success is True
    assert result.final_key_length > 0
    assert result.final_key is not None
    assert len(result.final_key) == result.final_key_length
    assert result.abort_reason is None


def test_pipeline_abort_at_high_qber():
    """Pipeline should abort when QBER exceeds threshold."""
    alice, bob, ba, bb = _simulate_bb84_raw(10000, qber=0.15, seed=100)
    result = run_post_processing_pipeline(
        alice, bob, ba, bb,
        qber_threshold=0.11,
        seed=100,
    )
    assert result.success is False
    assert result.final_key_length == 0
    assert "QBER" in result.abort_reason or "threshold" in result.abort_reason


def test_pipeline_sifting_reduces_key():
    """After sifting, key should be approximately half the raw length."""
    n = 10000
    alice, bob, ba, bb = _simulate_bb84_raw(n, qber=0.02, seed=200)
    result = run_post_processing_pipeline(
        alice, bob, ba, bb,
        ec_method="cascade",
        seed=200,
    )
    assert result.sifted_key_length < n
    assert result.sifted_key_length > n * 0.3  # roughly half


def test_pipeline_estimated_qber_reasonable():
    """Estimated QBER should be close to the injected QBER."""
    target_qber = 0.05
    alice, bob, ba, bb = _simulate_bb84_raw(50000, qber=target_qber, seed=300)
    result = run_post_processing_pipeline(
        alice, bob, ba, bb,
        ec_method="cascade",
        seed=300,
    )
    assert abs(result.estimated_qber - target_qber) < 0.02


def test_pipeline_verification_passes():
    """Verification should pass after successful error correction."""
    alice, bob, ba, bb = _simulate_bb84_raw(20000, qber=0.03, seed=400)
    result = run_post_processing_pipeline(
        alice, bob, ba, bb,
        ec_method="cascade",
        seed=400,
    )
    if result.ec_result.success:
        assert result.verification_passed is True


def test_pipeline_final_key_is_binary():
    """Final key should contain only 0s and 1s."""
    alice, bob, ba, bb = _simulate_bb84_raw(20000, qber=0.03, seed=500)
    result = run_post_processing_pipeline(
        alice, bob, ba, bb,
        ec_method="cascade",
        seed=500,
    )
    if result.final_key is not None:
        assert set(np.unique(result.final_key)).issubset({0, 1})


def test_pipeline_pe_fraction_affects_key():
    """Higher PE fraction should leave fewer key bits."""
    alice, bob, ba, bb = _simulate_bb84_raw(20000, qber=0.03, seed=600)
    r1 = run_post_processing_pipeline(
        alice, bob, ba, bb,
        pe_fraction=0.05,
        ec_method="cascade",
        seed=600,
    )
    r2 = run_post_processing_pipeline(
        alice, bob, ba, bb,
        pe_fraction=0.3,
        ec_method="cascade",
        seed=600,
    )
    if r1.success and r2.success:
        assert r1.final_key_length >= r2.final_key_length


def test_pipeline_too_few_bits():
    """Pipeline should abort gracefully with very few bits."""
    alice = np.array([0, 1, 0], dtype=np.int8)
    bob = np.array([0, 1, 0], dtype=np.int8)
    ba = np.array([0, 0, 0], dtype=np.int8)
    bb = np.array([0, 0, 0], dtype=np.int8)
    result = run_post_processing_pipeline(alice, bob, ba, bb, seed=0)
    # With only 3 bits, pipeline should handle gracefully
    assert isinstance(result.success, bool)
