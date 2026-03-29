"""Capacity forecasting for QKD network links."""

from __future__ import annotations

import math

from photonstrust.planner.types import CapacityForecast


def forecast_capacity(
    link_id: str,
    current_key_rate_bps: float,
    distance_km: float,
    detector_class: str = "snspd",
    *,
    forecast_years: int = 10,
    technology_improvement_rate: float = 0.05,
) -> CapacityForecast:
    """Forecast capacity for a QKD link over time.

    Parameters
    ----------
    link_id:
        Identifier for the link.
    current_key_rate_bps:
        Current secure key rate in bits per second.
    distance_km:
        Physical link distance in kilometres.
    detector_class:
        Detector technology (e.g. ``"snspd"``, ``"spad"``).
    forecast_years:
        Number of years to forecast.
    technology_improvement_rate:
        Annual fractional improvement in technology (default 5 %).

    Returns
    -------
    CapacityForecast
    """
    years = list(range(1, forecast_years + 1))
    rates: list[float] = []
    for y in years:
        rate = (
            current_key_rate_bps
            * (1.0 + technology_improvement_rate) ** y
            * math.exp(-0.001 * y)
        )
        rates.append(round(rate, 2))

    # Determine bottleneck
    if distance_km > 100.0:
        bottleneck = "fiber_distance"
        recommendation = "Add trusted node to reduce link distance"
    elif detector_class != "snspd":
        bottleneck = "detector_efficiency"
        recommendation = "Upgrade to SNSPD detectors"
    else:
        bottleneck = "source_rate"
        recommendation = "Upgrade source repetition rate"

    return CapacityForecast(
        link_id=link_id,
        current_key_rate_bps=current_key_rate_bps,
        forecast_key_rate_bps=rates,
        forecast_years=years,
        bottleneck_component=bottleneck,
        upgrade_recommendation=recommendation,
    )
