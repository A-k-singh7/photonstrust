"""Ge-on-Si waveguide photodetector component models.

Models germanium-on-silicon PIN photodetectors for integrated photonic receivers,
including responsivity, dark current, bandwidth (transit-time and RC-limited),
and noise-equivalent power.

References:
    J. Michel, J. Liu, and L. C. Kimerling, "High-performance Ge-on-Si
    photodetectors," Nature Photon., vol. 4, pp. 527-534, 2010.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

Q_E = 1.602e-19  # C  (elementary charge)
H_PLANCK = 6.626e-34  # J*s  (Planck constant)
C_LIGHT = 2.998e8  # m/s  (speed of light)
EPSILON_GE = 16.0 * 8.854e-12  # F/m  (germanium permittivity)
V_SAT_GE = 6e4  # m/s  (carrier saturation velocity in Ge)
K_B = 1.381e-23  # J/K  (Boltzmann constant)

# ---------------------------------------------------------------------------
# Port definitions
# ---------------------------------------------------------------------------

PD_PORTS = ComponentPorts(in_ports=("in",), out_ports=("out",))

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhotodetectorResult:
    """Aggregated photodetector performance metrics."""

    responsivity_A_per_W: float
    dark_current_nA: float
    bandwidth_3dB_GHz: float
    nep_W_per_rtHz: float
    quantum_efficiency: float


# ---------------------------------------------------------------------------
# Responsivity
# ---------------------------------------------------------------------------


def ge_responsivity(
    wavelength_nm: float,
    eta_coupling: float = 0.9,
    alpha_per_cm: float = 5000.0,
    length_um: float = 20.0,
    confinement_factor: float = 0.8,
    eta_collection: float = 0.95,
) -> float:
    """External responsivity of a Ge-on-Si waveguide photodetector (A/W).

    Parameters
    ----------
    wavelength_nm : float
        Operating wavelength (nm).
    eta_coupling : float
        Coupling efficiency from waveguide to absorber.
    alpha_per_cm : float
        Absorption coefficient of Ge at the operating wavelength (cm^-1).
    length_um : float
        Absorber length (um).
    confinement_factor : float
        Optical confinement factor in the Ge layer.
    eta_collection : float
        Carrier collection efficiency.

    Returns
    -------
    float
        Responsivity in A/W.
    """
    alpha_m = float(alpha_per_cm) * 100.0  # cm^-1 -> m^-1
    L_m = float(length_um) * 1e-6  # um -> m
    lam_m = float(wavelength_nm) * 1e-9  # nm -> m

    eta_abs = 1.0 - math.exp(-float(confinement_factor) * alpha_m * L_m)
    eta_ext = float(eta_coupling) * eta_abs * float(eta_collection)

    R = eta_ext * Q_E * lam_m / (H_PLANCK * C_LIGHT)
    return R


# ---------------------------------------------------------------------------
# Dark current
# ---------------------------------------------------------------------------


def ge_dark_current(
    J_dark_mA_per_cm2: float = 10.0,
    width_um: float = 5.0,
    length_um: float = 20.0,
) -> float:
    """Room-temperature dark current of a Ge PD (nA).

    Parameters
    ----------
    J_dark_mA_per_cm2 : float
        Dark-current density (mA/cm^2).
    width_um : float
        Detector width (um).
    length_um : float
        Detector length (um).

    Returns
    -------
    float
        Dark current in nA.
    """
    A_cm2 = (float(width_um) * 1e-4) * (float(length_um) * 1e-4)  # um^2 -> cm^2
    I_mA = float(J_dark_mA_per_cm2) * A_cm2
    return I_mA * 1e6  # mA -> nA


def ge_dark_current_temperature(
    I_dark_ref_nA: float,
    T_K: float,
    T_ref_K: float = 300.0,
    E_g_eV: float = 0.66,
) -> float:
    """Temperature-dependent dark current scaling (nA).

    Uses the standard Ge diode dark-current model:
        I(T) = I_ref * (T/T_ref)^2 * exp(-E_g/(2*k_B) * (1/T - 1/T_ref))

    Parameters
    ----------
    I_dark_ref_nA : float
        Reference dark current at T_ref (nA).
    T_K : float
        Target temperature (K).
    T_ref_K : float
        Reference temperature (K). Default 300 K.
    E_g_eV : float
        Germanium bandgap energy (eV). Default 0.66 eV.

    Returns
    -------
    float
        Dark current at T_K in nA.
    """
    T = float(T_K)
    T_ref = float(T_ref_K)
    E_g_J = float(E_g_eV) * Q_E  # eV -> J

    ratio = (T / T_ref) ** 2 * math.exp(-E_g_J / (2.0 * K_B) * (1.0 / T - 1.0 / T_ref))
    return float(I_dark_ref_nA) * ratio


# ---------------------------------------------------------------------------
# Bandwidth
# ---------------------------------------------------------------------------


def ge_bandwidth(
    depletion_width_um: float = 0.5,
    area_um2: float = 100.0,
    R_series_ohm: float = 10.0,
    R_load_ohm: float = 50.0,
    C_parasitic_fF: float = 10.0,
) -> float:
    """Combined transit-time and RC-limited 3-dB bandwidth (GHz).

    Parameters
    ----------
    depletion_width_um : float
        Intrinsic (depletion) region width (um).
    area_um2 : float
        Junction area (um^2).
    R_series_ohm : float
        Series resistance (ohm).
    R_load_ohm : float
        Load resistance (ohm).
    C_parasitic_fF : float
        Parasitic capacitance (fF).

    Returns
    -------
    float
        3-dB bandwidth in GHz.
    """
    w_i = float(depletion_width_um) * 1e-6  # um -> m
    A_m2 = float(area_um2) * 1e-12  # um^2 -> m^2

    # Transit-time-limited bandwidth
    if w_i > 0:
        f_tr = 0.45 * V_SAT_GE / w_i  # Hz
    else:
        f_tr = float("inf")

    # RC-limited bandwidth
    if w_i > 0:
        C_junction = EPSILON_GE * A_m2 / w_i  # F
    else:
        C_junction = 0.0
    C_parasitic_F = float(C_parasitic_fF) * 1e-15  # fF -> F
    C_total = C_junction + C_parasitic_F
    R_total = float(R_series_ohm) + float(R_load_ohm)

    if C_total > 0 and R_total > 0:
        f_RC = 1.0 / (2.0 * math.pi * R_total * C_total)  # Hz
    else:
        f_RC = float("inf")

    # Combined bandwidth
    if f_tr == float("inf") and f_RC == float("inf"):
        return 0.0
    f_3dB = 1.0 / math.sqrt(1.0 / f_tr ** 2 + 1.0 / f_RC ** 2)

    return f_3dB * 1e-9  # Hz -> GHz


# ---------------------------------------------------------------------------
# Noise-equivalent power
# ---------------------------------------------------------------------------


def ge_nep(dark_current_A: float, responsivity_A_per_W: float) -> float:
    """Noise-equivalent power (W/sqrt(Hz)).

    Shot-noise-limited NEP from dark current.

    Parameters
    ----------
    dark_current_A : float
        Dark current (A).
    responsivity_A_per_W : float
        Responsivity (A/W).

    Returns
    -------
    float
        NEP in W/sqrt(Hz).
    """
    if responsivity_A_per_W <= 0:
        return float("inf")
    return math.sqrt(2.0 * Q_E * abs(float(dark_current_A))) / float(responsivity_A_per_W)


# ---------------------------------------------------------------------------
# Aggregate response
# ---------------------------------------------------------------------------


def photodetector_response(params: dict, wavelength_nm: float | None = None) -> PhotodetectorResult:
    """Assemble full photodetector characterisation from parameters.

    Parameters (via *params* dict)
    ----------
    wavelength_nm : float
        Operating wavelength (nm). Can also be passed as a keyword.
    eta_coupling, alpha_per_cm, length_um, confinement_factor, eta_collection :
        See ``ge_responsivity``.
    J_dark_mA_per_cm2, width_um :
        See ``ge_dark_current``.
    depletion_width_um, R_series_ohm, R_load_ohm, C_parasitic_fF :
        See ``ge_bandwidth``.
    """
    wl = wavelength_nm if wavelength_nm is not None else float(params.get("wavelength_nm", 1550.0))
    length_um = float(params.get("length_um", 20.0))
    width_um = float(params.get("width_um", 5.0))

    R = ge_responsivity(
        wavelength_nm=wl,
        eta_coupling=float(params.get("eta_coupling", 0.9)),
        alpha_per_cm=float(params.get("alpha_per_cm", 5000.0)),
        length_um=length_um,
        confinement_factor=float(params.get("confinement_factor", 0.8)),
        eta_collection=float(params.get("eta_collection", 0.95)),
    )

    I_dark_nA = ge_dark_current(
        J_dark_mA_per_cm2=float(params.get("J_dark_mA_per_cm2", 10.0)),
        width_um=width_um,
        length_um=length_um,
    )

    area_um2 = width_um * length_um
    bw = ge_bandwidth(
        depletion_width_um=float(params.get("depletion_width_um", 0.5)),
        area_um2=area_um2,
        R_series_ohm=float(params.get("R_series_ohm", 10.0)),
        R_load_ohm=float(params.get("R_load_ohm", 50.0)),
        C_parasitic_fF=float(params.get("C_parasitic_fF", 10.0)),
    )

    I_dark_A = I_dark_nA * 1e-9
    nep = ge_nep(I_dark_A, R)

    # Quantum efficiency
    lam_m = wl * 1e-9
    eta_q = R * H_PLANCK * C_LIGHT / (Q_E * lam_m) if lam_m > 0 else 0.0

    return PhotodetectorResult(
        responsivity_A_per_W=R,
        dark_current_nA=I_dark_nA,
        bandwidth_3dB_GHz=bw,
        nep_W_per_rtHz=nep,
        quantum_efficiency=eta_q,
    )


# ---------------------------------------------------------------------------
# Matrix models for circuit simulation
# ---------------------------------------------------------------------------


def photodetector_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward (1,1) matrix representing optical absorption.

    The transmitted optical field is attenuated by the absorber.
    Returns shape (1, 1).
    """
    wl = wavelength_nm if wavelength_nm is not None else float(params.get("wavelength_nm", 1550.0))
    alpha_per_cm = float(params.get("alpha_per_cm", 5000.0))
    length_um = float(params.get("length_um", 20.0))
    confinement_factor = float(params.get("confinement_factor", 0.8))

    alpha_m = alpha_per_cm * 100.0  # cm^-1 -> m^-1
    L_m = length_um * 1e-6  # um -> m

    # Field transmission through the absorber
    t_field = math.exp(-0.5 * confinement_factor * alpha_m * L_m)
    return np.array([[complex(t_field, 0.0)]], dtype=np.complex128)


