"""MMI (multimode interference) coupler component models.

Supports 1x2 and 2x2 MMI couplers based on self-imaging theory.
The forward matrices model unidirectional propagation; scattering matrices
provide bidirectional port-level S-parameters.

References:
    L. B. Soldano and E. C. M. Pennings, "Optical multi-mode interference
    devices based on self-imaging: principles and applications,"
    J. Lightwave Technol., vol. 13, no. 4, pp. 615-627, Apr. 1995.
"""

from __future__ import annotations

import math

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Port definitions
# ---------------------------------------------------------------------------

MMI_1X2_PORTS = ComponentPorts(in_ports=("in",), out_ports=("out1", "out2"))
MMI_2X2_PORTS = ComponentPorts(in_ports=("in1", "in2"), out_ports=("out1", "out2"))


def mmi_ports(params: dict) -> ComponentPorts:
    """Return the correct port definition based on n_ports_in / n_ports_out."""
    n_in = int(params.get("n_ports_in", 1))
    n_out = int(params.get("n_ports_out", 2))
    if n_in == 1 and n_out == 2:
        return MMI_1X2_PORTS
    if n_in == 2 and n_out == 2:
        return MMI_2X2_PORTS
    raise ValueError(f"Unsupported MMI port configuration: {n_in}x{n_out}")


# ---------------------------------------------------------------------------
# Physical helper functions
# ---------------------------------------------------------------------------

def mmi_beat_length(n_eff: float, W_eff: float, wavelength_um: float) -> float:
    """Beat length of the fundamental and first-order modes.

    L_pi = 4 * n_eff * W_eff**2 / (3 * lambda)

    Parameters
    ----------
    n_eff : float
        Effective index of the multimode region.
    W_eff : float
        Effective width of the multimode region (um).
    wavelength_um : float
        Free-space wavelength (um).

    Returns
    -------
    float
        Beat length L_pi in the same unit as *W_eff* and *wavelength_um* (um).
    """
    if wavelength_um <= 0:
        raise ValueError("wavelength_um must be > 0")
    return 4.0 * n_eff * W_eff ** 2 / (3.0 * wavelength_um)


def mmi_effective_width(
    W_mmi: float,
    wavelength_um: float,
    n_core: float,
    n_clad: float,
    polarization: str = "TE",
) -> float:
    """Effective MMI width including Goos-Hanchen penetration depth.

    W_eff = W_MMI + (lambda / pi) * (n_clad / n_core)^(2*sigma)
                    * (n_core^2 - n_clad^2)^(-1/2)

    sigma = 0 for TE, 1 for TM.

    Parameters
    ----------
    W_mmi : float
        Physical width of the multimode region (um).
    wavelength_um : float
        Free-space wavelength (um).
    n_core, n_clad : float
        Core and cladding refractive indices.
    polarization : str
        ``"TE"`` or ``"TM"``.

    Returns
    -------
    float
        Effective width W_eff (um).
    """
    pol = polarization.strip().upper()
    if pol not in ("TE", "TM"):
        raise ValueError(f"polarization must be 'TE' or 'TM', got {polarization!r}")
    sigma = 0 if pol == "TE" else 1
    dn2 = n_core ** 2 - n_clad ** 2
    if dn2 <= 0:
        raise ValueError("n_core must be greater than n_clad")
    penetration = (
        (wavelength_um / math.pi)
        * (n_clad / n_core) ** (2 * sigma)
        / math.sqrt(dn2)
    )
    return W_mmi + penetration


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _eta_from_loss_db(loss_db: float) -> float:
    return 10.0 ** (-max(0.0, float(loss_db)) / 10.0)


def _imbalance_factor(imbalance_db: float) -> float:
    """Convert imbalance in dB to a linear ratio deviation from 0.5.

    A positive imbalance_db means the first output gets slightly more power.
    Returns r such that output powers split as r : (1 - r).
    """
    if imbalance_db == 0.0:
        return 0.5
    # 10*log10(r / (1-r)) = imbalance_db  =>  r/(1-r) = 10^(imb/10)
    ratio = 10.0 ** (float(imbalance_db) / 10.0)
    return ratio / (1.0 + ratio)


# ---------------------------------------------------------------------------
# Forward matrices
# ---------------------------------------------------------------------------

