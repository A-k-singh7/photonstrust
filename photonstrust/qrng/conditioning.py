"""Randomness conditioning / extraction for QRNG raw output."""

from __future__ import annotations

import numpy as np

from photonstrust.qrng.types import ConditioningResult


def apply_toeplitz_conditioning(
    raw_bits: np.ndarray,
    *,
    output_length: int = 0,
    seed: int = 42,
) -> ConditioningResult:
    """Apply Toeplitz-matrix hashing for randomness extraction."""
    n = len(raw_bits)
    if output_length <= 0:
        output_length = n // 2
    output_length = min(output_length, n)

    rng = np.random.default_rng(seed)
    # Build Toeplitz matrix first row
    first_row = rng.integers(0, 2, size=n)
    # Multiply: output[i] = sum(first_row_shifted[j] * raw[j]) mod 2
    output_bits = np.zeros(output_length, dtype=int)
    for i in range(output_length):
        shifted = np.roll(first_row, i)[:n]
        output_bits[i] = np.sum(shifted * raw_bits[:n]) % 2

    compression = output_length / max(n, 1)
    return ConditioningResult(
        method="toeplitz",
        input_bits=n,
        output_bits=output_length,
        compression_ratio=compression,
        output_min_entropy_per_bit=min(
            1.0, 1.0 / max(compression, 1e-30) * 0.5
        ),
    )


def apply_von_neumann_extraction(raw_bits: np.ndarray) -> ConditioningResult:
    """Apply von Neumann de-biasing extraction."""
    output = []
    for i in range(0, len(raw_bits) - 1, 2):
        a, b = int(raw_bits[i]), int(raw_bits[i + 1])
        if a != b:
            output.append(a)
    n_out = len(output)
    compression = n_out / max(len(raw_bits), 1)
    return ConditioningResult(
        method="von_neumann",
        input_bits=len(raw_bits),
        output_bits=n_out,
        compression_ratio=compression,
        output_min_entropy_per_bit=1.0 if n_out > 0 else 0.0,
    )
