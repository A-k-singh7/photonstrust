"""Parity utilities for comparing orbit provider traces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from photonstrust.orbit.providers.base import OrbitTrace


@dataclass(frozen=True)
class ProviderTraceDelta:
    reference: float
    candidate: float
    delta: float
    abs_delta: float


@dataclass(frozen=True)
class ProviderTraceParity:
    reference_provider: str
    candidate_provider: str
    pass_start_s: ProviderTraceDelta
    pass_end_s: ProviderTraceDelta
    peak_elevation_deg: ProviderTraceDelta
    peak_slant_range_km: ProviderTraceDelta
    sample_count: ProviderTraceDelta

    def to_dict(self) -> dict[str, Any]:
        return {
            "reference_provider": str(self.reference_provider),
            "candidate_provider": str(self.candidate_provider),
            "pass_start_s": _delta_to_dict(self.pass_start_s),
            "pass_end_s": _delta_to_dict(self.pass_end_s),
            "peak_elevation_deg": _delta_to_dict(self.peak_elevation_deg),
            "peak_slant_range_km": _delta_to_dict(self.peak_slant_range_km),
            "sample_count": _delta_to_dict(self.sample_count),
        }


def compare_provider_traces(reference: OrbitTrace, candidate: OrbitTrace) -> ProviderTraceParity:
    """Compare two provider traces and compute deterministic metric deltas."""

    return ProviderTraceParity(
        reference_provider=str(reference.provider_id),
        candidate_provider=str(candidate.provider_id),
        pass_start_s=_delta(reference.pass_start_s, candidate.pass_start_s),
        pass_end_s=_delta(reference.pass_end_s, candidate.pass_end_s),
        peak_elevation_deg=_delta(reference.peak_elevation_deg, candidate.peak_elevation_deg),
        peak_slant_range_km=_delta(reference.peak_slant_range_km, candidate.peak_slant_range_km),
        sample_count=_delta(float(reference.sample_count), float(candidate.sample_count)),
    )


def _delta(reference: float, candidate: float) -> ProviderTraceDelta:
    ref_value = float(reference)
    cand_value = float(candidate)
    signed = cand_value - ref_value
    return ProviderTraceDelta(
        reference=ref_value,
        candidate=cand_value,
        delta=float(signed),
        abs_delta=float(abs(signed)),
    )


def _delta_to_dict(delta: ProviderTraceDelta) -> dict[str, float]:
    return {
        "reference": float(delta.reference),
        "candidate": float(delta.candidate),
        "delta": float(delta.delta),
        "abs_delta": float(delta.abs_delta),
    }
