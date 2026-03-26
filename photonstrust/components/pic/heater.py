"""Thermo-optic phase tuner (heater) component model.

Models the thermo-optic effect used in silicon-photonic phase shifters.
Supports Si, SiN, and SiO2 waveguide platforms.

Physics:
    delta_phi = (2*pi / lambda) * (dn/dT) * delta_T * L
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Port definition
# ---------------------------------------------------------------------------

HEATER_PORTS = ComponentPorts(in_ports=("in",), out_ports=("out",))

# ---------------------------------------------------------------------------
# Thermo-optic coefficients (dn/dT per K)
# ---------------------------------------------------------------------------

THERMO_OPTIC_COEFF: dict[str, float] = {
    "Si": 1.86e-4,
    "SiN": 2.45e-5,
    "SiO2": 1.0e-5,
}

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeaterResult:
    """Summary of heater operating point."""

    phase_shift_rad: float
    power_mW: float
    P_pi_mW: float
    thermal_bandwidth_kHz: float
    temperature_rise_K: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _eta_from_loss_db(loss_db: float) -> float:
    return 10.0 ** (-max(0.0, float(loss_db)) / 10.0)


def _get_dn_dT(material: str) -> float:
    key = material.strip()
    if key not in THERMO_OPTIC_COEFF:
        raise ValueError(
            f"Unknown material '{key}'. Supported: {list(THERMO_OPTIC_COEFF)}"
        )
    return THERMO_OPTIC_COEFF[key]


# ---------------------------------------------------------------------------
# Physics functions
# ---------------------------------------------------------------------------


def heater_phase_shift(
    delta_T_K: float,
    length_um: float,
    wavelength_nm: float = 1550.0,
    material: str = "Si",
) -> float:
    """Phase shift (rad) from thermo-optic effect."""
    dn_dT = _get_dn_dT(material)
    lambda_um = wavelength_nm / 1000.0
    return (2.0 * math.pi / lambda_um) * dn_dT * delta_T_K * length_um


def heater_P_pi(
    length_um: float,
    thermal_resistance_K_per_mW: float = 0.5,
    wavelength_nm: float = 1550.0,
    material: str = "Si",
) -> float:
    """Power (mW) required for a pi phase shift."""
    dn_dT = _get_dn_dT(material)
    lambda_um = wavelength_nm / 1000.0
    # Temperature for pi shift: pi = (2*pi/lambda) * dn_dT * delta_T_pi * L
    # => delta_T_pi = lambda / (2 * L * dn_dT)
    delta_T_pi = lambda_um / (2.0 * length_um * dn_dT)
    return delta_T_pi / thermal_resistance_K_per_mW


def heater_thermal_crosstalk(
    delta_T_K: float,
    distance_um: float,
    L_thermal_um: float = 40.0,
) -> float:
    """Temperature rise (K) at a neighbouring waveguide due to thermal crosstalk."""
    return delta_T_K * math.exp(-distance_um / L_thermal_um)


def heater_thermal_bandwidth(
    thermal_resistance_K_per_mW: float = 0.5,
    thermal_capacitance_nJ_per_K: float = 50.0,
) -> float:
    """Thermal 3-dB bandwidth (kHz)."""
    # R_th: K/mW -> K/W => multiply by 1e3
    R_th_K_per_W = thermal_resistance_K_per_mW * 1e3
    # C_th: nJ/K -> J/K => multiply by 1e-9
    C_th_J_per_K = thermal_capacitance_nJ_per_K * 1e-9
    tau_s = R_th_K_per_W * C_th_J_per_K
    f_hz = 1.0 / (2.0 * math.pi * tau_s)
    return f_hz / 1e3  # Hz -> kHz


# ---------------------------------------------------------------------------
# Forward matrix
# ---------------------------------------------------------------------------


def heater_forward_matrix(
    params: dict, wavelength_nm: float | None = None,
) -> np.ndarray:
    """Forward (1,1) transfer matrix for the heater phase shifter.

    Parameters (in *params* dict)
    ----------
    delta_T_K : float, optional
        Temperature rise in Kelvin.  Mutually exclusive with *power_mW*.
    power_mW : float, optional
        Electrical drive power.  Requires *thermal_resistance_K_per_mW*.
    thermal_resistance_K_per_mW : float
        Default 0.5 K/mW.
    length_um : float
        Heater length in microns (required).
    material : str
        Platform material (default "Si").
    insertion_loss_db : float
        Excess loss (default 0.1 dB).
    """
    length_um = float(params.get("length_um", 0.0) or 0.0)
    material = str(params.get("material", "Si") or "Si")
    il_db = float(params.get("insertion_loss_db", 0.1) or 0.0)
    R_th = float(params.get("thermal_resistance_K_per_mW", 0.5) or 0.5)

    if "power_mW" in params and params["power_mW"] is not None:
        power_mW = float(params["power_mW"])
        delta_T_K = power_mW * R_th
    else:
        delta_T_K = float(params.get("delta_T_K", 0.0) or 0.0)

    wl = float(wavelength_nm if wavelength_nm is not None else 1550.0)
    phi = heater_phase_shift(delta_T_K, length_um, wavelength_nm=wl, material=material)
    eta = _eta_from_loss_db(il_db)
    amp = math.sqrt(eta)
    t = amp * complex(math.cos(phi), math.sin(phi))
    return np.array([[t]], dtype=np.complex128)


# ---------------------------------------------------------------------------
# Scattering matrix
# ---------------------------------------------------------------------------


def heater_scattering_matrix(
    params: dict, wavelength_nm: float | None = None,
) -> np.ndarray:
    """2x2 scattering matrix for the heater (reciprocal, no reflections).

    Port order: [in, out].
    """
    fwd = heater_forward_matrix(params, wavelength_nm)
    t = fwd[0, 0]
    s = np.zeros((2, 2), dtype=np.complex128)
    s[1, 0] = t  # S21 (forward)
    s[0, 1] = t  # S12 (reciprocal)
    return s


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class HeaterParams(BaseModel):
    power_mW: float = Field(0.0, ge=0.0, description="Electrical drive power in mW")
    length_um: float = Field(100.0, gt=0.0, description="Heater length in um")
    material: str = Field("Si", description="Waveguide platform material (Si, SiN, SiO2)")
    insertion_loss_db: float = Field(0.1, ge=0.0, description="Excess insertion loss in dB")
    thermal_resistance_K_per_mW: float = Field(0.5, gt=0.0, description="Thermal resistance in K/mW")
    delta_T_K: float | None = Field(None, ge=0.0, description="Direct temperature rise in K (alternative to power_mW)")


class HeaterComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.heater", title="Thermo-Optic Phase Shifter",
            description="Resistive heater for thermo-optic phase tuning",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return HeaterParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return heater_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return heater_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        return cls.meta().in_ports, cls.meta().out_ports
