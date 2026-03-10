"""Skyfield-backed orbit provider with fail-closed behavior."""

from __future__ import annotations

import hashlib
from typing import Any

from photonstrust.orbit.geometry import generate_elevation_profile
from photonstrust.orbit.providers.analytic_provider import AnalyticOrbitProvider
from photonstrust.orbit.providers.base import OrbitProviderRequest, OrbitProviderUnavailableError, OrbitTrace, OrbitTraceSample


class SkyfieldOrbitProvider:
    """Skyfield provider with preview-only deterministic fallback."""

    provider_id = "skyfield"

    def build_trace(self, request: OrbitProviderRequest) -> OrbitTrace:
        mode = str(request.execution_mode or "preview").strip().lower() or "preview"
        skyfield = _import_skyfield()
        has_tle = bool(str(request.tle_line1 or "").strip() and str(request.tle_line2 or "").strip())

        if skyfield is None or not has_tle:
            reason = "skyfield_dependency_unavailable" if skyfield is None else "skyfield_tle_required"
            if mode != "preview":
                raise OrbitProviderUnavailableError(
                    f"skyfield provider unavailable in {mode!r} mode: {reason}"
                )
            return _preview_fallback_trace(request=request, reason=reason)

        derived = _derive_altitude_from_tle(
            skyfield_api=skyfield,
            line1=str(request.tle_line1),
            line2=str(request.tle_line2),
            satellite_name=str(request.satellite_name or "satellite"),
            fallback_altitude_km=float(request.altitude_km),
        )
        altitude_km = float(derived["altitude_km"])
        samples_raw = generate_elevation_profile(
            altitude_km=altitude_km,
            el_min_deg=float(request.elevation_min_deg),
            dt_s=float(request.dt_s),
        )
        samples = tuple(
            OrbitTraceSample(
                t_s=float(row.get("t_s", 0.0) or 0.0),
                elevation_deg=float(row.get("elevation_deg", 0.0) or 0.0),
                slant_range_km=float(row.get("distance_km", 0.0) or 0.0),
            )
            for row in samples_raw
        )

        return OrbitTrace(
            provider_id=self.provider_id,
            provider_version=str(derived["provider_version"]),
            execution_mode=mode,
            trusted=True,
            compatibility="native",
            samples=tuple(sorted(samples, key=lambda row: float(row.t_s))),
            metadata={
                "tle_hash": str(derived["tle_hash"]),
                "tle_epoch": str(derived["tle_epoch"]),
                "altitude_km": float(altitude_km),
                "elevation_min_deg": float(request.elevation_min_deg),
                "dt_s": float(request.dt_s),
            },
        )


def _preview_fallback_trace(*, request: OrbitProviderRequest, reason: str) -> OrbitTrace:
    analytic = AnalyticOrbitProvider().build_trace(request)
    return OrbitTrace(
        provider_id="skyfield",
        provider_version="unavailable",
        execution_mode=str(request.execution_mode or "preview"),
        trusted=False,
        compatibility="preview_fallback",
        samples=analytic.samples,
        metadata={
            "fallback_provider": "analytic",
            "reason": str(reason),
            "altitude_km": float(request.altitude_km),
            "elevation_min_deg": float(request.elevation_min_deg),
            "dt_s": float(request.dt_s),
        },
        untrusted_reasons=(str(reason),),
    )


def _derive_altitude_from_tle(
    *,
    skyfield_api: Any,
    line1: str,
    line2: str,
    satellite_name: str,
    fallback_altitude_km: float,
) -> dict[str, Any]:
    try:
        ts = skyfield_api.load.timescale()
        satellite = skyfield_api.EarthSatellite(line1, line2, satellite_name, ts)
        geocentric = satellite.at(satellite.epoch)
        radius_km = float(geocentric.position.km.dot(geocentric.position.km) ** 0.5)
        altitude_km = max(1.0, radius_km - 6371.0)
        tle_epoch = satellite.epoch.utc_iso()
    except Exception:
        altitude_km = float(max(1.0, fallback_altitude_km))
        tle_epoch = "unknown"

    digest = hashlib.sha256((line1.strip() + "\n" + line2.strip()).encode("utf-8")).hexdigest()
    return {
        "provider_version": str(getattr(skyfield_api, "__version__", "unknown")),
        "tle_hash": digest,
        "tle_epoch": str(tle_epoch),
        "altitude_km": float(altitude_km),
    }


def _import_skyfield() -> Any | None:
    try:
        from skyfield import api
    except Exception:
        return None
    return api
