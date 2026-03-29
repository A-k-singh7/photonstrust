from __future__ import annotations

from photonstrust.satellite.types import AtmosphereProfile

# Reference extinction coefficients (dB/km) under clear conditions (visibility ~23 km).
_EXTINCTION_TABLE: dict[float, float] = {
    785.0: 0.07,
    810.0: 0.06,
    850.0: 0.05,
    1310.0: 0.02,
    1550.0: 0.015,
}

_SORTED_WAVELENGTHS = sorted(_EXTINCTION_TABLE.keys())


def _interpolate_extinction(wavelength_nm: float) -> float:
    """Linear interpolation across the reference extinction table."""
    if wavelength_nm <= _SORTED_WAVELENGTHS[0]:
        return _EXTINCTION_TABLE[_SORTED_WAVELENGTHS[0]]
    if wavelength_nm >= _SORTED_WAVELENGTHS[-1]:
        return _EXTINCTION_TABLE[_SORTED_WAVELENGTHS[-1]]

    for i in range(len(_SORTED_WAVELENGTHS) - 1):
        lo = _SORTED_WAVELENGTHS[i]
        hi = _SORTED_WAVELENGTHS[i + 1]
        if lo <= wavelength_nm <= hi:
            frac = (wavelength_nm - lo) / (hi - lo)
            return _EXTINCTION_TABLE[lo] + frac * (_EXTINCTION_TABLE[hi] - _EXTINCTION_TABLE[lo])

    # Fallback (should not reach here).
    return _EXTINCTION_TABLE[_SORTED_WAVELENGTHS[-1]]


def _dominant_mechanism(wavelength_nm: float) -> str:
    if wavelength_nm < 900.0:
        return "Rayleigh+Mie"
    return "Mie"


def lookup_extinction_db_per_km(
    wavelength_nm: float,
    *,
    condition: str = "clear",
    visibility_km: float = 23.0,
) -> AtmosphereProfile:
    """Return atmospheric extinction for a given wavelength and visibility.

    Uses Koschmieder scaling for non-clear conditions:
        scale = 23.0 / max(1, visibility_km)
    """
    base_extinction = _interpolate_extinction(wavelength_nm)
    scale = 23.0 / max(1.0, visibility_km)
    extinction = base_extinction * scale

    return AtmosphereProfile(
        wavelength_nm=wavelength_nm,
        extinction_db_per_km=extinction,
        dominant_mechanism=_dominant_mechanism(wavelength_nm),
        visibility_km=visibility_km,
        condition=condition,
    )


def get_atmosphere_profiles() -> list[dict]:
    """Return all standard atmosphere profiles as a list of dicts."""
    profiles: list[dict] = []
    for wl in _SORTED_WAVELENGTHS:
        profile = lookup_extinction_db_per_km(wl, condition="clear", visibility_km=23.0)
        profiles.append(profile.as_dict())
    return profiles
