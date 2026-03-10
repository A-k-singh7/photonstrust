"""Orbit provider interface and deterministic trace contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class OrbitProviderRequest:
    """Input contract shared by all orbit providers."""

    altitude_km: float
    elevation_min_deg: float
    dt_s: float
    execution_mode: str = "preview"
    tle_line1: str | None = None
    tle_line2: str | None = None
    satellite_name: str | None = None


@dataclass(frozen=True)
class OrbitTraceSample:
    """Single deterministic orbit trace sample."""

    t_s: float
    elevation_deg: float
    slant_range_km: float


@dataclass(frozen=True)
class OrbitTrace:
    """Deterministic provider output contract for pass geometry."""

    provider_id: str
    provider_version: str
    execution_mode: str
    trusted: bool
    compatibility: str
    samples: tuple[OrbitTraceSample, ...]
    metadata: dict[str, Any]
    untrusted_reasons: tuple[str, ...] = ()

    @property
    def sample_count(self) -> int:
        return int(len(self.samples))

    @property
    def pass_start_s(self) -> float:
        if not self.samples:
            return 0.0
        return float(self.samples[0].t_s)

    @property
    def pass_end_s(self) -> float:
        if not self.samples:
            return 0.0
        return float(self.samples[-1].t_s)

    @property
    def peak_elevation_deg(self) -> float:
        if not self.samples:
            return 0.0
        return float(max(s.elevation_deg for s in self.samples))

    @property
    def peak_slant_range_km(self) -> float:
        if not self.samples:
            return 0.0
        peak_elevation = self.peak_elevation_deg
        at_peak = [s for s in self.samples if s.elevation_deg == peak_elevation]
        if not at_peak:
            return 0.0
        return float(min(s.slant_range_km for s in at_peak))

    def to_dict(self) -> dict[str, Any]:
        """Return stable dict shape for serialization/testing."""

        return {
            "provider_id": str(self.provider_id),
            "provider_version": str(self.provider_version),
            "execution_mode": str(self.execution_mode),
            "trusted": bool(self.trusted),
            "compatibility": str(self.compatibility),
            "metadata": dict(self.metadata),
            "untrusted_reasons": [str(row) for row in self.untrusted_reasons],
            "pass_start_s": float(self.pass_start_s),
            "pass_end_s": float(self.pass_end_s),
            "peak_elevation_deg": float(self.peak_elevation_deg),
            "peak_slant_range_km": float(self.peak_slant_range_km),
            "sample_count": int(self.sample_count),
            "samples": [
                {
                    "t_s": float(s.t_s),
                    "elevation_deg": float(s.elevation_deg),
                    "slant_range_km": float(s.slant_range_km),
                }
                for s in self.samples
            ],
        }


class OrbitProvider(Protocol):
    """Protocol for provider implementations."""

    provider_id: str

    def build_trace(self, request: OrbitProviderRequest) -> OrbitTrace:
        """Build deterministic pass trace for a provider request."""


class OrbitProviderError(RuntimeError):
    """Base class for provider-level errors."""


class OrbitProviderUnavailableError(OrbitProviderError):
    """Raised when provider dependency is unavailable in strict modes."""
