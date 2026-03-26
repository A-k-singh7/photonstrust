"""QRNG source models simulating different quantum random-number sources."""

from __future__ import annotations

import numpy as np

from photonstrust.qrng.types import QRNGSource


def vacuum_fluctuation_source(
    *,
    homodyne_efficiency: float = 0.95,
    electronic_noise_fraction: float = 0.01,
    sampling_rate_mhz: float = 100,
    adc_bits: int = 12,
    n_samples: int = 10000,
    seed: int = 42,
) -> tuple[QRNGSource, np.ndarray]:
    """Simulate a vacuum-fluctuation QRNG source using homodyne detection."""
    rng = np.random.default_rng(seed)
    # Gaussian quadrature of vacuum state
    sigma = np.sqrt(homodyne_efficiency * (1 + electronic_noise_fraction))
    raw_continuous = rng.normal(0, sigma, n_samples)
    # Discretize to adc_bits, then take LSBs as raw bits
    max_val = 2 ** (adc_bits - 1) - 1
    discretized = np.clip(
        np.round(raw_continuous * max_val / (3 * sigma)), -max_val, max_val
    ).astype(int)
    raw_bits = np.abs(discretized) % 2  # LSB extraction

    source = QRNGSource(
        source_type="vacuum_fluctuation",
        generation_rate_bps=sampling_rate_mhz * 1e6,
        raw_entropy_per_bit=0.0,
        parameters={
            "homodyne_efficiency": homodyne_efficiency,
            "electronic_noise_fraction": electronic_noise_fraction,
            "sampling_rate_mhz": sampling_rate_mhz,
            "adc_bits": adc_bits,
            "n_samples": n_samples,
            "seed": seed,
        },
    )
    return source, raw_bits


def photon_arrival_source(
    *,
    mean_photon_rate_cps: float = 1e6,
    detector_pde: float = 0.3,
    dark_counts_cps: float = 100,
    n_samples: int = 10000,
    seed: int = 42,
) -> tuple[QRNGSource, np.ndarray]:
    """Simulate a photon-arrival-time QRNG source."""
    rng = np.random.default_rng(seed)
    effective_rate = mean_photon_rate_cps * detector_pde + dark_counts_cps
    inter_arrival = rng.exponential(1.0 / effective_rate, n_samples + 1)
    # LSB of integer inter-arrival-time differences
    diffs = np.diff(inter_arrival)
    raw_bits = np.round(diffs * 1e12).astype(int) % 2  # ps resolution, LSB

    source = QRNGSource(
        source_type="photon_arrival",
        generation_rate_bps=effective_rate,
        raw_entropy_per_bit=0.0,
        parameters={
            "mean_photon_rate_cps": mean_photon_rate_cps,
            "detector_pde": detector_pde,
            "dark_counts_cps": dark_counts_cps,
            "n_samples": n_samples,
            "seed": seed,
        },
    )
    return source, raw_bits[:n_samples]


def beam_splitter_source(
    *,
    splitting_ratio: float = 0.5,
    detector_pde: float = 0.3,
    n_pulses: int = 10000,
    seed: int = 42,
) -> tuple[QRNGSource, np.ndarray]:
    """Simulate a beam-splitter QRNG source with single-photon pulses."""
    rng = np.random.default_rng(seed)
    # For each pulse: single photon hits BS, probability splitting_ratio of
    # going to detector 0
    effective_ratio = splitting_ratio * detector_pde / (
        splitting_ratio * detector_pde
        + (1 - splitting_ratio) * detector_pde
        + 1e-30
    )
    raw_bits = (rng.random(n_pulses) > effective_ratio).astype(int)

    source = QRNGSource(
        source_type="beam_splitter",
        generation_rate_bps=float(n_pulses),
        raw_entropy_per_bit=0.0,
        parameters={
            "splitting_ratio": splitting_ratio,
            "detector_pde": detector_pde,
            "n_pulses": n_pulses,
            "seed": seed,
        },
    )
    return source, raw_bits


def di_qrng_source(
    *,
    chsh_violation: float = 2.7,
    detection_efficiency: float = 0.90,
    n_rounds: int = 10000,
    seed: int = 42,
) -> tuple[QRNGSource, np.ndarray]:
    """Simulate a device-independent QRNG source from CHSH violation.

    Certified randomness per round from CHSH violation S:

        H_min >= 1 - log2(1 + sqrt(2 - (S/2)^2))

    For S = 2*sqrt(2) (Tsirelson bound), H_min = 1 bit/round.
    For S = 2 (classical limit), H_min = 0.

    Args:
        chsh_violation: Observed CHSH S value (must be > 2)
        detection_efficiency: Detector efficiency
        n_rounds: Number of measurement rounds
        seed: Random seed

    Returns:
        (QRNGSource, raw_bits) tuple

    Ref: Pironio et al., Nature 464, 1021 (2010)
    """
    import math

    rng = np.random.default_rng(seed)
    S = max(2.0, min(2.0 * math.sqrt(2.0), float(chsh_violation)))

    # Min-entropy per round from CHSH value
    s2 = (S / 2.0) ** 2
    inner = max(0.0, 2.0 - s2)
    h_min = max(0.0, 1.0 - math.log2(1.0 + math.sqrt(inner)))

    # Effective randomness rate
    effective_rate = h_min * detection_efficiency

    # Generate raw bits (simulation: biased by entropy bound)
    # Perfect CHSH violation -> uniform bits
    # Reduced violation -> biased bits
    p1 = 0.5 + 0.5 * (1.0 - 2 ** (-h_min))
    raw_bits = (rng.random(n_rounds) < p1).astype(int)

    source = QRNGSource(
        source_type="di_qrng",
        generation_rate_bps=float(n_rounds) * effective_rate,
        raw_entropy_per_bit=h_min,
        parameters={
            "chsh_violation": S,
            "detection_efficiency": detection_efficiency,
            "n_rounds": n_rounds,
            "min_entropy_per_round": h_min,
            "seed": seed,
        },
    )
    return source, raw_bits
