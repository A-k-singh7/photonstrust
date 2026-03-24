"""Entropy estimation and randomness quality assessment for QRNG."""

from __future__ import annotations

import math

import numpy as np

from photonstrust.qrng.types import EntropyEstimate


def estimate_min_entropy(
    samples: np.ndarray, *, method: str = "most_common_value"
) -> EntropyEstimate:
    """Estimate min-entropy using the most-common-value method (NIST SP 800-90B)."""
    unique, counts = np.unique(samples, return_counts=True)
    p_max = counts.max() / len(samples)
    min_entropy = -math.log2(max(p_max, 1e-30))
    # Shannon entropy for comparison
    probs = counts / len(samples)
    shannon = -sum(p * math.log2(max(p, 1e-30)) for p in probs)
    return EntropyEstimate(
        min_entropy_per_bit=min_entropy,
        shannon_entropy_per_bit=shannon,
        sample_size=len(samples),
        estimator=method,
        confidence=0.95,
    )


def estimate_shannon_entropy(samples: np.ndarray) -> float:
    """Compute Shannon entropy of the sample distribution."""
    unique, counts = np.unique(samples, return_counts=True)
    probs = counts / len(samples)
    return -sum(p * math.log2(max(p, 1e-30)) for p in probs)


def assess_randomness_quality(samples: np.ndarray) -> dict:
    """Run lightweight randomness quality tests on binary samples."""
    n = len(samples)
    # Frequency test: count 1s, expect ~n/2
    ones = int(np.sum(samples == 1))
    freq_stat = abs(ones - n / 2) / math.sqrt(n / 4) if n > 0 else 0.0
    freq_pass = freq_stat < 3.0  # ~99.7% confidence

    # Runs test: count transitions
    transitions = int(np.sum(np.diff(samples) != 0)) if n > 1 else 0
    expected_runs = 1 + 2 * ones * (n - ones) / max(n, 1)
    runs_pass = abs(transitions - expected_runs) < 3 * math.sqrt(
        max(expected_runs, 1)
    )

    # Composite quality score
    quality_score = 0.5 * float(freq_pass) + 0.5 * float(runs_pass)
    return {
        "frequency_test": bool(freq_pass),
        "runs_test": bool(runs_pass),
        "quality_score": quality_score,
        "frequency_statistic": freq_stat,
    }
