"""Arrayed waveguide grating (AWG) demultiplexer component models.

Models N-channel AWG demultiplexers with Gaussian passband response, including
free spectral range, diffraction order, insertion loss, and crosstalk analysis.

References:
    M. K. Smit and C. Van Dam, "PHASAR-based WDM-devices: Principles, design
    and applications," IEEE J. Sel. Top. Quantum Electron., vol. 2, no. 2,
    pp. 236-250, Jun. 1996.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AWGResult:
    """Aggregated AWG performance metrics."""

    center_wavelength_nm: float
    fsr_nm: float
    channel_spacing_nm: float
    n_channels: int
    insertion_loss_db: float
    adjacent_crosstalk_db: float
    passband_3dB_nm: float
    diffraction_order: int


# ---------------------------------------------------------------------------
# Core AWG functions
# ---------------------------------------------------------------------------


def awg_fsr(
    center_wavelength_nm: float,
    group_index: float,
    delta_L_um: float,
) -> float:
    """Free spectral range of an AWG (nm).

    FSR = lambda_c^2 / (n_g * delta_L)

    Parameters
    ----------
    center_wavelength_nm : float
        Center wavelength (nm).
    group_index : float
        Group index of the arrayed waveguides.
    delta_L_um : float
        Path-length increment between adjacent arrayed waveguides (um).

    Returns
    -------
    float
        FSR in nm.
    """
    lam_nm = float(center_wavelength_nm)
    n_g = float(group_index)
    dL_nm = float(delta_L_um) * 1e3  # um -> nm

    if n_g <= 0 or dL_nm <= 0:
        return 0.0

    return lam_nm ** 2 / (n_g * dL_nm)


def awg_diffraction_order(
    center_wavelength_nm: float,
    n_eff: float,
    delta_L_um: float,
) -> int:
    """Diffraction order of the AWG.

    m = round(n_eff * delta_L / lambda_c)

    Parameters
    ----------
    center_wavelength_nm : float
        Center wavelength (nm).
    n_eff : float
        Effective index of the arrayed waveguides.
    delta_L_um : float
        Path-length increment (um).

    Returns
    -------
    int
        Diffraction order.
    """
    lam_um = float(center_wavelength_nm) * 1e-3  # nm -> um
    if lam_um <= 0:
        return 0
    return round(float(n_eff) * float(delta_L_um) / lam_um)


def awg_channel_spacing(fsr_nm: float, n_channels: int) -> float:
    """Channel spacing for uniform channel plan (nm).

    delta_lambda = FSR / N_ch

    Parameters
    ----------
    fsr_nm : float
        Free spectral range (nm).
    n_channels : int
        Number of output channels.

    Returns
    -------
    float
        Channel spacing in nm.
    """
    if int(n_channels) <= 0:
        return 0.0
    return float(fsr_nm) / int(n_channels)


# ---------------------------------------------------------------------------
# Passband and crosstalk
# ---------------------------------------------------------------------------


def awg_gaussian_passband(
    wavelength_nm: float,
    channel_center_nm: float,
    passband_3dB_nm: float,
    peak_transmission: float = 1.0,
) -> float:
    """Gaussian passband response of a single AWG channel.

    T = T0 * exp(-4*ln(2)*((lambda - lambda_k) / delta_lambda_3dB)^2)

    Parameters
    ----------
    wavelength_nm : float
        Evaluation wavelength (nm).
    channel_center_nm : float
        Channel center wavelength (nm).
    passband_3dB_nm : float
        3-dB passband width (nm).
    peak_transmission : float
        Peak transmission (linear). Default 1.0.

    Returns
    -------
    float
        Transmission (linear scale).
    """
    if passband_3dB_nm <= 0:
        return 0.0
    delta = float(wavelength_nm) - float(channel_center_nm)
    exponent = -4.0 * math.log(2.0) * (delta / float(passband_3dB_nm)) ** 2
    return float(peak_transmission) * math.exp(exponent)


def awg_adjacent_crosstalk_db(
    channel_spacing_nm: float,
    passband_3dB_nm: float,
) -> float:
    """Adjacent-channel crosstalk for Gaussian passband (dB, negative).

    XT = -4*ln(2)*(channel_spacing / passband_3dB)^2 * (10/ln(10))

    Parameters
    ----------
    channel_spacing_nm : float
        Channel spacing (nm).
    passband_3dB_nm : float
        3-dB passband width (nm).

    Returns
    -------
    float
        Crosstalk in dB (negative value).
    """
    if passband_3dB_nm <= 0:
        return 0.0
    ratio = float(channel_spacing_nm) / float(passband_3dB_nm)
    return -4.0 * math.log(2.0) * ratio ** 2 * (10.0 / math.log(10.0))


def awg_background_crosstalk_db(
    n_arrayed_wgs: int,
    phase_error_rms_rad: float = 0.05,
) -> float:
    """Background (non-adjacent) crosstalk due to phase errors (dB, negative).

    XT = -10*log10(N_a * (delta_phi_rms / (2*pi))^2)

    Parameters
    ----------
    n_arrayed_wgs : int
        Number of arrayed waveguides.
    phase_error_rms_rad : float
        RMS phase error per waveguide (rad).

    Returns
    -------
    float
        Background crosstalk in dB (negative value, lower is better).
    """
    N_a = int(n_arrayed_wgs)
    dphi = float(phase_error_rms_rad)

    arg = N_a * (dphi / (2.0 * math.pi)) ** 2
    if arg <= 0:
        return -float("inf")
    # Return as a negative dB value (crosstalk level relative to signal)
    return 10.0 * math.log10(arg)


# ---------------------------------------------------------------------------
# Insertion loss
# ---------------------------------------------------------------------------


def awg_insertion_loss_db(
    propagation_loss_db_per_cm: float,
    avg_path_length_cm: float,
    fpr_loss_db: float = 0.5,
    coupling_loss_db: float = 0.3,
) -> float:
    """Total insertion loss of the AWG (dB).

    IL = 2*fpr_loss + alpha*L + coupling_loss

    Parameters
    ----------
    propagation_loss_db_per_cm : float
        Waveguide propagation loss (dB/cm).
    avg_path_length_cm : float
        Average path length through the arrayed waveguides (cm).
    fpr_loss_db : float
        Loss per free-propagation region (dB). Default 0.5.
    coupling_loss_db : float
        Input/output coupling loss (dB). Default 0.3.

    Returns
    -------
    float
        Insertion loss in dB.
    """
    return (
        2.0 * float(fpr_loss_db)
        + float(propagation_loss_db_per_cm) * float(avg_path_length_cm)
        + float(coupling_loss_db)
    )


# ---------------------------------------------------------------------------
# Aggregate channel response
# ---------------------------------------------------------------------------


def awg_channel_response(params: dict, wavelength_nm: float | None = None) -> AWGResult:
    """Compute AWG channel characteristics.

    Parameters (via *params* dict)
    ----------
    n_channels : int
        Number of output channels. Default 8.
    center_wavelength_nm : float
        Center wavelength (nm). Default 1550.
    channel_spacing_nm : float
        Channel spacing (nm). Default 1.6.
    n_eff : float
        Effective index of arrayed WGs. Default 2.44.
    group_index : float
        Group index. Default 4.2.
    delta_L_um : float
        Path-length increment (um). Required; computed from spacing if absent.
    n_arrayed_wgs : int
        Number of arrayed waveguides. Default 40.
    passband_3dB_nm : float
        3-dB passband width (nm). Default 0.5.
    insertion_loss_db : float
        Total insertion loss (dB). Default 2.5.
    phase_error_rms_rad : float
        RMS phase error (rad). Default 0.05.

    Returns
    -------
    AWGResult
    """
    n_ch = int(params.get("n_channels", 8))
    center_wl = float(params.get("center_wavelength_nm", 1550.0))
    ch_spacing = float(params.get("channel_spacing_nm", 1.6))
    n_eff = float(params.get("n_eff", 2.44))
    n_g = float(params.get("group_index", 4.2))
    n_arr = int(params.get("n_arrayed_wgs", 40))
    pb_3dB = float(params.get("passband_3dB_nm", 0.5))
    il_db = float(params.get("insertion_loss_db", 2.5))
    phi_err = float(params.get("phase_error_rms_rad", 0.05))

    # Compute delta_L from channel spacing if not given
    if "delta_L_um" in params and params["delta_L_um"] is not None:
        dL_um = float(params["delta_L_um"])
    else:
        # delta_L = lambda_c^2 / (n_g * N_ch * channel_spacing)
        # where all in consistent units (nm for lambda, nm for spacing)
        ch_spacing_nm = ch_spacing
        fsr_nm = ch_spacing_nm * n_ch
        dL_nm = center_wl ** 2 / (n_g * fsr_nm)
        dL_um = dL_nm * 1e-3  # nm -> um

    fsr = awg_fsr(center_wl, n_g, dL_um)
    diff_order = awg_diffraction_order(center_wl, n_eff, dL_um)
    adj_xt = awg_adjacent_crosstalk_db(ch_spacing, pb_3dB)

    return AWGResult(
        center_wavelength_nm=center_wl,
        fsr_nm=fsr,
        channel_spacing_nm=ch_spacing,
        n_channels=n_ch,
        insertion_loss_db=il_db,
        adjacent_crosstalk_db=adj_xt,
        passband_3dB_nm=pb_3dB,
        diffraction_order=diff_order,
    )


# ---------------------------------------------------------------------------
# Matrix models for circuit simulation
# ---------------------------------------------------------------------------


def awg_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward (N_ch, 1) demultiplexer matrix.

    Each row gives the complex field transmission from the single input port
    to the corresponding output channel at the evaluation wavelength.

    Returns shape (n_channels, 1).
    """
    result = awg_channel_response(params, wavelength_nm)
    n_ch = result.n_channels
    wl = wavelength_nm if wavelength_nm is not None else result.center_wavelength_nm

    # Insertion-loss amplitude factor
    il_amp = 10.0 ** (-result.insertion_loss_db / 20.0)

    m = np.zeros((n_ch, 1), dtype=np.complex128)
    for k in range(n_ch):
        # Channel center wavelength (uniform grid centred on center_wavelength_nm)
        ch_center = result.center_wavelength_nm + (k - (n_ch - 1) / 2.0) * result.channel_spacing_nm
        # Gaussian passband transmission
        T_power = awg_gaussian_passband(wl, ch_center, result.passband_3dB_nm, peak_transmission=1.0)
        t_field = math.sqrt(max(0.0, T_power)) * il_amp
        m[k, 0] = complex(t_field, 0.0)

    return m


