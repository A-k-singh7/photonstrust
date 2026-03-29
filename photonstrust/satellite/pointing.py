"""Pointing bias + jitter decomposition with Rice distribution model.

Real pointing systems have both a systematic boresight error (bias) and
random jitter component.  The combined radial error follows a Rice
distribution (non-central Rayleigh).

References:
    Toyoshima et al. (2006) "Mutual alignment errors" Applied Optics 45(30)
    Liao et al. (2017) "Satellite-to-ground QKD" Nature 549, 43-47
"""

from __future__ import annotations

import math

import numpy as np

from photonstrust.satellite.types import PointingBudgetResult


def pointing_budget(
    *,
    bias_urad: float = 0.0,
    jitter_urad: float = 1.5,
    beam_divergence_urad: float = 10.0,
    n_samples: int = 4096,
    seed: int | None = None,
    outage_threshold_eta: float = 0.1,
) -> PointingBudgetResult:
    """Compute pointing loss with bias + jitter decomposition.

    The pointing error is decomposed as:
        r_point = r_bias + r_jitter

    where |r_bias| is the deterministic boresight error and r_jitter
    follows a Rayleigh distribution with scale sigma_jitter.

    The combined radial error follows a Rice distribution:
        f(r) = (r/sigma^2) * exp(-(r^2 + r0^2)/(2*sigma^2)) * I_0(r*r0/sigma^2)

    where r0 = bias, sigma = jitter, and I_0 is the modified Bessel
    function of the first kind.

    The pointing efficiency is:
        eta_point = exp(-(r / theta_beam)^2)
    """
    bias = max(0.0, float(bias_urad))
    jitter = max(0.0, float(jitter_urad))
    theta = max(1e-6, float(beam_divergence_urad))
    n = max(64, int(n_samples))

    # Rice parameter K = r0^2 / (2 * sigma^2)
    if jitter > 0.0:
        rice_k = (bias ** 2) / (2.0 * jitter ** 2) if bias > 0.0 else 0.0
    else:
        rice_k = float("inf") if bias > 0.0 else 0.0

    # Boresight-only efficiency (no jitter)
    eta_boresight = math.exp(-((bias / theta) ** 2))

    # Monte Carlo with 2D Gaussian offsets
    rng = np.random.default_rng(None if seed is None else int(seed))
    x = rng.normal(loc=bias, scale=max(1e-12, jitter), size=n)
    y = rng.normal(loc=0.0, scale=max(1e-12, jitter), size=n)
    radial = np.sqrt(x * x + y * y)
    eta_samples = np.clip(np.exp(-((radial / theta) ** 2)), 0.0, 1.0)

    eta_mean = float(np.mean(eta_samples))
    outage = float(np.mean(eta_samples < outage_threshold_eta))

    model = "rice" if bias > 0.0 else "rayleigh"

    return PointingBudgetResult(
        bias_urad=bias,
        jitter_urad=jitter,
        beam_divergence_urad=theta,
        eta_mean=eta_mean,
        eta_boresight=eta_boresight,
        outage_probability=outage,
        rice_parameter_k=rice_k if math.isfinite(rice_k) else 1e6,
        distribution_model=model,
    )


def joint_pointing_turbulence_outage(
    *,
    pointing_samples: np.ndarray,
    turbulence_samples: np.ndarray,
    eta_geometric: float,
    eta_atmospheric: float,
    eta_connector: float = 1.0,
    outage_threshold_eta: float = 1e-6,
) -> dict:
    """Compute joint outage probability from pointing + turbulence samples.

    Combines independent pointing and turbulence Monte Carlo samples to
    estimate the total channel outage probability.  This accounts for
    the convolution of both distributions.
    """
    n_min = min(len(pointing_samples), len(turbulence_samples))
    p = np.asarray(pointing_samples[:n_min], dtype=float)
    t = np.asarray(turbulence_samples[:n_min], dtype=float)

    eta_fixed = float(eta_geometric) * float(eta_atmospheric) * float(eta_connector)
    eta_total = np.clip(eta_fixed * p * t, 0.0, 1.0)

    outage = float(np.mean(eta_total < outage_threshold_eta))
    eta_mean = float(np.mean(eta_total))
    eta_p5 = float(np.percentile(eta_total, 5))
    eta_p50 = float(np.percentile(eta_total, 50))
    eta_p95 = float(np.percentile(eta_total, 95))

    return {
        "outage_probability": outage,
        "eta_mean": eta_mean,
        "eta_p5": eta_p5,
        "eta_p50": eta_p50,
        "eta_p95": eta_p95,
        "samples_used": int(n_min),
        "outage_threshold_eta": float(outage_threshold_eta),
    }
