"""Channel parameter extraction from measurement data."""
from __future__ import annotations
import math
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class FiberCalibration:
    """Calibration from OTDR measurements."""
    loss_db_per_km: float
    splice_losses_db: list[float]  # detected splice/connector losses
    splice_positions_km: list[float]
    intercept_dbm: float
    r_squared: float

@dataclass(frozen=True)
class Cn2Profile:
    """Atmospheric turbulence profile from scintillation."""
    effective_cn2: float  # effective Cn2 in m^(-2/3)
    rytov_variance: float
    aperture_averaging_factor: float


def fit_fiber_loss(
    distances_km: np.ndarray,
    power_dbm: np.ndarray,
    splice_threshold_db: float = 0.3,
) -> FiberCalibration:
    """Extract fiber loss from OTDR trace.

    Linear regression: P_dB(z) = P0 - alpha*z
    Detects splices/connectors from residuals.
    """
    d = np.asarray(distances_km, dtype=float)
    p = np.asarray(power_dbm, dtype=float)

    # Linear regression
    n = len(d)
    d_mean = np.mean(d)
    p_mean = np.mean(p)
    ss_dd = np.sum((d - d_mean)**2)
    ss_dp = np.sum((d - d_mean) * (p - p_mean))

    slope = ss_dp / max(ss_dd, 1e-30)
    intercept = p_mean - slope * d_mean

    loss_db_per_km = -slope  # loss is positive, slope is negative

    # R-squared
    p_pred = intercept + slope * d
    ss_res = np.sum((p - p_pred)**2)
    ss_tot = np.sum((p - p_mean)**2)
    r_sq = 1.0 - ss_res / max(ss_tot, 1e-30)

    # Detect splices from residuals
    residuals = p - p_pred
    splice_positions = []
    splice_losses = []
    for i in range(1, n):
        drop = residuals[i-1] - residuals[i]
        if drop > splice_threshold_db:
            splice_positions.append(float(d[i]))
            splice_losses.append(float(drop))

    return FiberCalibration(
        loss_db_per_km=float(loss_db_per_km),
        splice_losses_db=splice_losses,
        splice_positions_km=splice_positions,
        intercept_dbm=float(intercept),
        r_squared=float(r_sq),
    )


def fit_cn2_from_scintillation(
    sigma_I2: float,
    aperture_m: float = 0.3,
    zenith_deg: float = 0.0,
    wavelength_m: float = 785e-9,
    altitude_km: float = 500.0,
) -> Cn2Profile:
    """Invert Rytov integral for effective Cn2.

    Weak fluctuation regime:
    sigma_R^2 = 2.25 * k^(7/6) * integral(Cn2(h) * (h-h0)^(5/6) dh) * sec(zenith)^(11/6)

    Simplified: sigma_R^2 ~ 2.25 * k^(7/6) * Cn2_eff * L^(5/6) * sec(z)^(11/6)
    where L is the propagation path length.
    """
    k = 2 * math.pi / wavelength_m  # wave number
    sec_z = 1.0 / max(math.cos(math.radians(zenith_deg)), 0.01)

    # Slant range
    L = altitude_km * 1e3 * sec_z  # m

    # Aperture averaging: A_f ~ 1 / (1 + 1.06*(D/sqrt(lambda*L))^(7/3))
    fresnel = math.sqrt(wavelength_m * L)
    A_f = 1.0 / (1.0 + 1.06 * (aperture_m / fresnel) ** (7.0/3.0))

    # Corrected scintillation (undo aperture averaging)
    sigma_corrected = sigma_I2 / max(A_f, 1e-10)

    # Invert Rytov
    # sigma_R^2 = 2.25 * k^(7/6) * Cn2_eff * L^(5/6) * sec_z^(11/6)
    prefactor = 2.25 * k**(7.0/6.0) * L**(5.0/6.0) * sec_z**(11.0/6.0)

    cn2_eff = sigma_corrected / max(prefactor, 1e-30)

    return Cn2Profile(
        effective_cn2=float(cn2_eff),
        rytov_variance=float(sigma_corrected),
        aperture_averaging_factor=float(A_f),
    )
