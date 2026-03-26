"""Spot-size converter (SSC) / edge coupler with inverse taper.

Models the mode-field expansion of a sub-wavelength inverse taper and the
Gaussian overlap integral with a single-mode fibre.

References:
    D. Marcuse, "Loss analysis of single-mode fiber splices,"
    Bell Syst. Tech. J., vol. 56, no. 5, pp. 703-718, 1977.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Port definition
# ---------------------------------------------------------------------------

SSC_PORTS = ComponentPorts(in_ports=("in",), out_ports=("out",))

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SSCResult:
    """Summary of SSC performance."""

    coupling_loss_db: float
    coupling_efficiency: float
    mfd_waveguide_um: float
    mfd_fiber_um: float
    alignment_tolerance_1dB_um: float


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _eta_from_loss_db(loss_db: float) -> float:
    return 10.0 ** (-max(0.0, float(loss_db)) / 10.0)


# ---------------------------------------------------------------------------
# Physics functions
# ---------------------------------------------------------------------------


def gaussian_overlap_efficiency(
    mfd_1_um: float,
    mfd_2_um: float,
    offset_um: float = 0.0,
) -> float:
    """Overlap integral of two Gaussian mode fields.

    Returns the power coupling efficiency eta in [0, 1].
    """
    w1 = mfd_1_um / 2.0  # mode radius
    w2 = mfd_2_um / 2.0
    w1_sq = w1 * w1
    w2_sq = w2 * w2
    denom = w1_sq + w2_sq
    if denom < 1e-30:
        return 0.0
    eta = (2.0 * w1 * w2 / denom) ** 2 * math.exp(-2.0 * offset_um ** 2 / denom)
    return eta


def inverse_taper_mfd(
    tip_width_nm: float,
    core_thickness_nm: float = 220.0,
    wavelength_nm: float = 1550.0,
    n_core: float = 3.48,
    n_clad: float = 1.44,
) -> float:
    """Approximate mode-field diameter (um) of an inverse taper tip.

    Uses the Marcuse approximation for weakly-guiding waveguides.
    For very narrow tips (V < 0.8) the mode expands significantly.
    """
    w_tip_um = tip_width_nm / 1000.0  # nm -> um
    lambda_um = wavelength_nm / 1000.0
    NA = math.sqrt(n_core ** 2 - n_clad ** 2)
    V = (math.pi * w_tip_um / lambda_um) * NA

    if V < 1e-12:
        # Degenerate case: essentially no core
        return 100.0  # cap at a large MFD

    # Marcuse approximation for MFD of the fundamental mode
    # MFD = w_tip * (0.65 + 1.619 / V^1.5 + 2.879 / V^6)
    marcuse_factor = 0.65 + 1.619 / V ** 1.5 + 2.879 / V ** 6
    mfd = w_tip_um * marcuse_factor
    return mfd


def ssc_coupling_loss_db(
    tip_width_nm: float,
    fiber_mfd_um: float = 10.4,
    offset_um: float = 0.0,
    core_thickness_nm: float = 220.0,
    wavelength_nm: float = 1550.0,
) -> float:
    """Coupling loss (dB) of the SSC to a fibre.

    Positive values indicate loss.
    """
    taper_mfd = inverse_taper_mfd(
        tip_width_nm,
        core_thickness_nm=core_thickness_nm,
        wavelength_nm=wavelength_nm,
    )
    eta = gaussian_overlap_efficiency(taper_mfd, fiber_mfd_um, offset_um=offset_um)
    if eta < 1e-30:
        return 100.0  # cap
    return -10.0 * math.log10(eta)


def ssc_alignment_tolerance(
    tip_width_nm: float,
    fiber_mfd_um: float = 10.4,
    target_loss_increase_dB: float = 1.0,
) -> float:
    """Lateral alignment tolerance (um) for a given excess-loss budget.

    Returns the offset at which coupling loss increases by
    *target_loss_increase_dB* compared to perfect alignment.
    Uses binary search.
    """
    loss_0 = ssc_coupling_loss_db(tip_width_nm, fiber_mfd_um=fiber_mfd_um, offset_um=0.0)
    target_loss = loss_0 + target_loss_increase_dB

    lo, hi = 0.0, 50.0  # um search range
    for _ in range(60):
        mid = (lo + hi) / 2.0
        loss_mid = ssc_coupling_loss_db(tip_width_nm, fiber_mfd_um=fiber_mfd_um, offset_um=mid)
        if loss_mid < target_loss:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# ---------------------------------------------------------------------------
# Forward matrix
# ---------------------------------------------------------------------------


def ssc_forward_matrix(
    params: dict, wavelength_nm: float | None = None,
) -> np.ndarray:
    """Forward (1,1) transfer matrix for the SSC.

    Parameters (in *params* dict)
    ----------
    coupling_loss_db : float, optional
        Direct specification of coupling loss.  If absent, computed from
        *tip_width_nm* and *fiber_mfd_um*.
    tip_width_nm : float
        Inverse taper tip width (used when coupling_loss_db is not given).
    fiber_mfd_um : float
        Fibre mode-field diameter (default 10.4 um).
    insertion_loss_db : float
        Additional insertion loss (default 0.0 dB).
    """
    wl = float(wavelength_nm if wavelength_nm is not None else 1550.0)

    if "coupling_loss_db" in params and params["coupling_loss_db"] is not None:
        c_loss_db = float(params["coupling_loss_db"])
    else:
        tip_width_nm_val = float(params.get("tip_width_nm", 200.0) or 200.0)
        fiber_mfd = float(params.get("fiber_mfd_um", 10.4) or 10.4)
        c_loss_db = ssc_coupling_loss_db(
            tip_width_nm_val, fiber_mfd_um=fiber_mfd, wavelength_nm=wl,
        )

    il_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    total_loss_db = c_loss_db + il_db
    eta = _eta_from_loss_db(total_loss_db)
    t = complex(math.sqrt(eta), 0.0)
    return np.array([[t]], dtype=np.complex128)


# ---------------------------------------------------------------------------
# Scattering matrix
# ---------------------------------------------------------------------------


def ssc_scattering_matrix(
    params: dict, wavelength_nm: float | None = None,
) -> np.ndarray:
    """2x2 scattering matrix for the SSC (reciprocal, no reflections).

    Port order: [in, out].
    """
    fwd = ssc_forward_matrix(params, wavelength_nm)
    t = fwd[0, 0]
    s = np.zeros((2, 2), dtype=np.complex128)
    s[1, 0] = t  # S21
    s[0, 1] = t  # S12
    return s


# ---------------------------------------------------------------------------
# Response summary
# ---------------------------------------------------------------------------


def ssc_response(
    params: dict, wavelength_nm: float = 1550.0,
) -> SSCResult:
    """Compute a full SSC characterisation summary."""
    tip_width_nm_val = float(params.get("tip_width_nm", 200.0) or 200.0)
    fiber_mfd = float(params.get("fiber_mfd_um", 10.4) or 10.4)

    mfd_wg = inverse_taper_mfd(tip_width_nm_val, wavelength_nm=wavelength_nm)
    eta = gaussian_overlap_efficiency(mfd_wg, fiber_mfd)
    c_loss = -10.0 * math.log10(max(eta, 1e-30))
    tol = ssc_alignment_tolerance(tip_width_nm_val, fiber_mfd_um=fiber_mfd)

    return SSCResult(
        coupling_loss_db=c_loss,
        coupling_efficiency=eta,
        mfd_waveguide_um=mfd_wg,
        mfd_fiber_um=fiber_mfd,
        alignment_tolerance_1dB_um=tol,
    )


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class SSCParams(BaseModel):
    tip_width_nm: float = Field(200.0, gt=0.0, le=500.0, description="Inverse taper tip width in nm")
    fiber_mfd_um: float = Field(10.4, gt=0.0, description="Fibre mode-field diameter in um")
    core_thickness_nm: float = Field(220.0, gt=0.0, description="Waveguide core thickness in nm")
    insertion_loss_db: float = Field(0.0, ge=0.0, description="Additional insertion loss in dB")
    coupling_loss_db: float | None = Field(None, ge=0.0, description="Direct coupling loss override in dB")


class SSCComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.ssc", title="Spot-Size Converter",
            description="Inverse-taper edge coupler for fibre-to-chip coupling",
            in_ports=("in",), out_ports=("out",),
            port_domains={"in": "optical", "out": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return SSCParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return ssc_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return ssc_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        return cls.meta().in_ports, cls.meta().out_ports
