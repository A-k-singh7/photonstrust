"""Satellite QKD pass scheduling optimization."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Contact:
    """A visibility window between a satellite and ground station."""
    satellite_id: str
    ground_station_id: str
    start_time_s: float
    end_time_s: float
    max_elevation_deg: float
    mean_elevation_deg: float


@dataclass(frozen=True)
class ScheduleEntry:
    """A scheduled pass in the solution."""
    contact: Contact
    key_volume_bits: float
    clear_sky_prob: float
    priority: float


@dataclass(frozen=True)
class Schedule:
    """Complete scheduling solution."""
    entries: list[ScheduleEntry]
    total_key_bits: float
    total_expected_key_bits: float  # weighted by weather probability
    per_gs_key_bits: dict[str, float]
    utilization: float  # fraction of contacts used
    n_conflicts_resolved: int


def key_volume_per_pass(
    duration_s: float,
    mean_elevation_deg: float,
    *,
    zenith_rate_bps: float = 10000.0,
    min_elevation_deg: float = 10.0,
    elevation_exponent: float = 2.0,
) -> float:
    """Estimate key volume from a satellite pass.

    Key rate scales with elevation:
    SKR(el) ~ SKR_zenith * (sin(el))^exponent

    Total key = integral over pass duration.
    For simplicity, uses mean elevation:
    K = SKR_zenith * (sin(mean_el))^exp * duration

    Parameters
    ----------
    duration_s : float
        Pass duration in seconds.
    mean_elevation_deg : float
        Mean elevation angle during pass.
    zenith_rate_bps : float
        Key rate at zenith (90 deg) in bits/s.
    min_elevation_deg : float
        Minimum elevation for operation.
    elevation_exponent : float
        Rate scaling exponent with sin(elevation).

    Returns
    -------
    float
        Estimated key volume in bits.
    """
    if mean_elevation_deg < min_elevation_deg:
        return 0.0
    if duration_s <= 0:
        return 0.0

    el_rad = math.radians(mean_elevation_deg)
    rate = zenith_rate_bps * (math.sin(el_rad) ** elevation_exponent)
    return rate * duration_s


def schedule_passes_greedy(
    contacts: list[Contact],
    weather_probs: dict[str, float] | None = None,
    *,
    zenith_rate_bps: float = 10000.0,
    max_passes_per_gs: int | None = None,
    staleness_weight: float = 0.1,
) -> Schedule:
    """Priority-based greedy scheduler.

    Priority = K_expected * (1 + beta * ln(1 + t_since_last))

    Greedily selects highest-priority non-conflicting contacts.
    A conflict: same satellite or same ground station at overlapping times.
    """
    if not contacts:
        return Schedule(
            entries=[], total_key_bits=0.0, total_expected_key_bits=0.0,
            per_gs_key_bits={}, utilization=0.0, n_conflicts_resolved=0,
        )

    if weather_probs is None:
        weather_probs = {}

    # Compute key volume and priority for each contact
    scored = []
    for c in contacts:
        duration = c.end_time_s - c.start_time_s
        kv = key_volume_per_pass(
            duration, c.mean_elevation_deg, zenith_rate_bps=zenith_rate_bps,
        )
        p_clear = weather_probs.get(c.ground_station_id, 1.0)
        expected_kv = kv * p_clear

        # Staleness bonus (simplified: based on start time as proxy)
        staleness_bonus = 1.0 + staleness_weight * math.log1p(c.start_time_s / 3600.0)
        priority = expected_kv * staleness_bonus

        scored.append((priority, kv, p_clear, c))

    # Sort by priority (descending)
    scored.sort(key=lambda x: -x[0])

    # Greedy selection with conflict resolution
    selected = []
    sat_busy = {}    # sat_id -> list of (start, end)
    gs_busy = {}     # gs_id -> list of (start, end)
    gs_count = {}    # gs_id -> count of passes
    conflicts = 0

    def is_conflicting(busy_list, start, end):
        for s, e in busy_list:
            if start < e and end > s:
                return True
        return False

    for priority, kv, p_clear, c in scored:
        sat_intervals = sat_busy.get(c.satellite_id, [])
        gs_intervals = gs_busy.get(c.ground_station_id, [])

        if is_conflicting(sat_intervals, c.start_time_s, c.end_time_s):
            conflicts += 1
            continue
        if is_conflicting(gs_intervals, c.start_time_s, c.end_time_s):
            conflicts += 1
            continue
        if max_passes_per_gs is not None:
            if gs_count.get(c.ground_station_id, 0) >= max_passes_per_gs:
                conflicts += 1
                continue

        selected.append(ScheduleEntry(
            contact=c, key_volume_bits=kv,
            clear_sky_prob=p_clear, priority=priority,
        ))
        sat_busy.setdefault(c.satellite_id, []).append(
            (c.start_time_s, c.end_time_s)
        )
        gs_busy.setdefault(c.ground_station_id, []).append(
            (c.start_time_s, c.end_time_s)
        )
        gs_count[c.ground_station_id] = gs_count.get(c.ground_station_id, 0) + 1

    total_key = sum(e.key_volume_bits for e in selected)
    total_expected = sum(e.key_volume_bits * e.clear_sky_prob for e in selected)

    per_gs = {}
    for e in selected:
        gs = e.contact.ground_station_id
        per_gs[gs] = per_gs.get(gs, 0.0) + e.key_volume_bits * e.clear_sky_prob

    utilization = len(selected) / len(contacts) if contacts else 0.0

    return Schedule(
        entries=selected,
        total_key_bits=total_key,
        total_expected_key_bits=total_expected,
        per_gs_key_bits=per_gs,
        utilization=utilization,
        n_conflicts_resolved=conflicts,
    )
