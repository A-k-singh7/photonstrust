"""Geometry-based deterministic orbit provider."""

from __future__ import annotations

from photonstrust.orbit.geometry import generate_elevation_profile, slant_range_km
from photonstrust.orbit.providers.base import OrbitProviderRequest, OrbitTrace, OrbitTraceSample


class AnalyticOrbitProvider:
    """Deterministic baseline provider using existing geometry helpers."""

    provider_id = "analytic"

    def build_trace(self, request: OrbitProviderRequest) -> OrbitTrace:
        samples_raw = generate_elevation_profile(
            altitude_km=float(request.altitude_km),
            el_min_deg=float(request.elevation_min_deg),
            dt_s=float(request.dt_s),
        )

        samples = []
        for row in samples_raw:
            t_s = float(row.get("t_s", 0.0) or 0.0)
            elevation_deg = float(row.get("elevation_deg", 0.0) or 0.0)
            slant_km = float(row.get("distance_km", slant_range_km(elevation_deg, float(request.altitude_km))) or 0.0)
            samples.append(
                OrbitTraceSample(
                    t_s=t_s,
                    elevation_deg=max(0.0, min(90.0, elevation_deg)),
                    slant_range_km=max(0.0, slant_km),
                )
            )

        samples.sort(key=lambda row: float(row.t_s))
        return OrbitTrace(
            provider_id=self.provider_id,
            provider_version="geometry-v1",
            execution_mode=str(request.execution_mode or "preview"),
            trusted=True,
            compatibility="native",
            samples=tuple(samples),
            metadata={
                "model": "spherical_earth_circular_orbit",
                "altitude_km": float(request.altitude_km),
                "elevation_min_deg": float(request.elevation_min_deg),
                "dt_s": float(request.dt_s),
            },
        )
