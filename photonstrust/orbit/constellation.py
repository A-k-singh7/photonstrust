"""Walker delta constellation generator for satellite QKD networks."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


# Constants
R_EARTH_KM = 6371.0
MU_EARTH = 3.986004418e5  # km^3/s^2
J2 = 1.08263e-3
OMEGA_SUN = 2 * math.pi / (365.25 * 86400)  # rad/s (Earth's orbital rate)


@dataclass(frozen=True)
class ConstellationSatellite:
    """A satellite in a Walker constellation."""
    sat_id: str
    plane_index: int
    sat_index_in_plane: int
    altitude_km: float
    inclination_deg: float
    raan_deg: float  # Right Ascension of Ascending Node
    mean_anomaly_deg: float
    orbital_period_s: float


@dataclass(frozen=True)
class ConstellationConfig:
    """Walker delta constellation T/P/F configuration."""
    total_sats: int  # T
    n_planes: int    # P
    phase_factor: int  # F
    altitude_km: float
    inclination_deg: float
    satellites: list[ConstellationSatellite]


def orbital_period(altitude_km: float) -> float:
    """Kepler's third law: T = 2*pi*sqrt((R_E+h)^3/mu).

    Returns period in seconds.
    """
    a = R_EARTH_KM + altitude_km
    return 2.0 * math.pi * math.sqrt(a ** 3 / MU_EARTH)


def sso_inclination(altitude_km: float) -> float:
    """Sun-synchronous orbit inclination.

    For SSO: dOmega/dt = -omega_sun
    dOmega/dt = -3/2 * n * J2 * (R_E/a)^2 * cos(i)

    Returns inclination in degrees.
    """
    a = R_EARTH_KM + altitude_km
    n = math.sqrt(MU_EARTH / a ** 3)  # mean motion (rad/s)

    # Required precession rate for SSO
    precession_rate = OMEGA_SUN  # must match Earth's orbital angular velocity

    # cos(i) = -precession_rate / (3/2 * n * J2 * (R_E/a)^2)
    denominator = 1.5 * n * J2 * (R_EARTH_KM / a) ** 2
    cos_i = -precession_rate / denominator

    if abs(cos_i) > 1.0:
        raise ValueError(
            f"No SSO exists at altitude {altitude_km} km "
            f"(cos(i) = {cos_i:.4f})"
        )

    return math.degrees(math.acos(cos_i))


def walker_constellation(
    total_sats: int,
    n_planes: int,
    phase_factor: int,
    altitude_km: float,
    inclination_deg: float | None = None,
) -> ConstellationConfig:
    """Generate a Walker delta constellation.

    Walker notation: T/P/F where
    - T = total number of satellites
    - P = number of orbital planes
    - F = phase factor (0 <= F < P)

    If inclination_deg is None, uses SSO inclination.

    Satellites are evenly distributed:
    - S = T/P satellites per plane
    - Planes separated by 360/P degrees in RAAN
    - Phase offset between adjacent planes: F * 360/T degrees in mean anomaly
    """
    if total_sats <= 0 or n_planes <= 0:
        raise ValueError("total_sats and n_planes must be positive")
    if total_sats % n_planes != 0:
        raise ValueError("total_sats must be divisible by n_planes")
    if phase_factor < 0 or phase_factor >= n_planes:
        raise ValueError(f"phase_factor must be in [0, {n_planes-1}]")

    if inclination_deg is None:
        inclination_deg = sso_inclination(altitude_km)

    sats_per_plane = total_sats // n_planes
    period = orbital_period(altitude_km)

    satellites = []
    for p in range(n_planes):
        raan = (360.0 / n_planes) * p
        for s in range(sats_per_plane):
            # Mean anomaly: evenly spaced in plane + phase offset
            ma = (360.0 / sats_per_plane) * s + (phase_factor * 360.0 / total_sats) * p
            ma = ma % 360.0

            sat = ConstellationSatellite(
                sat_id=f"SAT-P{p:02d}-S{s:02d}",
                plane_index=p,
                sat_index_in_plane=s,
                altitude_km=altitude_km,
                inclination_deg=inclination_deg,
                raan_deg=raan,
                mean_anomaly_deg=ma,
                orbital_period_s=period,
            )
            satellites.append(sat)

    return ConstellationConfig(
        total_sats=total_sats,
        n_planes=n_planes,
        phase_factor=phase_factor,
        altitude_km=altitude_km,
        inclination_deg=inclination_deg,
        satellites=satellites,
    )


def ground_track_coverage(
    constellation: ConstellationConfig,
    latitude_deg: float,
    min_elevation_deg: float = 10.0,
) -> float:
    """Estimate fraction of time at least one satellite is visible.

    Simplified geometric model:
    - Coverage radius on ground: r = arccos(R_E*cos(el_min)/(R_E+h)) - el_min
    - Fraction covered by ring of satellites at given latitude

    Returns coverage fraction (0 to 1).
    """
    h = constellation.altitude_km
    el_min_rad = math.radians(min_elevation_deg)

    # Ground swath half-angle
    rho = math.asin(R_EARTH_KM * math.cos(el_min_rad) / (R_EARTH_KM + h))
    ground_half_angle = math.pi / 2 - el_min_rad - rho
    ground_half_angle_deg = math.degrees(ground_half_angle)

    # Simplified: coverage ~ T * (2 * ground_half_angle / 360) * (orbital_period / sidereal_day)
    # For Walker constellations, this is a rough estimate
    sidereal_day_s = 86164.1
    revisit_factor = constellation.total_sats * (2 * ground_half_angle_deg / 360.0)

    # Account for latitude vs inclination
    lat_rad = math.radians(abs(latitude_deg))
    inc_rad = math.radians(constellation.inclination_deg)
    if lat_rad > inc_rad:
        return 0.0  # Latitude outside orbit coverage

    period_s = orbital_period(constellation.altitude_km)
    coverage = min(1.0, revisit_factor * (period_s / sidereal_day_s))
    return coverage
