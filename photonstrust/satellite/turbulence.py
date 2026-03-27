"""Turbulence fading distributions and Cn2 profile models.

Implements lognormal and gamma-gamma irradiance distributions for
satellite-to-ground quantum links, plus the Hufnagel-Valley Cn2
refractive-index structure parameter profile.

References:
    Andrews & Phillips (2005) "Laser Beam Propagation through Random Media"
    Al-Habash et al. (2001) Opt. Eng. 40(8) — Gamma-Gamma model
    Vasylyev et al. (2016) PRL 117, 090501
"""

from __future__ import annotations

import math

import numpy as np

from photonstrust.satellite.types import (
    FadingDistributionResult,
    GammaGammaParams,
    HufnagelValleyProfile,
)


def lognormal_fading(
    *,
    scintillation_index: float,
    n_samples: int = 4096,
    seed: int | None = None,
    outage_threshold_eta: float = 0.1,
) -> FadingDistributionResult:
    """Sample lognormal irradiance fading (weak turbulence regime).

    The irradiance I follows a lognormal distribution with:
        sigma_ln = sqrt(ln(1 + sigma_I^2))
        mu_ln    = -sigma_ln^2 / 2   (normalised so <I> = 1)
    """
    si = max(0.0, float(scintillation_index))
    n = max(64, int(n_samples))
    rng = np.random.default_rng(None if seed is None else int(seed))

    sigma_ln = math.sqrt(math.log1p(si)) if si > 0.0 else 0.0
    mu_ln = -0.5 * sigma_ln * sigma_ln

    if sigma_ln > 0.0:
        samples = rng.lognormal(mean=mu_ln, sigma=sigma_ln, size=n)
    else:
        samples = np.ones(n, dtype=float)

    samples = np.clip(samples, 0.0, None)
    eta_mean = float(np.mean(samples))
    eta_median = float(np.median(samples))
    outage = float(np.mean(samples < outage_threshold_eta))
    fade_margin_db = -10.0 * math.log10(max(1e-15, eta_mean)) if eta_mean > 0 else 0.0

    return FadingDistributionResult(
        model="lognormal",
        scintillation_index=si,
        eta_mean=eta_mean,
        eta_median=eta_median,
        outage_probability=outage,
        outage_threshold_eta=outage_threshold_eta,
        fade_margin_db=fade_margin_db,
        samples_used=n,
        distribution_params={"sigma_ln": sigma_ln, "mu_ln": mu_ln},
    )


def gamma_gamma_fading(
    *,
    scintillation_index: float,
    rytov_variance: float | None = None,
    alpha: float | None = None,
    beta: float | None = None,
    n_samples: int = 4096,
    seed: int | None = None,
    outage_threshold_eta: float = 0.1,
) -> FadingDistributionResult:
    """Sample gamma-gamma irradiance fading (moderate-to-strong turbulence).

    If alpha/beta are not given, they are computed from scintillation_index
    or rytov_variance via the Andrews-Phillips model.
    """
    si = max(1e-6, float(scintillation_index))
    n = max(64, int(n_samples))
    rng = np.random.default_rng(None if seed is None else int(seed))

    if alpha is not None and beta is not None:
        a = max(1e-3, float(alpha))
        b = max(1e-3, float(beta))
    elif rytov_variance is not None:
        from photonstrust.satellite.pass_budget import gamma_gamma_params_from_rytov
        gg = gamma_gamma_params_from_rytov(float(rytov_variance))
        a, b = gg.alpha, gg.beta
    else:
        a = max(1e-3, 1.0 / si)
        b = max(1e-3, 1.0 / max(1e-3, 0.75 * si + 0.05))

    x = rng.gamma(shape=a, scale=1.0 / a, size=n)
    y = rng.gamma(shape=b, scale=1.0 / b, size=n)
    samples = x * y
    samples = np.clip(samples, 0.0, None)

    eta_mean = float(np.mean(samples))
    eta_median = float(np.median(samples))
    outage = float(np.mean(samples < outage_threshold_eta))
    fade_margin_db = -10.0 * math.log10(max(1e-15, eta_mean)) if eta_mean > 0 else 0.0

    return FadingDistributionResult(
        model="gamma_gamma",
        scintillation_index=si,
        eta_mean=eta_mean,
        eta_median=eta_median,
        outage_probability=outage,
        outage_threshold_eta=outage_threshold_eta,
        fade_margin_db=fade_margin_db,
        samples_used=n,
        distribution_params={"alpha": a, "beta": b},
    )


