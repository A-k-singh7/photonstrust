"""Orbit provider registry and selection helpers."""

from __future__ import annotations

from photonstrust.orbit.providers.analytic_provider import AnalyticOrbitProvider
from photonstrust.orbit.providers.base import (
    OrbitProvider,
    OrbitProviderError,
    OrbitProviderRequest,
    OrbitProviderUnavailableError,
    OrbitTrace,
    OrbitTraceSample,
)
from photonstrust.orbit.providers.orekit_provider import OrekitReferenceProvider
from photonstrust.orbit.providers.poliastro_provider import PoliastroOrbitProvider
from photonstrust.orbit.providers.skyfield_provider import SkyfieldOrbitProvider


_PROVIDERS: dict[str, type[OrbitProvider]] = {
    "analytic": AnalyticOrbitProvider,
    "skyfield": SkyfieldOrbitProvider,
    "poliastro": PoliastroOrbitProvider,
    "orekit": OrekitReferenceProvider,
}


def get_orbit_provider(provider_id: str) -> OrbitProvider:
    key = str(provider_id or "analytic").strip().lower() or "analytic"
    cls = _PROVIDERS.get(key)
    if cls is None:
        known = ", ".join(sorted(_PROVIDERS.keys()))
        raise OrbitProviderError(f"unknown orbit provider {key!r}; known providers: {known}")
    return cls()


def build_orbit_trace(provider_id: str, request: OrbitProviderRequest) -> OrbitTrace:
    provider = get_orbit_provider(provider_id)
    return provider.build_trace(request)


__all__ = [
    "OrbitProvider",
    "OrbitProviderError",
    "OrbitProviderRequest",
    "OrbitProviderUnavailableError",
    "OrbitTrace",
    "OrbitTraceSample",
    "AnalyticOrbitProvider",
    "SkyfieldOrbitProvider",
    "PoliastroOrbitProvider",
    "OrekitReferenceProvider",
    "get_orbit_provider",
    "build_orbit_trace",
]
