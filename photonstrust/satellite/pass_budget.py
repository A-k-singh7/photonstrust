from __future__ import annotations

import math

import numpy as np

from photonstrust.satellite.types import GammaGammaParams, PassKeyBudget


def compute_pass_key_budget(
    *,
    time_steps_s: list[float],
    key_rates_bps: list[float],
    dt_s: float,
) -> PassKeyBudget:
    """Accumulate key bits over a satellite pass.

    ``cumulative[i] = sum(key_rates[0:i+1] * dt_s)``
    """
    cumulative: list[float] = []
    running = 0.0
    for rate in key_rates_bps:
        running += rate * dt_s
        cumulative.append(running)

    total = cumulative[-1] if cumulative else 0.0
    pass_duration = (time_steps_s[-1] - time_steps_s[0]) if len(time_steps_s) >= 2 else 0.0

    return PassKeyBudget(
        time_steps=list(time_steps_s),
        key_rates_bps=list(key_rates_bps),
        cumulative_key_bits=cumulative,
        total_key_bits=total,
        pass_duration_s=pass_duration,
        dt_s=dt_s,
        finite_key_enforced=False,
    )


def enforce_finite_key_for_pass(
    *,
    scenario_kind: str,
    pass_duration_s: float | None = None,
    finite_key_cfg: dict | None = None,
    threshold_s: float = 600.0,
) -> dict:
    """Determine whether finite-key analysis should be enforced for a pass.

    Returns a dict with ``"enforced"`` boolean and optional recommendation.
    """
    if scenario_kind == "orbit_pass" or (
        pass_duration_s is not None and pass_duration_s < threshold_s
    ):
        return {
            "enforced": True,
            "reason": (
                f"Finite-key analysis enforced: scenario_kind={scenario_kind!r}, "
                f"pass_duration_s={pass_duration_s}, threshold_s={threshold_s}"
            ),
            "recommended_config": {
                "security_epsilon": 1e-10,
                "block_size_auto": True,
            },
        }
    return {"enforced": False}


def gamma_gamma_params_from_rytov(rytov_variance: float) -> GammaGammaParams:
    """Compute Gamma-Gamma scintillation parameters from Rytov variance.

    Uses the Andrews-Phillips Gamma-Gamma model:
        alpha = [exp(0.49*sigma_R^2 / (1 + 1.11*sigma_R^(12/5))^(7/6)) - 1]^{-1}
        beta  = [exp(0.51*sigma_R^2 / (1 + 0.69*sigma_R^(12/5))^(5/6)) - 1]^{-1}
    """
    sr2 = rytov_variance
    sr_12_5 = sr2 ** (6.0 / 5.0)  # sigma_R^(12/5) = (sigma_R^2)^(6/5)

    alpha = 1.0 / (
        math.exp(0.49 * sr2 / (1.0 + 1.11 * sr_12_5) ** (7.0 / 6.0)) - 1.0
    )
    beta = 1.0 / (
        math.exp(0.51 * sr2 / (1.0 + 0.69 * sr_12_5) ** (5.0 / 6.0)) - 1.0
    )

    scintillation_index = 1.0 / alpha + 1.0 / beta + 1.0 / (alpha * beta)

    if sr2 < 1.0:
        regime = "weak"
    elif sr2 < 5.0:
        regime = "moderate"
    else:
        regime = "strong"

    return GammaGammaParams(
        alpha=alpha,
        beta=beta,
        rytov_variance=sr2,
        scintillation_index=scintillation_index,
        regime=regime,
    )


def sample_gamma_gamma(
    alpha: float,
    beta: float,
    n: int,
    *,
    seed: int | None = None,
) -> np.ndarray:
    """Draw *n* samples from the Gamma-Gamma distribution (mean ~ 1).

    The Gamma-Gamma variate is the product of two independent Gamma variates:
        x ~ Gamma(alpha, 1/alpha)
        y ~ Gamma(beta,  1/beta)
        I = x * y
    """
    rng = np.random.default_rng(seed)
    x = rng.gamma(alpha, 1.0 / alpha, size=n)
    y = rng.gamma(beta, 1.0 / beta, size=n)
    return x * y