def select_fading_model(
    *,
    scintillation_index: float,
    rytov_variance: float | None = None,
    n_samples: int = 4096,
    seed: int | None = None,
    outage_threshold_eta: float = 0.1,
) -> FadingDistributionResult:
    """Automatically select lognormal or gamma-gamma based on turbulence regime.

    Weak turbulence (sigma_I^2 < 1.0) -> lognormal
    Moderate/strong (sigma_I^2 >= 1.0) -> gamma-gamma
    """
    si = max(0.0, float(scintillation_index))
    if si < 1.0:
        return lognormal_fading(
            scintillation_index=si,
            n_samples=n_samples,
            seed=seed,
            outage_threshold_eta=outage_threshold_eta,
        )
    return gamma_gamma_fading(
        scintillation_index=si,
        rytov_variance=rytov_variance,
        n_samples=n_samples,
        seed=seed,
        outage_threshold_eta=outage_threshold_eta,
    )


def hufnagel_valley_cn2(
    h_m: float,
    *,
    rms_wind_speed_m_s: float = 21.0,
    ground_cn2: float = 1.7e-14,
) -> float:
    """Compute Cn2(h) from the Hufnagel-Valley 5/7 profile.

    Cn2(h) = 0.00594*(v/27)^2 * (1e-5*h)^10 * exp(-h/1000)
             + 2.7e-16 * exp(-h/1500)
             + A * exp(-h/100)

    Parameters
    ----------
    h_m : float
        Altitude in metres.
    rms_wind_speed_m_s : float
        RMS wind speed (m/s), default 21 m/s (HV-5/7 standard).
    ground_cn2 : float
        Ground-level Cn2 (m^{-2/3}), default 1.7e-14.
    """
    h = max(0.0, float(h_m))
    v = max(0.1, float(rms_wind_speed_m_s))
    a = max(0.0, float(ground_cn2))

    term1 = 0.00594 * (v / 27.0) ** 2 * (1e-5 * h) ** 10 * math.exp(-h / 1000.0)
    term2 = 2.7e-16 * math.exp(-h / 1500.0)
    term3 = a * math.exp(-h / 100.0)
    return term1 + term2 + term3


def compute_rytov_variance(
    *,
    wavelength_nm: float,
    zenith_angle_deg: float,
    orbit_altitude_km: float = 500.0,
    rms_wind_speed_m_s: float = 21.0,
    ground_cn2: float = 1.7e-14,
    n_layers: int = 100,
) -> HufnagelValleyProfile:
    """Compute Rytov variance for a satellite downlink via numerical integration.

    sigma_R^2 = 2.25 * k^(7/6) * sec(zeta)^(11/6) * integral[Cn2(h) * (h/H)^(5/6) dh]

    Also computes the Fried parameter and isoplanatic angle.
    """
    wl_m = max(1e-10, float(wavelength_nm) * 1e-9)
    k = 2.0 * math.pi / wl_m
    zeta_rad = math.radians(max(0.0, min(90.0, float(zenith_angle_deg))))
    sec_zeta = 1.0 / max(1e-6, math.cos(zeta_rad))
    h_atm = 20000.0  # atmosphere effective top (m)
    h_max = float(orbit_altitude_km) * 1000.0
    v = max(0.1, float(rms_wind_speed_m_s))
    a = max(0.0, float(ground_cn2))

    # Numerical integration of Cn2 profile
    dh = h_atm / max(1, int(n_layers))
    integral_rytov = 0.0
    integral_fried = 0.0
    integral_iso = 0.0
    for i in range(int(n_layers)):
        h = (i + 0.5) * dh
        cn2_h = hufnagel_valley_cn2(h, rms_wind_speed_m_s=v, ground_cn2=a)
        integral_rytov += cn2_h * (h / max(1.0, h_max)) ** (5.0 / 6.0) * dh
        integral_fried += cn2_h * dh
        integral_iso += cn2_h * h ** (5.0 / 3.0) * dh

    sigma_r2 = 2.25 * k ** (7.0 / 6.0) * sec_zeta ** (11.0 / 6.0) * integral_rytov

    # Fried parameter r0
    r0 = (0.423 * k ** 2 * sec_zeta * integral_fried) ** (-3.0 / 5.0) if integral_fried > 0 else 1.0

    # Isoplanatic angle
    if integral_iso > 0:
        theta_0 = 0.314 * (math.cos(zeta_rad) / wl_m) * (2.914 * k ** 2 * sec_zeta * integral_iso) ** (-3.0 / 5.0)
        theta_0_urad = theta_0 * 1e6
    else:
        theta_0_urad = 100.0

    # Scintillation index from Rytov variance (weak approx)
    si = min(sigma_r2, 10.0)

    return HufnagelValleyProfile(
        ground_cn2=a,
        rms_wind_speed_m_s=v,
        rytov_variance=sigma_r2,
        scintillation_index=si,
        fried_parameter_m=r0,
        isoplanatic_angle_urad=theta_0_urad,
        zenith_angle_deg=float(zenith_angle_deg),
        wavelength_nm=float(wavelength_nm),
    )
