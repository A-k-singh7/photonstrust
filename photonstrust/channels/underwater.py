"""Underwater quantum communication channel models.

Beer-Lambert attenuation model with Jerlov water type classification
for modeling QKD over underwater optical links.

Key references:
    - Shi et al., JOSA A 32, 349 (2015) -- underwater QKD feasibility
    - Jerlov, "Marine Optics" (1976) -- water type classification
    - Haltrin, Appl. Opt. 38, 6826 (1999) -- inherent optical properties
    - Uitz et al., JGR Oceans 111 (2006) -- chlorophyll profiles
    - Cochenour et al., Opt. Express 21, 9668 (2013) -- underwater QKD demo

Water type classification (Jerlov 1976):
    - Type I:    Clearest open ocean
    - Type IA:   Clear open ocean
    - Type IB:   Open ocean (typical)
    - Type II:   Open ocean (productive)
    - Type III:  Coastal, moderate turbidity
    - Type 1C:   Coastal, turbid
    - Type 3C:   Coastal, very turbid (harbor)

Models:
    - Beer-Lambert: T = exp(-c * d) where c is total attenuation
    - Attenuation = absorption + scattering
    - Optimal wavelength: blue-green window (450-550 nm)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UnderwaterChannelResult:
    """Result of underwater channel calculation."""
    distance_m: float
    wavelength_nm: float
    water_type: str
    transmission: float               # total transmission
    attenuation_coeff_per_m: float    # total c (m^-1)
    absorption_coeff_per_m: float     # absorption a (m^-1)
    scattering_coeff_per_m: float     # scattering b (m^-1)
    loss_db: float                    # total loss in dB
    max_qkd_distance_m: float        # estimated max QKD range
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Jerlov water type coefficients
# ---------------------------------------------------------------------------

# Attenuation coefficients at key wavelengths (m^-1)
# Format: {water_type: {wavelength_nm: (absorption, scattering)}}
# Based on Jerlov (1976) and Haltrin (1999)

# Simplified: total attenuation coefficient c = a + b at blue-green optimum
# and at other QKD-relevant wavelengths
_JERLOV_COEFFICIENTS: dict[str, dict[int, tuple[float, float]]] = {
    "I": {
        # (absorption, scattering) in m^-1
        450: (0.0145, 0.0037),   # blue
        470: (0.0120, 0.0032),   # blue
        500: (0.0257, 0.0024),   # blue-green
        520: (0.0357, 0.0021),   # green (near minimum for open ocean)
        550: (0.0638, 0.0017),   # green
        600: (0.2440, 0.0012),   # orange
        650: (0.3490, 0.0009),   # red
        700: (0.6500, 0.0007),   # deep red
    },
    "IA": {
        450: (0.0180, 0.0055),
        470: (0.0155, 0.0048),
        500: (0.0280, 0.0036),
        520: (0.0385, 0.0031),
        550: (0.0660, 0.0025),
        600: (0.2460, 0.0018),
        650: (0.3510, 0.0014),
        700: (0.6520, 0.0010),
    },
    "IB": {
        450: (0.0250, 0.0082),
        470: (0.0210, 0.0071),
        500: (0.0330, 0.0053),
        520: (0.0430, 0.0046),
        550: (0.0700, 0.0037),
        600: (0.2490, 0.0027),
        650: (0.3530, 0.0020),
        700: (0.6540, 0.0015),
    },
    "II": {
        450: (0.0420, 0.0160),
        470: (0.0350, 0.0139),
        500: (0.0430, 0.0104),
        520: (0.0530, 0.0090),
        550: (0.0800, 0.0072),
        600: (0.2550, 0.0052),
        650: (0.3580, 0.0039),
        700: (0.6570, 0.0030),
    },
    "III": {
        450: (0.0880, 0.0410),
        470: (0.0750, 0.0356),
        500: (0.0750, 0.0267),
        520: (0.0800, 0.0231),
        550: (0.1050, 0.0185),
        600: (0.2700, 0.0134),
        650: (0.3700, 0.0100),
        700: (0.6650, 0.0075),
    },
    "1C": {
        450: (0.1800, 0.0900),
        470: (0.1500, 0.0782),
        500: (0.1300, 0.0586),
        520: (0.1200, 0.0507),
        550: (0.1400, 0.0406),
        600: (0.3000, 0.0294),
        650: (0.4000, 0.0220),
        700: (0.6900, 0.0165),
    },
    "3C": {
        450: (0.3800, 0.2200),
        470: (0.3200, 0.1912),
        500: (0.2600, 0.1432),
        520: (0.2300, 0.1240),
        550: (0.2200, 0.0993),
        600: (0.3600, 0.0719),
        650: (0.4500, 0.0538),
        700: (0.7300, 0.0403),
    },
}


def jerlov_water_coefficients(
    water_type: str,
    wavelength_nm: float,
) -> tuple[float, float]:
    """Get absorption and scattering coefficients for a Jerlov water type.

    Interpolates between tabulated wavelengths.

    Args:
        water_type: Jerlov water type ("I", "IA", "IB", "II", "III", "1C", "3C")
        wavelength_nm: Wavelength in nm

    Returns:
        (absorption_per_m, scattering_per_m) tuple

    Ref: Jerlov, "Marine Optics" (1976), Ch. 4
    """
    wt = str(water_type).strip().upper()
    # Normalize common aliases
    wt_map = {"1": "I", "1A": "IA", "1B": "IB", "2": "II", "3": "III"}
    wt = wt_map.get(wt, wt)

    if wt not in _JERLOV_COEFFICIENTS:
        wt = "IB"  # default to typical open ocean

    coeff_table = _JERLOV_COEFFICIENTS[wt]
    lam = float(wavelength_nm)

    wavelengths = sorted(coeff_table.keys())

    # Exact match
    if int(lam) in coeff_table:
        return coeff_table[int(lam)]

    # Extrapolate below minimum
    if lam <= wavelengths[0]:
        return coeff_table[wavelengths[0]]

    # Extrapolate above maximum
    if lam >= wavelengths[-1]:
        return coeff_table[wavelengths[-1]]

    # Linear interpolation
    for i in range(len(wavelengths) - 1):
        w1, w2 = wavelengths[i], wavelengths[i + 1]
        if w1 <= lam <= w2:
            frac = (lam - w1) / (w2 - w1)
            a1, b1 = coeff_table[w1]
            a2, b2 = coeff_table[w2]
            a_interp = a1 + frac * (a2 - a1)
            b_interp = b1 + frac * (b2 - b1)
            return (a_interp, b_interp)

    return coeff_table[wavelengths[-1]]


# ---------------------------------------------------------------------------
# Beer-Lambert transmission
# ---------------------------------------------------------------------------

def beer_lambert_transmission(
    distance_m: float,
    attenuation_coeff_per_m: float,
) -> float:
    """Beer-Lambert transmission through an absorbing medium.

    T = exp(-c * d)

    Args:
        distance_m: Propagation distance (m)
        attenuation_coeff_per_m: Total attenuation coefficient c (m^-1)

    Returns:
        Transmission (0 to 1)
    """
    d = max(0.0, float(distance_m))
    c = max(0.0, float(attenuation_coeff_per_m))
    return math.exp(-c * d)


# ---------------------------------------------------------------------------
# Underwater channel model
# ---------------------------------------------------------------------------

def underwater_channel(
    distance_m: float,
    *,
    wavelength_nm: float = 520.0,
    water_type: str = "IB",
    detector_efficiency: float = 0.25,
    dark_count_rate_cps: float = 100.0,
    source_rate_hz: float = 1e6,
) -> UnderwaterChannelResult:
    """Compute underwater optical channel transmission.

    Uses Beer-Lambert law with Jerlov water type classification.

    The maximum QKD distance is estimated from the loss budget
    where the key rate approaches zero.

    Args:
        distance_m: Link distance (m)
        wavelength_nm: Operating wavelength (nm)
        water_type: Jerlov water type
        detector_efficiency: Single-photon detector efficiency
        dark_count_rate_cps: Dark count rate
        source_rate_hz: Source repetition rate

    Returns:
        UnderwaterChannelResult with transmission and diagnostics
    """
    d = max(0.0, float(distance_m))
    lam = max(100.0, float(wavelength_nm))

    # Get water coefficients
    a, b = jerlov_water_coefficients(water_type, lam)
    c = a + b  # total attenuation

    # Beer-Lambert transmission
    T = beer_lambert_transmission(d, c)

    # Loss in dB
    loss_db = -10.0 * math.log10(max(1e-30, T))

    # Estimate max QKD distance
    # Rough criterion: need eta > dark_counts / source_rate for positive key
    eta_min = max(1e-15, dark_count_rate_cps / max(1.0, source_rate_hz))
    if c > 0:
        max_dist = -math.log(max(eta_min, 1e-30)) / c
    else:
        max_dist = float("inf")

    return UnderwaterChannelResult(
        distance_m=d,
        wavelength_nm=lam,
        water_type=water_type,
        transmission=T,
        attenuation_coeff_per_m=c,
        absorption_coeff_per_m=a,
        scattering_coeff_per_m=b,
        loss_db=loss_db,
        max_qkd_distance_m=max_dist,
        diagnostics={
            "detector_efficiency": detector_efficiency,
            "dark_count_rate_cps": dark_count_rate_cps,
            "source_rate_hz": source_rate_hz,
            "eta_total": T * detector_efficiency,
            "optical_depth": c * d,
        },
    )


def optimal_wavelength(
    water_type: str = "IB",
) -> float:
    """Find the wavelength with minimum attenuation for a water type.

    Args:
        water_type: Jerlov water type

    Returns:
        Optimal wavelength in nm
    """
    wt = str(water_type).strip().upper()
    wt_map = {"1": "I", "1A": "IA", "1B": "IB", "2": "II", "3": "III"}
    wt = wt_map.get(wt, wt)
    if wt not in _JERLOV_COEFFICIENTS:
        wt = "IB"

    coeff_table = _JERLOV_COEFFICIENTS[wt]
    best_wl = 520
    best_c = float("inf")
    for wl, (a, b) in coeff_table.items():
        c = a + b
        if c < best_c:
            best_c = c
            best_wl = wl

    return float(best_wl)
