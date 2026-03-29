"""Wavelength-dependent atmospheric extinction models.

Computes atmospheric transmission as a function of wavelength,
decomposed into Rayleigh scattering, Mie (aerosol) scattering,
and molecular absorption.

Key references:
    - McCartney, "Optics of the Atmosphere" (1976) -- Rayleigh/Mie
    - Kim et al., Proc. SPIE 4530 (2001) -- Kruse/Kim visibility model
    - Kneizys et al., "MODTRAN" (1996) -- atmospheric transmission
    - Bucholtz, Appl. Opt. 34, 2765 (1995) -- Rayleigh coefficients
    - Tomasi et al., Appl. Opt. 44, 3600 (2005) -- aerosol models

Models:
    - Rayleigh: alpha_R(lambda) ~ lambda^-4
    - Mie/Kruse: alpha_M(lambda, V) with visibility-dependent coefficient
    - Molecular: simplified HITRAN-based absorption windows
    - Total: T(lambda, z) = exp(-(alpha_R + alpha_M + alpha_mol) * z)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AtmosphericTransmissionResult:
    """Result of wavelength-dependent atmospheric transmission."""
    wavelength_nm: float
    transmission: float               # total transmission
    transmission_rayleigh: float      # Rayleigh component
    transmission_mie: float           # Mie/aerosol component
    transmission_molecular: float     # molecular absorption
    extinction_coefficient_per_km: float  # total (km^-1)
    optical_depth: float              # total optical depth
    diagnostics: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rayleigh scattering
# ---------------------------------------------------------------------------

def rayleigh_scattering_coefficient(
    wavelength_nm: float,
    *,
    altitude_m: float = 0.0,
    pressure_hPa: float = 1013.25,
    temperature_K: float = 288.15,
) -> float:
    """Rayleigh scattering coefficient (km^-1) at given wavelength.

    The Rayleigh scattering coefficient at sea level is:

        alpha_R(lambda) = A / lambda^4

    where A = 1.09e-3 km^-1 nm^4 (at STP).

    Altitude correction via barometric formula for air density.

    Args:
        wavelength_nm: Wavelength in nm
        altitude_m: Altitude above sea level (m)
        pressure_hPa: Atmospheric pressure (hPa)
        temperature_K: Temperature (K)

    Returns:
        Rayleigh scattering coefficient (km^-1)

    Ref: Bucholtz, Appl. Opt. 34, 2765 (1995)
    """
    lam = max(100.0, float(wavelength_nm))
    P = max(0.0, float(pressure_hPa))
    T = max(1.0, float(temperature_K))

    # Reference: sea-level at STP (1013.25 hPa, 288.15 K)
    # A ~ 1.09e-3 km^-1 at lambda=1000nm -> alpha = A * (1000/lambda)^4
    # Which gives alpha(550nm) ~ 0.0116 km^-1 (matches Bucholtz)
    A_stp = 1.09e-3  # km^-1 at 1000 nm, sea level

    # Wavelength dependence
    alpha_stp = A_stp * (1000.0 / lam) ** 4

    # Density correction: alpha ~ P/T (ideal gas)
    density_ratio = (P / 1013.25) * (288.15 / T)

    return alpha_stp * density_ratio


# ---------------------------------------------------------------------------
# Mie (aerosol) scattering — Kruse/Kim model
# ---------------------------------------------------------------------------

def mie_scattering_coefficient(
    wavelength_nm: float,
    *,
    visibility_km: float = 23.0,
) -> float:
    """Mie/aerosol scattering coefficient using the Kruse/Kim model.

    The Mie scattering coefficient is:

        alpha_M = (3.912 / V) * (lambda / 550)^(-q)

    where V is the meteorological visibility (km) and q depends on V:
        - V > 50 km:  q = 1.6
        - 6 < V <= 50: q = 1.3
        - 1 < V <= 6:  q = 0.16*V + 0.34
        - V <= 1:      q = V - 0.5  (Kim model)

    Args:
        wavelength_nm: Wavelength in nm
        visibility_km: Meteorological visibility (km)

    Returns:
        Mie scattering coefficient (km^-1)

    Ref: Kim et al., Proc. SPIE 4530, 84 (2001)
    """
    lam = max(100.0, float(wavelength_nm))
    V = max(0.01, float(visibility_km))

    # Kruse/Kim q parameter
    if V > 50.0:
        q = 1.6
    elif V > 6.0:
        q = 1.3
    elif V > 1.0:
        q = 0.16 * V + 0.34
    else:
        q = max(0.0, V - 0.5)

    alpha_m = (3.912 / V) * (lam / 550.0) ** (-q)
    return max(0.0, alpha_m)


# ---------------------------------------------------------------------------
# Molecular absorption — simplified HITRAN windows
# ---------------------------------------------------------------------------

# Major atmospheric absorption windows (simplified)
# Format: (center_nm, width_nm, peak_absorption_km^-1)
# Based on HITRAN/MODTRAN atmospheric transmission windows
_ABSORPTION_BANDS: list[tuple[float, float, float]] = [
    # Water vapor bands
    (720.0, 20.0, 0.5),       # 720 nm O2 A-band (actually O2, not H2O)
    (940.0, 30.0, 2.0),       # 940 nm H2O band
    (1130.0, 40.0, 1.5),      # 1130 nm H2O band
    (1380.0, 50.0, 8.0),      # 1380 nm H2O strong absorption
    (1870.0, 60.0, 10.0),     # 1870 nm H2O strong absorption
    # CO2 bands
    (2010.0, 40.0, 3.0),      # 2010 nm CO2
    (2060.0, 30.0, 2.0),      # 2060 nm CO2
    # O2 bands
    (762.0, 3.0, 5.0),        # O2 A-band (narrow)
    (688.0, 3.0, 1.0),        # O2 B-band
]


def molecular_absorption_coefficient(
    wavelength_nm: float,
    *,
    humidity_relative: float = 0.5,
) -> float:
    """Simplified molecular absorption coefficient.

    Uses a simplified model of atmospheric absorption bands
    based on HITRAN/MODTRAN data. Major absorbers: H2O, CO2, O2.

    QKD-relevant windows:
        - 780-790 nm: good (Rb transition, minor O2 A-band nearby)
        - 850 nm: good (Si APD window)
        - 1310 nm: good (telecom O-band)
        - 1550 nm: good (telecom C-band)

    Args:
        wavelength_nm: Wavelength in nm
        humidity_relative: Relative humidity (0-1), scales H2O bands

    Returns:
        Molecular absorption coefficient (km^-1)
    """
    lam = float(wavelength_nm)
    rh = max(0.0, min(1.0, float(humidity_relative)))

    alpha_mol = 0.0
    for center, width, peak in _ABSORPTION_BANDS:
        # Gaussian line shape (simplified)
        sigma = width / 2.355  # FWHM to sigma
        x = (lam - center) / max(0.1, sigma)
        contribution = peak * math.exp(-0.5 * x * x)

        # Scale water vapor bands by humidity
        is_h2o = center in (940.0, 1130.0, 1380.0, 1870.0)
        if is_h2o:
            contribution *= rh

        alpha_mol += contribution

    return max(0.0, alpha_mol)


# ---------------------------------------------------------------------------
# Total atmospheric transmission
# ---------------------------------------------------------------------------

def atmospheric_transmission(
    wavelength_nm: float,
    path_length_km: float,
    *,
    visibility_km: float = 23.0,
    altitude_m: float = 0.0,
    humidity_relative: float = 0.5,
    pressure_hPa: float = 1013.25,
    temperature_K: float = 288.15,
) -> AtmosphericTransmissionResult:
    """Compute wavelength-dependent atmospheric transmission.

    Total extinction:

        alpha_total = alpha_R + alpha_M + alpha_mol

    Transmission:

        T = exp(-alpha_total * L)

    Args:
        wavelength_nm: Wavelength (nm)
        path_length_km: Propagation path length (km)
        visibility_km: Meteorological visibility (km)
        altitude_m: Ground altitude (m)
        humidity_relative: Relative humidity (0-1)
        pressure_hPa: Pressure (hPa)
        temperature_K: Temperature (K)

    Returns:
        AtmosphericTransmissionResult with component breakdown
    """
    lam = max(100.0, float(wavelength_nm))
    L = max(0.0, float(path_length_km))

    # Component coefficients (km^-1)
    alpha_r = rayleigh_scattering_coefficient(
        lam, altitude_m=altitude_m, pressure_hPa=pressure_hPa,
        temperature_K=temperature_K,
    )
    alpha_m = mie_scattering_coefficient(lam, visibility_km=visibility_km)
    alpha_mol = molecular_absorption_coefficient(lam, humidity_relative=humidity_relative)

    alpha_total = alpha_r + alpha_m + alpha_mol

    # Transmissions
    T_r = math.exp(-alpha_r * L)
    T_m = math.exp(-alpha_m * L)
    T_mol = math.exp(-alpha_mol * L)
    T_total = math.exp(-alpha_total * L)
    tau = alpha_total * L  # optical depth

    return AtmosphericTransmissionResult(
        wavelength_nm=lam,
        transmission=T_total,
        transmission_rayleigh=T_r,
        transmission_mie=T_m,
        transmission_molecular=T_mol,
        extinction_coefficient_per_km=alpha_total,
        optical_depth=tau,
        diagnostics={
            "alpha_rayleigh_per_km": alpha_r,
            "alpha_mie_per_km": alpha_m,
            "alpha_molecular_per_km": alpha_mol,
            "path_length_km": L,
            "visibility_km": float(visibility_km),
            "humidity_relative": float(humidity_relative),
        },
    )


# ---------------------------------------------------------------------------
# Convenience: QKD-window transmissions
# ---------------------------------------------------------------------------

def qkd_window_comparison(
    path_length_km: float = 1.0,
    visibility_km: float = 23.0,
) -> dict[str, AtmosphericTransmissionResult]:
    """Compare atmospheric transmission at common QKD wavelengths.

    Returns transmission at 780, 850, 1310, and 1550 nm.
    """
    wavelengths = {
        "780nm": 780.0,
        "850nm": 850.0,
        "1310nm": 1310.0,
        "1550nm": 1550.0,
    }
    return {
        name: atmospheric_transmission(
            wl, path_length_km, visibility_km=visibility_km,
        )
        for name, wl in wavelengths.items()
    }
