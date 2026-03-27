"""Tests for weather probability models (Phase C, Task C6)."""

from __future__ import annotations

import pytest

from photonstrust.orbit.weather import (
    WEATHER_PRESETS,
    clear_sky_probability,
    estimated_clear_nights_per_month,
)


def test_annual_clear_sky_bounds() -> None:
    """All preset annual clear-sky fractions must lie in (0, 1)."""
    for loc in WEATHER_PRESETS:
        p = clear_sky_probability(loc)
        assert 0.0 < p < 1.0


def test_monthly_seasonal_variation() -> None:
    """Mauna Kea summer months should have higher clear-sky than winter."""
    summer = clear_sky_probability("mauna_kea", month=7)
    winter = clear_sky_probability("mauna_kea", month=12)
    assert summer > winter


def test_unknown_location_raises() -> None:
    """An unknown location must raise ValueError."""
    with pytest.raises(ValueError):
        clear_sky_probability("mars")


def test_invalid_month_raises() -> None:
    """Month outside 1-12 must raise ValueError."""
    with pytest.raises(ValueError):
        clear_sky_probability("mauna_kea", month=13)


def test_clear_nights_positive() -> None:
    """Estimated clear nights per month must be positive for all presets."""
    for loc in WEATHER_PRESETS:
        for m in range(1, 13):
            nights = estimated_clear_nights_per_month(loc, m)
            assert nights > 0.0
