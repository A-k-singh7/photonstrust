from __future__ import annotations

from photonstrust.orbit.geometry import annual_pass_count, generate_elevation_profile, slant_range_km


def test_slant_range_zenith_equals_altitude() -> None:
    altitude_km = 600.0
    assert slant_range_km(90.0, altitude_km) == altitude_km


def test_slant_range_increases_at_low_elevation() -> None:
    altitude_km = 500.0
    z_zenith = slant_range_km(90.0, altitude_km)
    z_low = slant_range_km(15.0, altitude_km)
    assert z_low > z_zenith


def test_generate_elevation_profile_non_empty_and_sorted() -> None:
    samples = generate_elevation_profile(altitude_km=600.0, el_min_deg=15.0, dt_s=5.0)
    assert samples

    t_values = [float(row["t_s"]) for row in samples]
    assert t_values == sorted(t_values)

    elevations = [float(row["elevation_deg"]) for row in samples]
    assert min(elevations) >= 15.0
    assert max(elevations) <= 90.0



def test_annual_pass_count_positive_sane_range() -> None:
    passes = annual_pass_count(
        latitude_deg=52.5,
        inclination_deg=70.0,
        altitude_km=600.0,
        el_min_deg=15.0,
    )
    assert passes > 0.0
    assert passes < 15.0
