"""End-to-end QRNG simulation orchestrator."""

from __future__ import annotations

from photonstrust.qrng.conditioning import (
    apply_toeplitz_conditioning,
    apply_von_neumann_extraction,
)
from photonstrust.qrng.entropy import assess_randomness_quality, estimate_min_entropy
from photonstrust.qrng.sources import (
    beam_splitter_source,
    photon_arrival_source,
    vacuum_fluctuation_source,
)
from photonstrust.qrng.types import QRNGResult

_VACUUM_PARAMS = frozenset({
    "homodyne_efficiency",
    "electronic_noise_fraction",
    "sampling_rate_mhz",
    "adc_bits",
    "seed",
})

_PHOTON_PARAMS = frozenset({
    "mean_photon_rate_cps",
    "detector_pde",
    "dark_counts_cps",
    "seed",
})

_BEAM_PARAMS = frozenset({
    "splitting_ratio",
    "detector_pde",
    "seed",
})


def simulate_qrng(
    *,
    source_type: str = "vacuum_fluctuation",
    source_params: dict | None = None,
    conditioning_method: str = "toeplitz",
    n_samples: int = 10000,
) -> QRNGResult:
    """Run a complete QRNG simulation pipeline."""
    params = source_params or {}

    # 1. Generate raw samples
    if source_type == "vacuum_fluctuation":
        filtered = {k: v for k, v in params.items() if k in _VACUUM_PARAMS}
        source, raw = vacuum_fluctuation_source(n_samples=n_samples, **filtered)
    elif source_type == "photon_arrival":
        filtered = {k: v for k, v in params.items() if k in _PHOTON_PARAMS}
        source, raw = photon_arrival_source(n_samples=n_samples, **filtered)
    elif source_type == "beam_splitter":
        filtered = {k: v for k, v in params.items() if k in _BEAM_PARAMS}
        source, raw = beam_splitter_source(n_pulses=n_samples, **filtered)
    else:
        raise ValueError(f"Unknown source_type: {source_type!r}")

    # 2. Estimate entropy
    entropy = estimate_min_entropy(raw)

    # 3. Conditioning
    if conditioning_method == "toeplitz":
        conditioning = apply_toeplitz_conditioning(raw)
    elif conditioning_method == "von_neumann":
        conditioning = apply_von_neumann_extraction(raw)
    else:
        raise ValueError(f"Unknown conditioning_method: {conditioning_method!r}")

    # 4. Quality assessment
    quality = assess_randomness_quality(raw)

    # 5. Output rate
    output_rate = source.generation_rate_bps * conditioning.compression_ratio

    return QRNGResult(
        source=source.as_dict(),
        entropy_estimate=entropy.as_dict(),
        conditioning=conditioning.as_dict(),
        output_rate_bps=output_rate,
        quality_score=quality["quality_score"],
        passes_nist_tests=quality["frequency_test"] and quality["runs_test"],
        diagnostics=quality,
    )
