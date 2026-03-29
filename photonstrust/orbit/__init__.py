"""OrbitVerify mission execution primitives."""

from __future__ import annotations

from photonstrust.orbit.geometry import annual_pass_count, generate_elevation_profile, slant_range_km
from photonstrust.orbit.pass_envelope import run_orbit_pass_from_config, simulate_orbit_pass
from photonstrust.orbit.provider_manager import resolve_orbit_provider
from photonstrust.orbit.constellation import (
    ConstellationConfig,
    ConstellationSatellite,
    ground_track_coverage,
    orbital_period,
    sso_inclination,
    walker_constellation,
)
from photonstrust.orbit.weather import (
    WEATHER_PRESETS,
    clear_sky_probability,
    estimated_clear_nights_per_month,
)
from photonstrust.orbit.scheduler import (
    Contact,
    Schedule,
    ScheduleEntry,
    key_volume_per_pass,
    schedule_passes_greedy,
)

__all__ = [
    "simulate_orbit_pass",
    "run_orbit_pass_from_config",
    "slant_range_km",
    "generate_elevation_profile",
    "annual_pass_count",
    "resolve_orbit_provider",
    "ConstellationConfig",
    "ConstellationSatellite",
    "ground_track_coverage",
    "orbital_period",
    "sso_inclination",
    "walker_constellation",
    "WEATHER_PRESETS",
    "clear_sky_probability",
    "estimated_clear_nights_per_month",
    "Contact",
    "Schedule",
    "ScheduleEntry",
    "key_volume_per_pass",
    "schedule_passes_greedy",
]
