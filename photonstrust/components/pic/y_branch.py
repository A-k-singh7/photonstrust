"""Y-branch (Y-junction) 1x2 splitter component model.

A passive 3-port device that splits one input waveguide into two output
waveguides.  The splitting ratio *r* determines the power fraction directed
to the first output; the remainder goes to the second output.
"""

from __future__ import annotations

import math

import numpy as np

from photonstrust.components.pic.library import ComponentPorts

# ---------------------------------------------------------------------------
# Port definition
# ---------------------------------------------------------------------------

Y_BRANCH_PORTS = ComponentPorts(in_ports=("in",), out_ports=("out1", "out2"))


def y_branch_ports() -> ComponentPorts:
    """Return the port definition for a Y-branch."""
    return Y_BRANCH_PORTS


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _eta_from_loss_db(loss_db: float) -> float:
    return 10.0 ** (-max(0.0, float(loss_db)) / 10.0)


# ---------------------------------------------------------------------------
# Forward matrix
# ---------------------------------------------------------------------------

def y_branch_forward_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward matrix for a Y-branch splitter.

    Shape: (2, 1).
    M = sqrt(eta) * [[sqrt(r)], [sqrt(1 - r)]]

    Parameters (in *params* dict)
    ----------
    insertion_loss_db : float
        Excess insertion loss in dB (default 0.2).
    splitting_ratio : float
        Power fraction to out1, in [0, 1] (default 0.5).
    taper_length_um : float, optional
        Informational; does not affect the matrix in this model.
    """
    il_db = float(params.get("insertion_loss_db", 0.2) or 0.0)
    r = float(params.get("splitting_ratio", 0.5) or 0.5)
    r = min(1.0, max(0.0, r))

    eta = _eta_from_loss_db(il_db)
    amp = math.sqrt(eta)

    m = np.array(
        [[amp * math.sqrt(r)], [amp * math.sqrt(1.0 - r)]],
        dtype=np.complex128,
    )
    return m


# ---------------------------------------------------------------------------
# Scattering matrix
# ---------------------------------------------------------------------------

def y_branch_scattering_matrix(params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """3x3 scattering matrix for a Y-branch.

    Port order: [in, out1, out2].
    Assumes reciprocity (S = S^T) and no reflections by default.
    """
    fwd = y_branch_forward_matrix(params, wavelength_nm)  # (2,1)

    rl_db = params.get("return_loss_db")
    rl_mag = 0.0
    if rl_db is not None:
        rl_db = float(rl_db)
        if math.isfinite(rl_db):
            rl_mag = 10.0 ** (-rl_db / 20.0)

    s = np.zeros((3, 3), dtype=np.complex128)
    # Diagonal reflections
    s[0, 0] = rl_mag
    s[1, 1] = rl_mag
    s[2, 2] = rl_mag
    # Forward: in -> out1, in -> out2
    s[1, 0] = fwd[0, 0]
    s[2, 0] = fwd[1, 0]
    # Reciprocal reverse
    s[0, 1] = fwd[0, 0]
    s[0, 2] = fwd[1, 0]
    return s


# ---------------------------------------------------------------------------
# PICComponentBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from photonstrust.components.pic.base import PICComponentBase, PICComponentMeta


class YBranchParams(BaseModel):
    insertion_loss_db: float = Field(0.2, ge=0.0, description="Excess insertion loss in dB")
    splitting_ratio: float = Field(0.5, ge=0.0, le=1.0, description="Power fraction to out1")
    return_loss_db: float | None = Field(None, ge=0.0, description="Return loss in dB")


class YBranchComponent(PICComponentBase):
    @classmethod
    def meta(cls):
        return PICComponentMeta(
            kind="pic.y_branch", title="Y-Branch Splitter",
            description="Passive 1x2 Y-junction waveguide splitter",
            in_ports=("in",), out_ports=("out1", "out2"),
            port_domains={"in": "optical", "out1": "optical", "out2": "optical"},
        )

    @classmethod
    def params_schema(cls):
        return YBranchParams

    @classmethod
    def forward_matrix(cls, params, wavelength_nm=None):
        return y_branch_forward_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def scattering_matrix(cls, params, wavelength_nm=None):
        return y_branch_scattering_matrix(cls._as_dict(params), wavelength_nm)

    @classmethod
    def ports(cls, params=None):
        return cls.meta().in_ports, cls.meta().out_ports
