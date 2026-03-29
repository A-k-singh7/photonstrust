"""Waveguide crossing component model.

A 4-port device with two waveguides that intersect.  Ideally all power
continues straight through (the *through* path) with negligible coupling
to the perpendicular waveguide (the *cross* or *crosstalk* path).

Port convention:
    in1 -> out1  (through path 1)
    in2 -> out2  (through path 2)
    in1 -> out2  (crosstalk)
    in2 -> out1  (crosstalk)
"""

from __future__ import annotations

import math

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Port definition
# ---------------------------------------------------------------------------

CROSSING_PORTS = ComponentPorts(in_ports=("in1", "in2"), out_ports=("out1", "out2"))


def crossing_ports() -> ComponentPorts:
    """Return the port definition for a waveguide crossing."""
    return CROSSING_PORTS


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _eta_from_loss_db(loss_db: float) -> float:
    return 10.0 ** (-max(0.0, float(loss_db)) / 10.0)


# ---------------------------------------------------------------------------
# Forward matrix
# ---------------------------------------------------------------------------

def crossing_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward matrix for a waveguide crossing.

    Shape: (2, 2).

    Through-path amplitude: sqrt(eta_through) * exp(j * phi)
    Cross-path amplitude:   sqrt(eta_xt) * exp(j * phi_xt)

    where:
        eta_through = 10^(-IL_dB / 10)
        eta_xt      = 10^(XT_dB / 10)     (XT_dB is negative, e.g. -40)

    Parameters (in *params* dict)
    ----------
    insertion_loss_db : float
        Through-path insertion loss in dB (default 0.02).
    crosstalk_db : float
        Crosstalk coupling in dB, negative (default -40.0).
    """
    il_db = float(params.get("insertion_loss_db", 0.02) or 0.0)
    xt_db = float(params.get("crosstalk_db", -40.0) if params.get("crosstalk_db") is not None else -40.0)

    eta_through = _eta_from_loss_db(il_db)
    # Crosstalk: xt_db is negative, so 10^(xt_db/10) gives a small number
    eta_xt = 10.0 ** (float(xt_db) / 10.0)

    phi = float(params.get("phase_rad", 0.0) or 0.0)
    phi_xt = float(params.get("phase_xt_rad", 0.0) or 0.0)

    t_through = math.sqrt(eta_through) * complex(math.cos(phi), math.sin(phi))
    t_xt = math.sqrt(eta_xt) * complex(math.cos(phi_xt), math.sin(phi_xt))

    m = np.array(
        [[t_through, t_xt], [t_xt, t_through]],
        dtype=np.complex128,
    )
    return m


# ---------------------------------------------------------------------------
# Scattering matrix
# ---------------------------------------------------------------------------

def crossing_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """4x4 scattering matrix for a waveguide crossing.

    Port order: [in1, in2, out1, out2].
    Assumes reciprocity.
    """
    fwd = crossing_forward_matrix(params, wavelength_nm)  # (2,2)

    s = np.zeros((4, 4), dtype=np.complex128)
    # Forward block: b_out = fwd @ a_in  (rows 2-3, cols 0-1)
    s[2:4, 0:2] = fwd
    # Reciprocal reverse block: b_in = fwd^T @ a_out  (rows 0-1, cols 2-3)
    s[0:2, 2:4] = fwd.T
    return s


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def cumulative_crossing_loss_db(n_crossings: int, loss_per_crossing_db: float) -> float:
    """Total insertion loss for *n_crossings* identical crossings in series.

    Parameters
    ----------
    n_crossings : int
        Number of crossings.
    loss_per_crossing_db : float
        Insertion loss per crossing in dB.

    Returns
    -------
    float
        Cumulative loss in dB.
    """
    return float(n_crossings) * float(loss_per_crossing_db)


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class CrossingParams(BaseModel):
    insertion_loss_db: float = Field(0.02, ge=0.0, description="Through-path insertion loss in dB")
    crosstalk_db: float = Field(-40.0, le=0.0, description="Crosstalk coupling in dB (negative)")
    phase_rad: float = Field(0.0, description="Through-path phase in radians")
    phase_xt_rad: float = Field(0.0, description="Crosstalk path phase in radians")


class CrossingComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.crossing", title="Waveguide Crossing",
            description="Low-loss waveguide intersection with crosstalk isolation",
            in_ports=("in1", "in2"), out_ports=("out1", "out2"),
            port_domains={"in1": "optical", "in2": "optical", "out1": "optical", "out2": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return CrossingParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return crossing_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return crossing_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        return cls.meta().in_ports, cls.meta().out_ports
