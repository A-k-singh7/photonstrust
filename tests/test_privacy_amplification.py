"""Tests for privacy amplification (Toeplitz hashing)."""

from __future__ import annotations

import numpy as np
import pytest

from photonstrust.pipeline.privacy_amplification import (
    compute_pa_output_length,
    fft_toeplitz_hash,
    naive_toeplitz_hash,
)


def test_fft_matches_naive():
    """FFT Toeplitz hash should produce identical results to naive."""
    rng = np.random.default_rng(99)
    key = rng.integers(0, 2, size=128, dtype=np.int8)
    m = 64

    out_fft, _ = fft_toeplitz_hash(key, m, seed=42)
    out_naive, _ = naive_toeplitz_hash(key, m, seed=42)

    np.testing.assert_array_equal(out_fft, out_naive)


def test_fft_matches_naive_various_sizes():
    """FFT and naive should match for several input/output sizes."""
    rng = np.random.default_rng(123)
    for n, m in [(64, 32), (100, 50), (256, 100), (200, 10)]:
        key = rng.integers(0, 2, size=n, dtype=np.int8)
        out_fft, _ = fft_toeplitz_hash(key, m, seed=7)
        out_naive, _ = naive_toeplitz_hash(key, m, seed=7)
        np.testing.assert_array_equal(
            out_fft, out_naive,
            err_msg=f"Mismatch for n={n}, m={m}",
        )


def test_output_is_binary():
    key = np.ones(100, dtype=np.int8)
    out, _ = fft_toeplitz_hash(key, 50, seed=0)
    assert set(np.unique(out)).issubset({0, 1})


def test_output_length_correct():
    key = np.zeros(200, dtype=np.int8)
    out, result = fft_toeplitz_hash(key, 80, seed=0)
    assert len(out) == 80
    assert result.output_length == 80
    assert result.input_length == 200


def test_empty_output():
    key = np.zeros(50, dtype=np.int8)
    out, result = fft_toeplitz_hash(key, 0, seed=0)
    assert len(out) == 0
    assert result.output_length == 0


def test_compression_ratio():
    key = np.zeros(100, dtype=np.int8)
    _, result = fft_toeplitz_hash(key, 25, seed=0)
    assert abs(result.compression_ratio - 0.25) < 1e-10


# ---- Output length computation tests ---------------------------------------

def test_pa_output_length_positive_at_low_qber():
    length = compute_pa_output_length(10000, qber=0.03, leaked_bits=500)
    assert length > 0


def test_pa_output_length_zero_at_high_qber():
    length = compute_pa_output_length(1000, qber=0.45, leaked_bits=100)
    assert length == 0


def test_pa_output_length_decreases_with_qber():
    l1 = compute_pa_output_length(10000, qber=0.02, leaked_bits=200)
    l2 = compute_pa_output_length(10000, qber=0.08, leaked_bits=200)
    assert l1 > l2


def test_pa_output_length_decreases_with_leaked():
    l1 = compute_pa_output_length(10000, qber=0.05, leaked_bits=100)
    l2 = compute_pa_output_length(10000, qber=0.05, leaked_bits=1000)
    assert l1 > l2


def test_pa_output_length_zero_input():
    assert compute_pa_output_length(0, qber=0.05, leaked_bits=0) == 0
