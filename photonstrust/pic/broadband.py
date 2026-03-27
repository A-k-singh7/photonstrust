"""Broadband wavelength sweep simulation for PIC circuits."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class BroadbandResult:
    """Result of a broadband wavelength sweep."""

    wavelengths_nm: np.ndarray  # shape (N,)
    transmission_db: dict[str, np.ndarray]  # port_name -> dB array shape (N,)
    group_delay_ps: dict[str, np.ndarray] | None = None  # optional

    def __eq__(self, other):
        if not isinstance(other, BroadbandResult):
            return NotImplemented
        if not np.array_equal(self.wavelengths_nm, other.wavelengths_nm):
            return False
        if set(self.transmission_db.keys()) != set(other.transmission_db.keys()):
            return False
        return all(
            np.array_equal(self.transmission_db[k], other.transmission_db[k])
            for k in self.transmission_db
        )

    def __hash__(self):
        return hash(len(self.wavelengths_nm))


def broadband_sweep(
    component_fn,  # callable(wavelength_nm) -> dict with "transmission" or np.ndarray
    wavelength_start_nm: float = 1500.0,
    wavelength_stop_nm: float = 1600.0,
    n_points: int = 201,
    output_ports: list[str] | None = None,
) -> BroadbandResult:
    """Sweep wavelength and collect transmission spectra.

    Parameters
    ----------
    component_fn : callable
        Function that takes wavelength_nm and returns either:
        - a dict with port_name -> complex transmission
        - a numpy array (treated as single-port transmission)
    wavelength_start_nm, wavelength_stop_nm : float
        Wavelength range.
    n_points : int
        Number of wavelength points.
    output_ports : list[str] or None
        Port names to track. If None, auto-detect from first call.
    """
    wavelengths = np.linspace(wavelength_start_nm, wavelength_stop_nm, n_points)

    # Probe first point to determine structure
    first = component_fn(wavelengths[0])
    if isinstance(first, dict):
        ports = output_ports or sorted(first.keys())
    elif isinstance(first, np.ndarray):
        if first.ndim == 0 or first.size == 1:
            ports = output_ports or ["out"]
        else:
            ports = output_ports or [f"out_{i}" for i in range(first.size)]
    else:
        ports = output_ports or ["out"]

    # Allocate arrays
    transmission = {p: np.zeros(n_points, dtype=complex) for p in ports}

    for i, wl in enumerate(wavelengths):
        result = component_fn(wl)
        if isinstance(result, dict):
            for p in ports:
                transmission[p][i] = result.get(p, 0.0)
        elif isinstance(result, np.ndarray):
            flat = result.flatten()
            for j, p in enumerate(ports):
                if j < len(flat):
                    transmission[p][i] = flat[j]
        else:
            transmission[ports[0]][i] = complex(result)

    # Convert to dB
    transmission_db = {}
    for p, t_complex in transmission.items():
        power = np.abs(t_complex) ** 2
        power = np.maximum(power, 1e-30)
        transmission_db[p] = 10.0 * np.log10(power)

    # Compute group delay from phase
    group_delay_ps = {}
    for p, t_complex in transmission.items():
        phase = np.unwrap(np.angle(t_complex))
        omega = 2 * math.pi * 299792458.0 / (wavelengths * 1e-9)  # rad/s
        if len(omega) > 1:
            d_phase = np.gradient(phase)
            d_omega = np.gradient(omega)
            with np.errstate(divide="ignore", invalid="ignore"):
                gd = np.where(np.abs(d_omega) > 0, -d_phase / d_omega, 0.0)
            group_delay_ps[p] = gd * 1e12  # s -> ps
        else:
            group_delay_ps[p] = np.zeros_like(phase)

    return BroadbandResult(
        wavelengths_nm=wavelengths,
        transmission_db=transmission_db,
        group_delay_ps=group_delay_ps,
    )


def ring_resonator_transmission(
    wavelength_nm: float,
    *,
    radius_um: float = 10.0,
    n_eff: float = 2.45,
    n_g: float = 4.2,
    loss_db_per_cm: float = 2.0,
    coupling_kappa: float = 0.1,
) -> complex:
    """All-pass ring resonator transmission (analytical).

    T = (t - a*exp(j*phi)) / (1 - t*a*exp(j*phi))
    where t = sqrt(1-kappa^2), a = exp(-alpha*L/2), phi = 2*pi*n_eff*L/lambda
    """
    L = 2 * math.pi * radius_um * 1e-4  # cm
    alpha = loss_db_per_cm / (10 * math.log10(math.e))  # 1/cm (power)
    a = math.exp(-alpha * L / 2)
    t = math.sqrt(1 - coupling_kappa**2)

    lam_cm = wavelength_nm * 1e-7
    phi = 2 * math.pi * n_eff * L / lam_cm

    exp_j_phi = complex(math.cos(phi), math.sin(phi))
    numerator = t - a * exp_j_phi
    denominator = 1 - t * a * exp_j_phi

    return numerator / denominator
