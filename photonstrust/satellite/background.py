from __future__ import annotations

import math

from photonstrust.satellite.types import BackgroundEstimate

# Spectral radiance lookup table (W/m^2/sr/nm).
# References: Er-long et al. (2005) NJP 7, 215; Liao et al. (2017) Nature 549.
RADIANCE_TABLE: dict[str, dict[float, float]] = {
    "night": {785.0: 1e-8, 810.0: 1e-8, 850.0: 1e-8, 1310.0: 5e-9, 1550.0: 3e-9},
    "twilight": {785.0: 1e-4, 810.0: 8e-5, 850.0: 5e-5, 1310.0: 1e-5, 1550.0: 5e-6},
    "day": {785.0: 1e-2, 810.0: 8e-3, 850.0: 5e-3, 1310.0: 1e-3, 1550.0: 5e-4},
    "full_moon": {785.0: 1e-6, 810.0: 1e-6, 850.0: 8e-7, 1310.0: 5e-7, 1550.0: 3e-7},
}

_SORTED_WAVELENGTHS: dict[str, list[float]] = {
    k: sorted(v.keys()) for k, v in RADIANCE_TABLE.items()
}


def _interpolate_radiance(day_night: str, wavelength_nm: float) -> float:
    """Linear interpolation across the radiance table."""
    table = RADIANCE_TABLE[day_night]
    wls = _SORTED_WAVELENGTHS[day_night]

    if wavelength_nm <= wls[0]:
        return table[wls[0]]
    if wavelength_nm >= wls[-1]:
        return table[wls[-1]]

    for i in range(len(wls) - 1):
        lo, hi = wls[i], wls[i + 1]
        if lo <= wavelength_nm <= hi:
            frac = (wavelength_nm - lo) / (hi - lo)
            return table[lo] + frac * (table[hi] - table[lo])

    return table[wls[-1]]


def estimate_background_counts_cps(
    *,
    wavelength_nm: float,
    day_night: str,
    fov_urad: float,
    rx_aperture_m: float,
    filter_bandwidth_nm: float,
    detector_efficiency: float,
    filter_transmission: float = 1.0,
) -> BackgroundEstimate:
    """Estimate background photon count rate at the detector.

    Parameters
    ----------
    wavelength_nm : float
        Operating wavelength in nanometres.
    day_night : str
        ``"day"`` or ``"night"``.
    fov_urad : float
        Receiver field-of-view half-angle in micro-radians.
    rx_aperture_m : float
        Receiver aperture diameter in metres.
    filter_bandwidth_nm : float
        Spectral filter bandwidth in nanometres.
    detector_efficiency : float
        Detector quantum efficiency (0--1).
    filter_transmission : float
        Filter transmission factor (0--1), default 1.0.
    """
    dn = day_night.lower().strip()
    if dn not in RADIANCE_TABLE:
        raise ValueError(
            f"day_night must be one of {sorted(RADIANCE_TABLE.keys())}, got {day_night!r}"
        )

    h_lambda = _interpolate_radiance(dn, wavelength_nm)
    omega_fov = math.pi * (fov_urad * 1e-6) ** 2
    a_rx = math.pi * (rx_aperture_m / 2.0) ** 2
    h_nu = 6.626e-34 * 3e8 / (wavelength_nm * 1e-9)
    n_bg = (
        h_lambda * omega_fov * a_rx * filter_bandwidth_nm
        * detector_efficiency * filter_transmission / h_nu
    )

    return BackgroundEstimate(
        counts_cps=n_bg,
        spectral_radiance_w_m2_sr_nm=h_lambda,
        fov_sr=omega_fov,
        rx_area_m2=a_rx,
        filter_bandwidth_nm=filter_bandwidth_nm,
        detector_efficiency=detector_efficiency,
        photon_energy_j=h_nu,
        day_night=dn,
        model="radiance_table_v1",
    )