def mmi_1x2_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward matrix for a 1x2 MMI coupler.

    Shape: (2, 1).  M = sqrt(eta) * [[sqrt(r)], [sqrt(1 - r)]]
    where r accounts for any imbalance.
    """
    il_db = float(params.get("insertion_loss_db", 0.3) or 0.0)
    imb_db = float(params.get("imbalance_db", 0.0) or 0.0)

    eta = _eta_from_loss_db(il_db)
    r = _imbalance_factor(imb_db)

    amp = math.sqrt(eta)
    m = np.array(
        [[amp * math.sqrt(r)], [amp * math.sqrt(1.0 - r)]],
        dtype=np.complex128,
    )
    return m


def mmi_2x2_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward matrix for a 2x2 MMI coupler.

    Shape: (2, 2).  M = sqrt(eta)/sqrt(2) * [[1, 1j], [1j, 1]]
    """
    il_db = float(params.get("insertion_loss_db", 0.3) or 0.0)
    eta = _eta_from_loss_db(il_db)
    amp = math.sqrt(eta) / math.sqrt(2.0)
    m = np.array(
        [[amp * 1.0, amp * 1j], [amp * 1j, amp * 1.0]],
        dtype=np.complex128,
    )
    return m


def mmi_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Dispatch to 1x2 or 2x2 based on params."""
    ports = mmi_ports(params)
    if len(ports.in_ports) == 1:
        return mmi_1x2_forward_matrix(params, wavelength_nm)
    return mmi_2x2_forward_matrix(params, wavelength_nm)


# ---------------------------------------------------------------------------
# Scattering matrices
# ---------------------------------------------------------------------------

def mmi_1x2_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """3x3 scattering matrix for a 1x2 MMI.

    Port order: [in, out1, out2].
    Assumes reciprocity: S = S^T.
    """
    fwd = mmi_1x2_forward_matrix(params, wavelength_nm)  # (2,1)

    rl_db = params.get("return_loss_db")
    rl_mag = 0.0
    if rl_db is not None:
        rl_db = float(rl_db)
        if math.isfinite(rl_db):
            rl_mag = 10.0 ** (-rl_db / 20.0)

    s = np.zeros((3, 3), dtype=np.complex128)
    # Reflections on diagonal
    s[0, 0] = rl_mag
    s[1, 1] = rl_mag
    s[2, 2] = rl_mag
    # Forward: in -> out1, out2
    s[1, 0] = fwd[0, 0]
    s[2, 0] = fwd[1, 0]
    # Reciprocal reverse
    s[0, 1] = fwd[0, 0]
    s[0, 2] = fwd[1, 0]
    return s


def mmi_2x2_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """4x4 scattering matrix for a 2x2 MMI.

    Port order: [in1, in2, out1, out2].
    Assumes reciprocity.
    """
    fwd = mmi_2x2_forward_matrix(params, wavelength_nm)  # (2,2)

    s = np.zeros((4, 4), dtype=np.complex128)
    # Forward block: out = fwd @ in  (rows 2-3, cols 0-1)
    s[2:4, 0:2] = fwd
    # Reciprocal reverse block: in = fwd^T @ out  (rows 0-1, cols 2-3)
    s[0:2, 2:4] = fwd.T
    return s


def mmi_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Dispatch to 1x2 or 2x2 scattering matrix."""
    ports = mmi_ports(params)
    if len(ports.in_ports) == 1:
        return mmi_1x2_scattering_matrix(params, wavelength_nm)
    return mmi_2x2_scattering_matrix(params, wavelength_nm)


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class MMIParams(BaseModel):
    n_ports_in: int = Field(1, ge=1, le=2)
    n_ports_out: int = Field(2, ge=2, le=2)
    insertion_loss_db: float = Field(0.3, ge=0.0, description="Excess insertion loss in dB")
    imbalance_db: float = Field(0.0, description="Output power imbalance in dB")
    return_loss_db: float | None = Field(None, ge=0.0, description="Return loss in dB")


class MMIComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.mmi", title="MMI Coupler",
            description="Multimode interference coupler using self-imaging",
            in_ports=("in1", "in2"), out_ports=("out1", "out2"),
            port_domains={"in1": "optical", "in2": "optical", "out1": "optical", "out2": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return MMIParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return mmi_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return mmi_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        if params:
            p = mmi_ports(cls._as_dict(params))
            return p.in_ports, p.out_ports
        return cls.meta().in_ports, cls.meta().out_ports