def photodetector_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """2x2 scattering matrix for the photodetector.

    Port order: [in, out]. Reciprocal, no reflections.
    """
    fwd = photodetector_forward_matrix(params, wavelength_nm)
    t = fwd[0, 0]

    s = np.zeros((2, 2), dtype=np.complex128)
    s[1, 0] = t  # S21
    s[0, 1] = t  # S12 (reciprocal)
    return s


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class PhotodetectorParams(BaseModel):
    wavelength_nm: float = Field(1550.0, gt=0.0, description="Operating wavelength in nm")
    length_um: float = Field(20.0, gt=0.0, description="Absorber length in um")
    eta_coupling: float = Field(0.9, ge=0.0, le=1.0, description="Waveguide-to-absorber coupling efficiency")
    alpha_per_cm: float = Field(5000.0, ge=0.0, description="Ge absorption coefficient in cm^-1")
    confinement_factor: float = Field(0.8, ge=0.0, le=1.0, description="Optical confinement factor in Ge")
    eta_collection: float = Field(0.95, ge=0.0, le=1.0, description="Carrier collection efficiency")
    width_um: float = Field(5.0, gt=0.0, description="Detector width in um")
    J_dark_mA_per_cm2: float = Field(10.0, ge=0.0, description="Dark-current density in mA/cm^2")


class PhotodetectorComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.photodetector", title="Ge-on-Si Photodetector",
            description="Germanium waveguide photodetector for integrated receivers",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return PhotodetectorParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return photodetector_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return photodetector_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        return cls.meta().in_ports, cls.meta().out_ports
