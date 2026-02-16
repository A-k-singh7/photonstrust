"""Fiber channel models."""

from __future__ import annotations

import math


def apply_fiber_loss(distance_km: float, alpha_db_per_km: float) -> float:
    return 10 ** (-(distance_km * alpha_db_per_km) / 10.0)


def time_of_flight_ns(distance_km: float, n_group: float = 1.468) -> float:
    c_km_per_ns = 0.299792458
    return (distance_km * n_group) / c_km_per_ns


def dispersion_ps(distance_km: float, dispersion_ps_per_km: float) -> float:
    return distance_km * dispersion_ps_per_km


def polarization_drift(distance_km: float, coherence_length_km: float = 50.0) -> float:
    if coherence_length_km <= 0:
        return 1.0
    return math.exp(-distance_km / coherence_length_km)
