"""Tests for QRNG simulation (Feature 14)."""

from __future__ import annotations

import numpy as np
import pytest

from photonstrust.qrng.conditioning import (
    apply_toeplitz_conditioning,
    apply_von_neumann_extraction,
)
from photonstrust.qrng.entropy import (
    assess_randomness_quality,
    estimate_min_entropy,
)
from photonstrust.qrng.simulator import simulate_qrng
from photonstrust.qrng.sources import (
    beam_splitter_source,
    photon_arrival_source,
    vacuum_fluctuation_source,
)
from photonstrust.qrng.types import QRNGResult


# ---------------------------------------------------------------------------
# Source tests
# ---------------------------------------------------------------------------


def test_vacuum_source_binary_output() -> None:
    """Vacuum-fluctuation source must produce a {0, 1} array."""
    _source, raw = vacuum_fluctuation_source(n_samples=500, seed=7)
    unique = set(np.unique(raw))
    assert unique <= {0, 1}, f"Expected binary, got {unique}"
    assert len(raw) == 500


def test_photon_arrival_positive_entropy() -> None:
    """Photon-arrival source must yield min entropy > 0."""
    _source, raw = photon_arrival_source(n_samples=500, seed=7)
    entropy = estimate_min_entropy(raw)
    assert entropy.min_entropy_per_bit > 0.0


def test_beam_splitter_binary_output() -> None:
    """Beam-splitter source must produce a {0, 1} array."""
    _source, raw = beam_splitter_source(n_pulses=500, seed=7)
    unique = set(np.unique(raw))
    assert unique <= {0, 1}, f"Expected binary, got {unique}"
    assert len(raw) == 500


# ---------------------------------------------------------------------------
# Entropy tests
# ---------------------------------------------------------------------------


def test_min_entropy_estimation_binary() -> None:
    """Min entropy of binary data must be in (0, 1]."""
    samples = np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 0] * 50)
    est = estimate_min_entropy(samples)
    assert 0.0 < est.min_entropy_per_bit <= 1.0
    assert est.sample_size == 500


# ---------------------------------------------------------------------------
# Conditioning tests
# ---------------------------------------------------------------------------


def test_toeplitz_compression_reduces_output() -> None:
    """Toeplitz conditioning must output fewer bits than input."""
    raw = np.array([0, 1] * 500)
    result = apply_toeplitz_conditioning(raw)
    assert result.output_bits < result.input_bits
    assert result.method == "toeplitz"


def test_von_neumann_unbiasing() -> None:
    """Von Neumann extraction should produce near 50/50 output even from biased input."""
    rng = np.random.default_rng(42)
    # Biased: 70% ones
    biased = (rng.random(2000) < 0.7).astype(int)
    result = apply_von_neumann_extraction(biased)
    assert result.output_bits > 0
    assert result.output_min_entropy_per_bit == 1.0
    assert result.method == "von_neumann"


# ---------------------------------------------------------------------------
# Quality tests
# ---------------------------------------------------------------------------


def test_quality_assessment_returns_score() -> None:
    """assess_randomness_quality must return quality_score in [0, 1]."""
    rng = np.random.default_rng(99)
    samples = rng.integers(0, 2, size=1000)
    quality = assess_randomness_quality(samples)
    assert 0.0 <= quality["quality_score"] <= 1.0
    assert "frequency_test" in quality
    assert "runs_test" in quality


# ---------------------------------------------------------------------------
# End-to-end tests
# ---------------------------------------------------------------------------


def test_end_to_end_simulation() -> None:
    """simulate_qrng must return a QRNGResult with a valid quality_score."""
    result = simulate_qrng(
        source_type="vacuum_fluctuation",
        n_samples=1000,
    )
    assert isinstance(result, QRNGResult)
    assert 0.0 <= result.quality_score <= 1.0
    assert result.source["source_type"] == "vacuum_fluctuation"


def test_qrng_result_serialization() -> None:
    """QRNGResult.as_dict() must produce a plain dict."""
    result = simulate_qrng(
        source_type="beam_splitter",
        conditioning_method="von_neumann",
        n_samples=500,
    )
    d = result.as_dict()
    assert isinstance(d, dict)
    assert "source" in d
    assert "entropy_estimate" in d
    assert "conditioning" in d
    assert "quality_score" in d
    assert isinstance(d["quality_score"], float)