def awg_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """(N_ch+1, N_ch+1) scattering matrix for the AWG.

    Port order: [in, out_ch0, out_ch1, ..., out_ch_{N-1}].
    Reciprocal, no reflections.
    """
    fwd = awg_forward_matrix(params, wavelength_nm)  # (N_ch, 1)
    n_ch = fwd.shape[0]
    n_ports = n_ch + 1  # 1 input + N_ch outputs

    s = np.zeros((n_ports, n_ports), dtype=np.complex128)

    # Forward: input (port 0) -> output channels (ports 1..N_ch)
    for k in range(n_ch):
        s[k + 1, 0] = fwd[k, 0]
        s[0, k + 1] = fwd[k, 0]  # reciprocal

    return s


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class AWGParams(BaseModel):
    n_channels: int = Field(8, ge=1, le=128, description="Number of output channels")
    center_wavelength_nm: float = Field(1550.0, gt=0.0, description="Center wavelength in nm")
    channel_spacing_nm: float = Field(1.6, gt=0.0, description="Channel spacing in nm")
    insertion_loss_db: float = Field(2.5, ge=0.0, description="Total insertion loss in dB")
    n_eff: float = Field(2.44, gt=0.0, description="Effective index of arrayed waveguides")
    group_index: float = Field(4.2, gt=0.0, description="Group index of arrayed waveguides")
    n_arrayed_wgs: int = Field(40, ge=1, description="Number of arrayed waveguides")
    passband_3dB_nm: float = Field(0.5, gt=0.0, description="3-dB passband width in nm")
    delta_L_um: float | None = Field(None, gt=0.0, description="Path-length increment in um")
    phase_error_rms_rad: float = Field(0.05, ge=0.0, description="RMS phase error per waveguide in rad")


class AWGComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.awg", title="AWG Demultiplexer",
            description="Arrayed waveguide grating N-channel demultiplexer",
            in_ports=("in",), out_ports=tuple(f"out{i+1}" for i in range(8)),
            port_domains={"in": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return AWGParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return awg_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return awg_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        if params:
            p = cls._as_dict(params)
            n_ch = int(p.get("n_channels", 8))
            out = tuple(f"out{i+1}" for i in range(n_ch))
            return ("in",), out
        return cls.meta().in_ports, cls.meta().out_ports
