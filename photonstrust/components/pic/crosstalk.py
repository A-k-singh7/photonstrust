"""Analytic crosstalk predictor for parallel waveguides (v0).

This is a calibration-friendly "performance DRC" primitive: it is designed to
be deterministic, monotonic (within applicability bounds), and fast enough for
real-time UI interactions.
"""

from __future__ import annotations

import math


def predict_parallel_waveguide_xt_db(
    *,
    gap_um: float,
    parallel_length_um: float,
    wavelength_nm: float,
    model: dict | None = None,
    corner: dict | None = None,
) -> float:
    """Predict crosstalk in dB for two parallel waveguides.

    Returns a negative dB value (more negative is better).

    Model (v0, heuristic):
      kappa(g, lambda) = kappa0 * exp(-g / gap_decay) * (lambda/lambda_ref)^lambda_exp * corner_scale
      P_xt ~= min(1, (kappa * L)^2)
      XT_dB = 10*log10(P_xt)

    The quadratic approximation avoids sinusoidal beating that is not monotonic
    over long interaction lengths.
    """

    model = model or {}
    corner = corner or {}

    gap_um = max(0.0, float(gap_um))
    parallel_length_um = max(0.0, float(parallel_length_um))
    wavelength_nm = max(1.0, float(wavelength_nm))

    kappa0_per_um = float(model.get("kappa0_per_um", 1.0e-3))
    gap_decay_um = float(model.get("gap_decay_um", 0.2))
    lambda_ref_nm = float(model.get("lambda_ref_nm", 1550.0))
    lambda_exp = float(model.get("lambda_exp", 1.0))

    if not math.isfinite(kappa0_per_um) or kappa0_per_um <= 0.0:
        return -200.0
    if not math.isfinite(gap_decay_um) or gap_decay_um <= 0.0:
        return -200.0

    corner_scale = float(corner.get("kappa_scale", 1.0))
    if not math.isfinite(corner_scale) or corner_scale <= 0.0:
        corner_scale = 1.0

    wavelength_scale = (wavelength_nm / max(1e-6, lambda_ref_nm)) ** lambda_exp
    kappa = kappa0_per_um * math.exp(-gap_um / gap_decay_um) * wavelength_scale * corner_scale
    kappa = max(0.0, float(kappa))

    coupling_amp = kappa * parallel_length_um
    p_xt = min(1.0, coupling_amp * coupling_amp)
    if p_xt <= 0.0:
        return -200.0
    if not math.isfinite(p_xt):
        return -200.0
    return float(10.0 * math.log10(p_xt))


def recommended_min_gap_um(
    *,
    target_xt_db: float,
    parallel_length_um: float,
    wavelength_nm: float,
    model: dict | None = None,
    corner: dict | None = None,
) -> float:
    """Solve for a minimum gap that meets a target crosstalk spec (v0).

    This assumes the quadratic approximation region (no beating).
    """

    model = model or {}
    corner = corner or {}

    target_xt_db = float(target_xt_db)
    if not math.isfinite(target_xt_db):
        raise ValueError("target_xt_db must be finite")

    parallel_length_um = max(0.0, float(parallel_length_um))
    wavelength_nm = max(1.0, float(wavelength_nm))

    kappa0_per_um = float(model.get("kappa0_per_um", 1.0e-3))
    gap_decay_um = float(model.get("gap_decay_um", 0.2))
    lambda_ref_nm = float(model.get("lambda_ref_nm", 1550.0))
    lambda_exp = float(model.get("lambda_exp", 1.0))

    corner_scale = float(corner.get("kappa_scale", 1.0))
    if not math.isfinite(corner_scale) or corner_scale <= 0.0:
        corner_scale = 1.0

    if parallel_length_um <= 0.0:
        return 0.0
    if kappa0_per_um <= 0.0 or gap_decay_um <= 0.0:
        return float("inf")

    # Convert XT spec to power probability.
    target_p = 10 ** (target_xt_db / 10.0)
    target_p = min(1.0, max(0.0, float(target_p)))
    if target_p <= 0.0:
        return float("inf")

    wavelength_scale = (wavelength_nm / max(1e-6, lambda_ref_nm)) ** lambda_exp
    effective_kappa0 = kappa0_per_um * wavelength_scale * corner_scale
    if effective_kappa0 <= 0.0:
        return float("inf")

    # target_p = (kappa*L)^2 => kappa = sqrt(target_p)/L
    target_kappa = math.sqrt(target_p) / parallel_length_um
    if target_kappa <= 0.0:
        return float("inf")

    # kappa = kappa0 * exp(-gap/gd) => gap = -gd * ln(kappa/kappa0)
    ratio = target_kappa / effective_kappa0
    if ratio <= 0.0:
        return float("inf")
    gap = -gap_decay_um * math.log(ratio)
    return max(0.0, float(gap))
