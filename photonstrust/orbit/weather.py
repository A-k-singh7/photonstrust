"""Weather probability models for satellite QKD scheduling."""

from __future__ import annotations

from dataclasses import dataclass


# Published clear-sky probabilities for QKD ground station sites.
# Values are approximate annual averages from astronomical site surveys.
WEATHER_PRESETS: dict[str, dict] = {
    "mauna_kea": {
        "description": "Mauna Kea, Hawaii (4205m)",
        "latitude_deg": 19.82,
        "longitude_deg": -155.47,
        "annual_clear_fraction": 0.65,
        "monthly_clear": {
            1: 0.55, 2: 0.55, 3: 0.60, 4: 0.65, 5: 0.70, 6: 0.75,
            7: 0.75, 8: 0.70, 9: 0.65, 10: 0.60, 11: 0.55, 12: 0.50,
        },
    },
    "xinglong": {
        "description": "Xinglong Observatory, China (960m)",
        "latitude_deg": 40.39,
        "longitude_deg": 117.57,
        "annual_clear_fraction": 0.45,
        "monthly_clear": {
            1: 0.55, 2: 0.50, 3: 0.40, 4: 0.35, 5: 0.35, 6: 0.25,
            7: 0.20, 8: 0.25, 9: 0.40, 10: 0.55, 11: 0.60, 12: 0.60,
        },
    },
    "vienna": {
        "description": "Vienna, Austria (200m)",
        "latitude_deg": 48.21,
        "longitude_deg": 16.37,
        "annual_clear_fraction": 0.30,
        "monthly_clear": {
            1: 0.20, 2: 0.25, 3: 0.30, 4: 0.35, 5: 0.35, 6: 0.35,
            7: 0.40, 8: 0.35, 9: 0.30, 10: 0.25, 11: 0.20, 12: 0.15,
        },
    },
    "tenerife": {
        "description": "Teide Observatory, Tenerife (2390m)",
        "latitude_deg": 28.30,
        "longitude_deg": -16.51,
        "annual_clear_fraction": 0.70,
        "monthly_clear": {
            1: 0.60, 2: 0.60, 3: 0.65, 4: 0.70, 5: 0.75, 6: 0.80,
            7: 0.85, 8: 0.80, 9: 0.75, 10: 0.65, 11: 0.60, 12: 0.55,
        },
    },
    "generic_urban": {
        "description": "Generic urban site",
        "latitude_deg": 45.0,
        "longitude_deg": 0.0,
        "annual_clear_fraction": 0.25,
        "monthly_clear": {
            1: 0.20, 2: 0.20, 3: 0.25, 4: 0.25, 5: 0.30, 6: 0.30,
            7: 0.30, 8: 0.30, 9: 0.25, 10: 0.25, 11: 0.20, 12: 0.20,
        },
    },
}


def clear_sky_probability(location: str, month: int | None = None) -> float:
    """Return clear-sky probability for a known QKD ground station site.

    Parameters
    ----------
    location : str
        Site name (key in WEATHER_PRESETS).
    month : int or None
        Month (1-12). If None, returns annual average.

    Returns
    -------
    float
        Probability of clear sky (0 to 1).
    """
    loc = location.strip().lower()
    if loc not in WEATHER_PRESETS:
        raise ValueError(
            f"Unknown location {location!r}. "
            f"Available: {sorted(WEATHER_PRESETS.keys())}"
        )

    site = WEATHER_PRESETS[loc]

    if month is None:
        return float(site["annual_clear_fraction"])

    if month < 1 or month > 12:
        raise ValueError("month must be 1-12")

    return float(site["monthly_clear"][month])


def estimated_clear_nights_per_month(location: str, month: int) -> float:
    """Estimate number of clear nights in a given month.

    Assumes ~10 hours of darkness per night on average.
    """
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    p_clear = clear_sky_probability(location, month)
    return p_clear * days_in_month[month - 1]
