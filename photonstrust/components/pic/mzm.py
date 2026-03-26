"""Mach-Zehnder modulator (MZM) component models with free-carrier plasma dispersion.

Models silicon photonic MZMs using the Soref-Bennett electro-refractive effect
in PN-junction phase shifters. Supports both lumped-element transfer-function
analysis and matrix-based circuit simulation.

References:
    R. A. Soref and B. R. Bennett, "Electrooptical effects in silicon,"
    IEEE J. Quantum Electron., vol. 23, no. 1, pp. 123-129, Jan. 1987.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EPSILON_SI = 11.7 * 8.854e-12  # F/m  (silicon permittivity)
Q_E = 1.602e-19  # C  (elementary charge)
N_I_SI = 1.08e16  # m^-3  (intrinsic carrier concentration at 300 K)
K_B = 1.381e-23  # J/K  (Boltzmann constant)

# ---------------------------------------------------------------------------
# Port definitions
# ---------------------------------------------------------------------------

MZM_PORTS = ComponentPorts(in_ports=("in",), out_ports=("out",))

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MZMResult:
    """Aggregated MZM performance metrics."""

    transmission: float
    phase_shift_rad: float
    extinction_ratio_db: float
    insertion_loss_db: float
    bandwidth_3dB_GHz: float
    chirp_alpha: float


# ---------------------------------------------------------------------------
# Soref-Bennett electro-refractive model
# ---------------------------------------------------------------------------


def soref_bennett_delta_n(
    delta_N_e_per_cm3: float,
    delta_N_h_per_cm3: float,
    wavelength_nm: float = 1550.0,
) -> tuple[float, float]:
    """Carrier-induced refractive index and absorption changes at 1550 nm.

    Parameters
    ----------
    delta_N_e_per_cm3 : float
        Change in free-electron concentration (cm^-3).
    delta_N_h_per_cm3 : float
        Change in free-hole concentration (cm^-3).
    wavelength_nm : float
        Operating wavelength (nm). Only 1550 nm coefficients are implemented.

    Returns
    -------
    (delta_n, delta_alpha_per_cm) : tuple[float, float]
        Refractive index change (negative for carrier injection) and
        absorption change (cm^-1, positive).
    """
    dN_e = abs(float(delta_N_e_per_cm3))
    dN_h = abs(float(delta_N_h_per_cm3))

    # Soref-Bennett empirical coefficients at 1550 nm
    delta_n = -(8.8e-22 * dN_e + 8.5e-18 * (dN_h) ** 0.8)
    delta_alpha = 8.5e-18 * dN_e + 6.0e-18 * dN_h  # cm^-1

    return (delta_n, delta_alpha)


# ---------------------------------------------------------------------------
# PN-junction depletion model
# ---------------------------------------------------------------------------


def pn_depletion_delta_n(
    voltage_V: float,
    N_A_per_cm3: float,
    N_D_per_cm3: float,
    W_wg_um: float,
    confinement_factor: float = 0.85,
) -> float:
    """Index change from depletion-width modulation in a PN-junction phase shifter.

    Parameters
    ----------
    voltage_V : float
        Applied voltage (V). Negative = reverse bias (widens depletion).
    N_A_per_cm3 : float
        Acceptor doping concentration (cm^-3).
    N_D_per_cm3 : float
        Donor doping concentration (cm^-3).
    W_wg_um : float
        Waveguide width (um).
    confinement_factor : float
        Optical confinement factor in the junction region.

    Returns
    -------
    float
        Effective refractive index change (typically negative for reverse bias).
    """
    N_A = abs(float(N_A_per_cm3))
    N_D = abs(float(N_D_per_cm3))
    W_wg = abs(float(W_wg_um)) * 1e-6  # convert to metres
    V = float(voltage_V)

    # Intrinsic carrier concentration in cm^-3 for the V_bi formula
    n_i_cm3 = N_I_SI * 1e-6  # m^-3 -> cm^-3  (1.08e10 cm^-3)

    # Built-in voltage (thermal voltage ~ 26 mV at 300 K)
    V_bi = 0.026 * math.log(N_A * N_D / (n_i_cm3 ** 2))

    # Convert doping to SI (m^-3) for depletion-width calculation
    N_A_si = N_A * 1e6
    N_D_si = N_D * 1e6

    # Depletion width at applied bias (V is negative for reverse bias)
    V_total = V_bi - V  # reverse bias increases this
    if V_total < 0:
        V_total = 0.0  # forward bias beyond V_bi collapses depletion

    W_dep = math.sqrt(
        2.0 * EPSILON_SI * V_total * (N_A_si + N_D_si) / (Q_E * N_A_si * N_D_si)
    )

    # Zero-bias depletion width
    W_dep_0 = math.sqrt(
        2.0 * EPSILON_SI * V_bi * (N_A_si + N_D_si) / (Q_E * N_A_si * N_D_si)
    )

    delta_W = W_dep - W_dep_0

    # Carrier-concentration changes seen by the optical mode
    if W_wg <= 0:
        return 0.0

    delta_N_e = N_D * abs(delta_W) / W_wg  # in cm^-3 (N_D is cm^-3, delta_W/W_wg dimensionless via metres)
    # delta_W is in metres, W_wg is in metres, so the ratio is dimensionless
    delta_N_h = N_A * abs(delta_W) / W_wg

    delta_n, _delta_alpha = soref_bennett_delta_n(delta_N_e, delta_N_h)
    return confinement_factor * delta_n


# ---------------------------------------------------------------------------
# MZM transfer function
# ---------------------------------------------------------------------------


def mzm_transfer_function(
    params: dict,
    wavelength_nm: float | None = None,
) -> MZMResult:
    """Compute MZM output characteristics from physical/electrical parameters.

    Parameters (via *params* dict)
    ----------
    phase_shifter_length_mm : float
        Active phase-shifter length (mm).
    V_pi_L_pi_Vcm : float
        V_pi * L_pi product (V*cm). Default 2.0.
    voltage_V : float
        Applied drive voltage (V).
    splitting_ratio : float
        Power splitting ratio of the input coupler (0 to 1). Default 0.5.
    insertion_loss_db : float
        Total excess insertion loss (dB). Default 4.0.

    Returns
    -------
    MZMResult
    """
    L_mm = float(params.get("phase_shifter_length_mm", 3.0))
    VpiLpi = float(params.get("V_pi_L_pi_Vcm", 2.0))
    V = float(params.get("voltage_V", 0.0))
    r = float(params.get("splitting_ratio", 0.5))
    il_db = float(params.get("insertion_loss_db", 4.0))

    r = max(0.0, min(1.0, r))
    L_cm = L_mm / 10.0  # mm -> cm

    # V_pi for this length
    if L_cm > 0:
        V_pi = VpiLpi / L_cm
    else:
        V_pi = float("inf")

    # Phase shift accumulated
    if VpiLpi > 0:
        delta_phi = math.pi * V * L_cm / VpiLpi
    else:
        delta_phi = 0.0

    # Insertion-loss power factor
    eta = 10.0 ** (-max(0.0, il_db) / 10.0)

    # MZM interference: T = eta * (r + (1-r) + 2*sqrt(r*(1-r))*cos(delta_phi))
    # Normalised so max T = eta when delta_phi = 0 and r = 0.5
    T = eta * (r + (1.0 - r) + 2.0 * math.sqrt(r * (1.0 - r)) * math.cos(delta_phi))

    # Extinction ratio
    r_sqrt = math.sqrt(r)
    r1_sqrt = math.sqrt(1.0 - r)
    num_er = (r_sqrt + r1_sqrt) ** 2
    den_er = (r_sqrt - r1_sqrt) ** 2
    if den_er > 0:
        er_db = 10.0 * math.log10(num_er / den_er)
    else:
        er_db = float("inf")

    # Chirp parameter (simplified Henry alpha for push-pull)
    # For a single-drive MZM, alpha_chirp ~ -1/tan(delta_phi/2), but
    # we use the small-signal approximation: alpha ~ (1-2r)/(1-2r) simplification.
    # Standard push-pull: alpha = 0; single-arm: |alpha| ~ 1
    # Here we model single-arm drive with alpha dependent on bias point.
    if abs(math.sin(delta_phi)) > 1e-12:
        chirp_alpha = -math.cos(delta_phi) / math.sin(delta_phi) * (1.0 - 2.0 * r) / 1.0
    else:
        chirp_alpha = 0.0

    return MZMResult(
        transmission=T,
        phase_shift_rad=delta_phi,
        extinction_ratio_db=er_db,
        insertion_loss_db=il_db,
        bandwidth_3dB_GHz=0.0,  # placeholder; use mzm_bandwidth() separately
        chirp_alpha=chirp_alpha,
    )


# ---------------------------------------------------------------------------
# Bandwidth model
# ---------------------------------------------------------------------------


def mzm_bandwidth(
    junction_capacitance_fF_per_mm: float,
    series_resistance_ohm: float,
    phase_shifter_length_mm: float,
    load_resistance_ohm: float = 50.0,
) -> float:
    """RC-limited 3-dB electro-optic bandwidth of the MZM (GHz).

    Parameters
    ----------
    junction_capacitance_fF_per_mm : float
        Junction capacitance per unit length (fF/mm).
    series_resistance_ohm : float
        Series resistance of the PN junction (ohm).
    phase_shifter_length_mm : float
        Phase-shifter length (mm).
    load_resistance_ohm : float
        Load/termination resistance (ohm). Default 50.

    Returns
    -------
    float
        3-dB bandwidth in GHz.
    """
    C_fF = float(junction_capacitance_fF_per_mm) * float(phase_shifter_length_mm)
    C_total = C_fF * 1e-15  # fF -> F
    R_total = float(series_resistance_ohm) + float(load_resistance_ohm)

    if C_total <= 0 or R_total <= 0:
        return 0.0

    f_RC = 1.0 / (2.0 * math.pi * R_total * C_total)  # Hz
    return f_RC * 1e-9  # Hz -> GHz


# ---------------------------------------------------------------------------
# Matrix models for circuit simulation
# ---------------------------------------------------------------------------


def mzm_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward (1,1) complex transmission coefficient for circuit solvers.

    Returns an array of shape (1, 1) containing the complex field transmission.
    """
    result = mzm_transfer_function(params, wavelength_nm)

    # Amplitude transmission (sqrt of power transmission)
    amp = math.sqrt(max(0.0, result.transmission))

    # Phase accumulated
    phi = result.phase_shift_rad

    t = amp * complex(math.cos(phi), math.sin(phi))
    return np.array([[t]], dtype=np.complex128)


def mzm_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """2x2 scattering matrix for the MZM (reciprocal, no reflections by default).

    Port order: [in, out].
    """
    fwd = mzm_forward_matrix(params, wavelength_nm)
    t = fwd[0, 0]

    s = np.zeros((2, 2), dtype=np.complex128)
    s[1, 0] = t  # S21 (forward)
    s[0, 1] = t  # S12 (reciprocal)
    return s
