"""Orbital geometry helpers for satellite QKD pass synthesis."""

from __future__ import annotations

import math
from typing import Any

_EARTH_RADIUS_KM = 6371.0
_EARTH_MU_KM3_S2 = 3.986004418e5


def slant_range_km(el_deg: float, altitude_km: float) -> float:
    """Return slant range from ground station to satellite.

    Geometry assumes spherical Earth and a circular orbit snapshot at elevation
    ``el_deg``.
    """

    elevation_rad = math.radians(max(0.0, min(90.0, float(el_deg))))
    altitude = max(1.0e-9, float(altitude_km))
    r_e = _EARTH_RADIUS_KM

    term = (r_e * math.sin(elevation_rad)) ** 2 + altitude**2 + 2.0 * r_e * altitude
    return float(max(altitude, -r_e * math.sin(elevation_rad) + math.sqrt(max(0.0, term))))


def generate_elevation_profile(
    altitude_km: float,
    el_min_deg: float,
    dt_s: float,
    *,
    day_night: str = "night",
    low_el_background_cps: float = 200.0,
    high_el_background_cps: float = 50.0,
    low_el_threshold_deg: float = 20.0,
) -> list[dict[str, Any]]:
    """Generate a symmetric LEO pass profile above ``el_min_deg``.

    Returns samples with ``t_s``, ``distance_km``, ``elevation_deg``,
    ``background_counts_cps``, and ``day_night``.
    """

    altitude = max(1.0, float(altitude_km))
    el_min = max(0.0, min(89.0, float(el_min_deg)))
    dt = max(0.1, float(dt_s))

    omega = math.sqrt(_EARTH_MU_KM3_S2 / ((_EARTH_RADIUS_KM + altitude) ** 3))
    gamma_max = _solve_visible_half_angle_rad(altitude_km=altitude, el_min_deg=el_min)
    t_half = gamma_max / max(1.0e-12, omega)

    n_steps = max(1, int(math.floor((2.0 * t_half) / dt)))
    samples: list[dict[str, Any]] = []

    for idx in range(n_steps + 1):
        t_rel = -t_half + idx * dt
        gamma = abs(omega * t_rel)
        elevation = _elevation_deg_from_central_angle(gamma_rad=gamma, altitude_km=altitude)
        if elevation + 1.0e-12 < el_min:
            continue

        distance = _distance_km_from_central_angle(gamma_rad=gamma, altitude_km=altitude)
        bg = low_el_background_cps if elevation < float(low_el_threshold_deg) else high_el_background_cps

        samples.append(
            {
                "t_s": float(t_rel + t_half),
                "distance_km": float(max(altitude, distance)),
                "elevation_deg": float(max(0.0, elevation)),
                "background_counts_cps": float(max(0.0, bg)),
                "day_night": str(day_night or "night").strip().lower() or "night",
            }
        )

    samples.sort(key=lambda row: float(row["t_s"]))
    return samples


def annual_pass_count(
    latitude_deg: float,
    inclination_deg: float,
    altitude_km: float,
    el_min_deg: float,
) -> float:
    """Return a first-order estimate for visible passes/day.

    This is a statistical planning estimator (not a propagator).
    """

    lat = abs(float(latitude_deg))
    inc = max(0.0, min(98.0, float(inclination_deg)))
    alt = max(300.0, float(altitude_km))
    el_min = max(5.0, min(60.0, float(el_min_deg)))

    orbital_period_s = 2.0 * math.pi * math.sqrt(((_EARTH_RADIUS_KM + alt) ** 3) / _EARTH_MU_KM3_S2)
    orbits_per_day = 86400.0 / max(1.0, orbital_period_s)

    latitude_visibility = max(0.08, 1.0 - max(0.0, lat - inc) / 90.0)
    altitude_factor = max(0.55, min(1.20, 0.70 + (alt - 400.0) / 1600.0))
    elevation_factor = max(0.20, min(1.0, (90.0 - el_min) / 75.0))

    passes_per_day = orbits_per_day * 0.30 * latitude_visibility * altitude_factor * elevation_factor
    return float(max(0.1, min(14.0, passes_per_day)))


def _solve_visible_half_angle_rad(*, altitude_km: float, el_min_deg: float) -> float:
    lo = 0.0
    hi = math.pi / 2.0
    target = float(el_min_deg)

    for _ in range(80):
        mid = 0.5 * (lo + hi)
        elevation = _elevation_deg_from_central_angle(gamma_rad=mid, altitude_km=altitude_km)
        if elevation >= target:
            lo = mid
        else:
            hi = mid
    return float(max(0.0, lo))


def _distance_km_from_central_angle(*, gamma_rad: float, altitude_km: float) -> float:
    r_e = _EARTH_RADIUS_KM
    r_s = r_e + float(altitude_km)
    cos_g = max(-1.0, min(1.0, math.cos(float(gamma_rad))))
    return float(math.sqrt(max(0.0, r_s * r_s + r_e * r_e - 2.0 * r_s * r_e * cos_g)))


def _elevation_deg_from_central_angle(*, gamma_rad: float, altitude_km: float) -> float:
    r_e = _EARTH_RADIUS_KM
    r_s = r_e + float(altitude_km)
    distance = _distance_km_from_central_angle(gamma_rad=float(gamma_rad), altitude_km=altitude_km)
    if distance <= 0.0:
        return 90.0
    sin_el = ((r_s * math.cos(float(gamma_rad))) - r_e) / distance
    sin_el = max(-1.0, min(1.0, sin_el))
    return float(math.degrees(math.asin(sin_el)))
