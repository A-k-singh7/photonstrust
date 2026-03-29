"""Tests for satellite QKD pass scheduling (Phase C, Task C6)."""

from __future__ import annotations

import math

import pytest

from photonstrust.orbit.scheduler import (
    Contact,
    key_volume_per_pass,
    schedule_passes_greedy,
)


# ---------------------------------------------------------------------------
# key_volume_per_pass
# ---------------------------------------------------------------------------

def test_key_volume_scales_with_elevation() -> None:
    """Higher mean elevation must yield more key bits for same duration."""
    kv_low = key_volume_per_pass(300.0, 20.0, zenith_rate_bps=10000.0)
    kv_high = key_volume_per_pass(300.0, 60.0, zenith_rate_bps=10000.0)
    assert kv_high > kv_low > 0.0


def test_key_volume_zero_below_threshold() -> None:
    """Mean elevation below min_elevation must return 0 bits."""
    kv = key_volume_per_pass(
        300.0, 5.0, zenith_rate_bps=10000.0, min_elevation_deg=10.0,
    )
    assert kv == 0.0


# ---------------------------------------------------------------------------
# schedule_passes_greedy
# ---------------------------------------------------------------------------

def test_greedy_selects_highest_priority() -> None:
    """The contact with the highest expected key volume is selected first."""
    low = Contact("SAT-01", "GS-A", 0.0, 300.0, 30.0, 15.0)
    high = Contact("SAT-02", "GS-B", 0.0, 300.0, 85.0, 80.0)
    sched = schedule_passes_greedy([low, high])
    # Both should be selected (no conflict), but the first entry should be
    # the higher-priority one.
    assert len(sched.entries) == 2
    assert sched.entries[0].contact.satellite_id == "SAT-02"


def test_conflict_resolution() -> None:
    """Overlapping contacts on the same satellite: only one is selected."""
    c1 = Contact("SAT-01", "GS-A", 0.0, 300.0, 45.0, 30.0)
    c2 = Contact("SAT-01", "GS-B", 100.0, 400.0, 60.0, 45.0)
    sched = schedule_passes_greedy([c1, c2])
    assert len(sched.entries) == 1
    assert sched.n_conflicts_resolved == 1


def test_weather_reduces_expected_key() -> None:
    """Clear-sky probability < 1 must reduce total_expected_key_bits."""
    contacts = [Contact("SAT-01", "GS-A", 0.0, 300.0, 45.0, 30.0)]
    sched_clear = schedule_passes_greedy(contacts, weather_probs={"GS-A": 1.0})
    sched_cloudy = schedule_passes_greedy(contacts, weather_probs={"GS-A": 0.3})
    assert sched_clear.total_expected_key_bits > sched_cloudy.total_expected_key_bits
    # Raw key bits are identical regardless of weather.
    assert abs(sched_clear.total_key_bits - sched_cloudy.total_key_bits) < 1e-6


def test_max_passes_per_gs_enforced() -> None:
    """max_passes_per_gs=1 limits each ground station to a single pass."""
    contacts = [
        Contact("SAT-01", "GS-A", 0.0, 300.0, 45.0, 30.0),
        Contact("SAT-02", "GS-A", 500.0, 800.0, 50.0, 35.0),
    ]
    sched = schedule_passes_greedy(contacts, max_passes_per_gs=1)
    gs_a_entries = [e for e in sched.entries if e.contact.ground_station_id == "GS-A"]
    assert len(gs_a_entries) == 1


def test_empty_contacts() -> None:
    """Empty contact list must produce an empty schedule."""
    sched = schedule_passes_greedy([])
    assert sched.entries == []
    assert sched.total_key_bits == 0.0
    assert sched.total_expected_key_bits == 0.0
    assert sched.per_gs_key_bits == {}
    assert sched.utilization == 0.0
    assert sched.n_conflicts_resolved == 0
