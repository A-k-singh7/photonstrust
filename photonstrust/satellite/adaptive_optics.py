"""Adaptive optics correction models for satellite QKD links.

Models the improvement in single-mode fiber coupling when adaptive
optics (AO) corrects atmospheric turbulence-induced wavefront errors.

Key references:
    - Noll, JOSA 66, 207 (1976) -- Zernike variance coefficients
    - Hardy, "Adaptive Optics for Astronomical Telescopes" (1998)
    - Gruneisen et al., Opt. Express 23, 23924 (2015) -- AO for QKD
    - Tyson, "Principles of Adaptive Optics" (2015)
    - Dikmelik & Davidson, JOSA A 22, 1553 (2005) -- SMF coupling

Models:
    - Noll residual variance: sigma_J^2 = alpha_J * (D/r0)^(5/3)
    - Strehl ratio: SR = exp(-sigma^2)  (Marechal approximation)
    - SMF coupling with AO: eta_smf = (Strehl * eta_0) where eta_0 ~ 0.81
    - Greenwood frequency: f_G = 0.4265 * v_wind / r0
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Noll residual variance coefficients (Table 1, Noll 1976)
# alpha_J: residual variance after correcting J Zernike modes
# sigma_J^2 = alpha_J * (D/r0)^(5/3)
# ---------------------------------------------------------------------------

# Index J = number of corrected Zernike modes
# alpha values from Noll (1976), JOSA 66, Table 1
NOLL_ALPHA_COEFFICIENTS: dict[int, float] = {
    0: 1.0299,    # no correction (full turbulence)
    1: 1.0299,    # piston only (same as 0 for phase variance)
    2: 0.582,     # tip removed
    3: 0.134,     # tip + tilt removed
    4: 0.111,     # + defocus
    5: 0.0880,    # + astigmatism (2 modes)
    6: 0.0648,    # + coma (2 modes)
    7: 0.0587,
    8: 0.0525,
    9: 0.0463,
    10: 0.0401,   # 10 Zernike modes corrected
    11: 0.0377,
    14: 0.0328,
    15: 0.0304,
    20: 0.0228,
    21: 0.0220,
    30: 0.0151,
    35: 0.0130,
    40: 0.0113,
    50: 0.00907,
    60: 0.00760,
    80: 0.00571,
    100: 0.00456,
}


@dataclass(frozen=True)
class AOCorrectionResult:
    """Result of adaptive optics correction calculation."""
    residual_variance_rad2: float  # residual phase variance (rad^2)
    strehl_ratio: float            # Strehl ratio after AO correction
    smf_coupling: float            # single-mode fiber coupling efficiency
    greenwood_freq_hz: float       # Greenwood frequency
    bandwidth_error_rad2: float    # temporal bandwidth error contribution
    total_strehl: float            # Strehl including bandwidth error
    total_smf_coupling: float      # SMF coupling including all errors
    diagnostics: dict[str, Any] = field(default_factory=dict)


def noll_residual_variance(
    D_m: float,
    r0_m: float,
    J: int = 3,
) -> float:
    """Compute residual wavefront variance after J Zernike mode corrections.

    The residual phase variance is:

        sigma_J^2 = alpha_J * (D/r0)^(5/3)

    where alpha_J is the Noll coefficient for J corrected modes.

    Args:
        D_m: Telescope aperture diameter (m)
        r0_m: Fried parameter (m)
        J: Number of corrected Zernike modes

    Returns:
        Residual phase variance in rad^2

    Ref: Noll, JOSA 66, 207 (1976), Table 1
    """
    D = max(0.01, float(D_m))
    r0 = max(1e-6, float(r0_m))
    J = max(0, int(J))

    alpha = _get_noll_alpha(J)
    return alpha * (D / r0) ** (5.0 / 3.0)


def _get_noll_alpha(J: int) -> float:
    """Get Noll alpha coefficient, interpolating if needed."""
    if J in NOLL_ALPHA_COEFFICIENTS:
        return NOLL_ALPHA_COEFFICIENTS[J]

    # Interpolate between known values
    keys = sorted(NOLL_ALPHA_COEFFICIENTS.keys())
    if J <= keys[0]:
        return NOLL_ALPHA_COEFFICIENTS[keys[0]]
    if J >= keys[-1]:
        # Asymptotic: alpha ~ 0.2944 * J^(-sqrt(3)/2) for large J
        return 0.2944 * J ** (-math.sqrt(3.0) / 2.0)

    # Linear interpolation in log space
    for i in range(len(keys) - 1):
        if keys[i] <= J <= keys[i + 1]:
            j1, j2 = keys[i], keys[i + 1]
            a1, a2 = NOLL_ALPHA_COEFFICIENTS[j1], NOLL_ALPHA_COEFFICIENTS[j2]
            if a1 > 0 and a2 > 0:
                frac = (J - j1) / (j2 - j1)
                log_alpha = math.log(a1) + frac * (math.log(a2) - math.log(a1))
                return math.exp(log_alpha)
            return a1 + (a2 - a1) * (J - j1) / (j2 - j1)

    return NOLL_ALPHA_COEFFICIENTS[keys[-1]]


def strehl_ratio(sigma_rad2: float) -> float:
    """Compute Strehl ratio from wavefront variance (Marechal approximation).

    SR = exp(-sigma^2)

    Valid for sigma^2 < ~2 rad^2 (extended Marechal).

    Args:
        sigma_rad2: Wavefront phase variance in rad^2

    Returns:
        Strehl ratio (0 to 1)

    Ref: Hardy, "Adaptive Optics for Astronomical Telescopes" (1998)
    """
    sigma2 = max(0.0, float(sigma_rad2))
    return math.exp(-sigma2)


def smf_coupling_with_ao(
    strehl: float,
    *,
    eta_0: float = 0.81,
) -> float:
    """Single-mode fiber coupling efficiency with AO correction.

    The coupling efficiency into a single-mode fiber is approximately:

        eta_smf = eta_0 * SR

    where eta_0 ~ 0.81 is the maximum coupling efficiency for a
    diffraction-limited Airy pattern (Dikmelik & Davidson 2005).

    Args:
        strehl: Strehl ratio after AO correction
        eta_0: Maximum coupling efficiency (diffraction-limited)

    Returns:
        SMF coupling efficiency
    """
    sr = max(0.0, min(1.0, float(strehl)))
    return sr * max(0.0, min(1.0, float(eta_0)))


def greenwood_frequency(
    v_wind_m_s: float,
    r0_m: float,
) -> float:
    """Compute Greenwood frequency for AO bandwidth requirements.

    The Greenwood frequency defines the minimum AO correction bandwidth:

        f_G = 0.4265 * v_wind / r0

    The AO system must operate at several times f_G for effective correction.

    Args:
        v_wind_m_s: Effective wind speed across the beam path (m/s)
        r0_m: Fried parameter (m)

    Returns:
        Greenwood frequency in Hz

    Ref: Greenwood, JOSA 67, 390 (1977)
    """
    v = max(0.0, float(v_wind_m_s))
    r0 = max(1e-6, float(r0_m))
    return 0.4265 * v / r0


def compute_ao_correction(
    D_m: float,
    r0_m: float,
    *,
    J: int = 20,
    v_wind_m_s: float = 10.0,
    ao_bandwidth_hz: float = 1000.0,
    eta_0: float = 0.81,
) -> AOCorrectionResult:
    """Full AO correction model for satellite QKD downlink.

    Combines Noll residual variance, Greenwood temporal error,
    Strehl ratio, and SMF coupling efficiency.

    Temporal bandwidth error:

        sigma_bw^2 = (f_G / f_AO)^(5/3)

    Total Strehl:

        SR_total = exp(-(sigma_noll^2 + sigma_bw^2))

    Args:
        D_m: Telescope aperture diameter (m)
        r0_m: Fried parameter (m)
        J: Number of corrected Zernike modes
        v_wind_m_s: Effective wind speed (m/s)
        ao_bandwidth_hz: AO system bandwidth (Hz)
        eta_0: Maximum SMF coupling efficiency

    Returns:
        AOCorrectionResult with Strehl and coupling
    """
    # Noll residual
    sigma_noll2 = noll_residual_variance(D_m, r0_m, J)

    # Greenwood frequency
    f_G = greenwood_frequency(v_wind_m_s, r0_m)

    # Temporal bandwidth error
    f_ao = max(1.0, float(ao_bandwidth_hz))
    if f_G > 0:
        sigma_bw2 = (f_G / f_ao) ** (5.0 / 3.0)
    else:
        sigma_bw2 = 0.0

    # Total variance and Strehl
    total_var = sigma_noll2 + sigma_bw2
    sr_noll = strehl_ratio(sigma_noll2)
    sr_total = strehl_ratio(total_var)

    # SMF coupling
    eta_smf = smf_coupling_with_ao(sr_noll, eta_0=eta_0)
    eta_smf_total = smf_coupling_with_ao(sr_total, eta_0=eta_0)

    return AOCorrectionResult(
        residual_variance_rad2=sigma_noll2,
        strehl_ratio=sr_noll,
        smf_coupling=eta_smf,
        greenwood_freq_hz=f_G,
        bandwidth_error_rad2=sigma_bw2,
        total_strehl=sr_total,
        total_smf_coupling=eta_smf_total,
        diagnostics={
            "D_m": float(D_m),
            "r0_m": float(r0_m),
            "J_modes": J,
            "alpha_J": _get_noll_alpha(J),
            "v_wind_m_s": float(v_wind_m_s),
            "ao_bandwidth_hz": float(ao_bandwidth_hz),
            "total_variance_rad2": total_var,
            "D_over_r0": float(D_m) / max(1e-6, float(r0_m)),
        },
    )
