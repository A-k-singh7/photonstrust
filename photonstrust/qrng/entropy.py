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


# ---------------------------------------------------------------------------
# NIST SP 800-90B entropy estimators
# ---------------------------------------------------------------------------

def collision_entropy_estimator(samples: np.ndarray) -> EntropyEstimate:
    """Collision entropy estimator from NIST SP 800-90B, Section 6.3.2.

    Estimates entropy from the mean number of samples between collisions
    (repeated values). Lower collision distance -> lower entropy.

    The collision entropy is:

        H_collision = -log2(sum p_i^2)

    Estimated from average collision distance:

        H ~ log2(mean_collision_distance)

    Args:
        samples: Array of discrete samples

    Returns:
        EntropyEstimate with collision-based min-entropy bound

    Ref: NIST SP 800-90B, Section 6.3.2
    """
    n = len(samples)
    if n < 3:
        return EntropyEstimate(
            min_entropy_per_bit=0.0,
            shannon_entropy_per_bit=0.0,
            sample_size=n,
            estimator="collision",
            confidence=0.0,
        )

    # Compute collision distances
    collision_distances: list[int] = []
    i = 0
    while i < n - 1:
        # Find next collision (repeated value)
        seen: set[int] = {int(samples[i])}
        j = i + 1
        while j < n:
            val = int(samples[j])
            if val in seen:
                collision_distances.append(j - i)
                break
            seen.add(val)
            j += 1
        i = j if j < n else i + 1

    if not collision_distances:
        # No collisions found — max entropy
        h_collision = math.log2(n)
    else:
        mean_dist = sum(collision_distances) / len(collision_distances)
        # H ~ log2(mean_collision_distance)
        h_collision = math.log2(max(2.0, mean_dist))

    # Also compute Shannon for comparison
    unique, counts = np.unique(samples, return_counts=True)
    probs = counts / n
    shannon = -sum(float(p) * math.log2(max(float(p), 1e-30)) for p in probs)

    return EntropyEstimate(
        min_entropy_per_bit=min(h_collision, 1.0),
        shannon_entropy_per_bit=shannon,
        sample_size=n,
        estimator="collision",
        confidence=0.95,
    )


def markov_entropy_estimator(samples: np.ndarray) -> EntropyEstimate:
    """Markov entropy estimator from NIST SP 800-90B, Section 6.3.3.

    Models the source as a first-order Markov chain and computes
    the per-symbol entropy rate:

        H_Markov = -sum_i pi_i * sum_j P(j|i) * log2(P(j|i))

    where pi is the stationary distribution and P(j|i) are transition
    probabilities.

    Args:
        samples: Array of discrete samples (binary: 0/1)

    Returns:
        EntropyEstimate with Markov-based entropy

    Ref: NIST SP 800-90B, Section 6.3.3
    """
    n = len(samples)
    if n < 3:
        return EntropyEstimate(
            min_entropy_per_bit=0.0,
            shannon_entropy_per_bit=0.0,
            sample_size=n,
            estimator="markov",
            confidence=0.0,
        )

    # Count transitions for binary data
    unique_vals = np.unique(samples)
    n_states = len(unique_vals)
    val_to_idx = {int(v): i for i, v in enumerate(unique_vals)}

    # Transition count matrix
    trans = np.zeros((n_states, n_states), dtype=float)
    for k in range(n - 1):
        i = val_to_idx[int(samples[k])]
        j = val_to_idx[int(samples[k + 1])]
        trans[i, j] += 1

    # Transition probabilities
    row_sums = trans.sum(axis=1)
    P = np.zeros_like(trans)
    for i in range(n_states):
        if row_sums[i] > 0:
            P[i] = trans[i] / row_sums[i]

    # Stationary distribution (from empirical frequencies)
    counts = np.array([float(np.sum(samples == v)) for v in unique_vals])
    pi = counts / n

    # Markov entropy rate
    h_markov = 0.0
    for i in range(n_states):
        for j in range(n_states):
            if P[i, j] > 0:
                h_markov -= pi[i] * P[i, j] * math.log2(P[i, j])

    # Shannon for comparison
    probs = counts / n
    shannon = -sum(float(p) * math.log2(max(float(p), 1e-30)) for p in probs)

    return EntropyEstimate(
        min_entropy_per_bit=min(h_markov, 1.0),
        shannon_entropy_per_bit=shannon,
        sample_size=n,
        estimator="markov",
        confidence=0.95,
    )
