"""Tests for Walker delta constellation generation (Phase C, Task C6)."""

from __future__ import annotations

import pytest

from photonstrust.orbit.constellation import (
    ground_track_coverage,
    orbital_period,
    sso_inclination,
    walker_constellation,
)


def test_walker_placement_correct_count() -> None:
    """Walker 12/3/1 must produce 12 satellites with 4 per plane."""
    cfg = walker_constellation(12, 3, 1, 550.0, inclination_deg=97.5)
    assert len(cfg.satellites) == 12
    for p in range(3):
        count = sum(1 for s in cfg.satellites if s.plane_index == p)
        assert count == 4


def test_walker_raan_spacing() -> None:
    """Three planes must be separated by 120 degrees in RAAN."""
    cfg = walker_constellation(12, 3, 1, 550.0, inclination_deg=97.5)
    raans = sorted({s.raan_deg for s in cfg.satellites})
    assert len(raans) == 3
    expected_spacing = 120.0
    for i in range(1, len(raans)):
        assert abs(raans[i] - raans[i - 1] - expected_spacing) < 1e-9


def test_orbital_period_iss() -> None:
    """ISS-like orbit at 400 km altitude should have period near 5560 s."""
    period = orbital_period(400.0)
    assert abs(period - 5560.0) < 100.0


def test_sso_inclination_range() -> None:
    """SSO inclination for 500-800 km should fall in 97-99 degrees."""
    for alt in [500.0, 600.0, 700.0, 800.0]:
        inc = sso_inclination(alt)
        assert 97.0 <= inc <= 99.0, f"SSO inc at {alt} km = {inc}"


def test_sso_inclination_used_when_none() -> None:
    """When inclination_deg=None, walker_constellation uses SSO inclination."""
    cfg = walker_constellation(12, 3, 1, 550.0, inclination_deg=None)
    expected_inc = sso_inclination(550.0)
    assert abs(cfg.inclination_deg - expected_inc) < 1e-9
    for sat in cfg.satellites:
        assert abs(sat.inclination_deg - expected_inc) < 1e-9


def test_invalid_total_sats_raises() -> None:
    """total_sats not divisible by n_planes must raise ValueError."""
    with pytest.raises(ValueError):
        walker_constellation(10, 3, 0, 550.0, inclination_deg=97.5)


def test_ground_track_coverage_increases_with_sats() -> None:
    """More satellites should yield equal or higher ground track coverage."""
    small = walker_constellation(6, 3, 1, 550.0, inclination_deg=53.0)
    large = walker_constellation(24, 3, 1, 550.0, inclination_deg=53.0)
    cov_small = ground_track_coverage(small, latitude_deg=30.0)
    cov_large = ground_track_coverage(large, latitude_deg=30.0)
    assert cov_large >= cov_small
