"""Shared helpers for relay-based QKD protocol models."""

from __future__ import annotations

import math

from photonstrust.channels.fiber import apply_fiber_loss, dispersion_ps
from photonstrust.utils import clamp


def normalize_protocol_name(name: str | None) -> str:
    raw = str(name or "").strip().lower().replace("-", "_")

    if raw in {"bb84", "bb84_decoy", "decoy_bb84", "bb84_wcp", "decoy"}:
        return "bb84_decoy"
    if raw in {"mdi", "mdi_qkd"}:
        return "mdi_qkd"
    if raw in {"amdi", "amdi_qkd", "async_mdi", "mp_qkd", "mode_pairing"}:
        return "amdi_qkd"
    if raw in {"pm", "pm_qkd"}:
        return "pm_qkd"
    if raw in {"tf", "tf_qkd", "twin_field", "twinfield"}:
        return "tf_qkd"

    return raw


def relay_split_distances_km(distance_km: float, relay_fraction: float | None) -> tuple[float, float]:
    """Split Alice-Bob distance into Alice-relay and Bob-relay segments."""

    frac = 0.5 if relay_fraction is None else float(relay_fraction)
    frac = clamp(frac, 0.0, 1.0)
    da = max(0.0, float(distance_km) * frac)
    db = max(0.0, float(distance_km) - da)
    return da, db


def fiber_segment_transmittance(
    distance_km: float,
    loss_db_per_km: float,
    connector_loss_db: float,
) -> float:
    eta = apply_fiber_loss(distance_km, loss_db_per_km)
    eta *= 10 ** (-float(connector_loss_db) / 10.0)
    return max(0.0, float(eta))


def effective_coincidence_window_s(
    *,
    distance_km: float,
    channel: dict,
    detector: dict,
    timing: dict,
) -> float:
    """Compute the effective detection window in seconds.

    Mirrors the direct-link logic in `photonstrust.qkd.compute_point` so relay
    protocols reuse the same timing semantics.
    """

    jitter_ps_fwhm = float(detector.get("jitter_ps_fwhm", 0.0) or 0.0)
    jitter_sigma_ps = jitter_ps_fwhm / 2.355 if jitter_ps_fwhm > 0 else 0.0

    drift_ps_rms = float(timing.get("sync_drift_ps_rms", 0.0) or 0.0)
    disp_ps_per_km = float(channel.get("dispersion_ps_per_km", 0.0) or 0.0)
    disp_ps = float(dispersion_ps(distance_km, disp_ps_per_km))

    sigma_eff_ps = math.sqrt(jitter_sigma_ps**2 + drift_ps_rms**2 + disp_ps**2)

    window_ps = timing.get("coincidence_window_ps")
    if window_ps is None:
        window_ps = max(3.0 * sigma_eff_ps, 200.0)
    window_ps = max(0.0, float(window_ps))
    return window_ps * 1e-12


def per_pulse_prob_from_rate(rate_cps: float, window_s: float) -> float:
    """Convert a count rate (cps) into a per-window click probability."""

    lam = max(0.0, float(rate_cps)) * max(0.0, float(window_s))
    if lam <= 0.0:
        return 0.0
    # Poisson arrivals; probability of at least one count in the window.
    # Use expm1 for numerical stability at small lambda.
    return clamp(-math.expm1(-lam), 0.0, 1.0)


def apply_dead_time(
    rate_in_hz: float,
    dead_time_s: float,
    *,
    model: str | None = None,
) -> tuple[float, float]:
    """Apply detector dead time to an input event rate.

    Returns (rate_out_hz, scale) where scale = rate_out / rate_in.

    Default model is non-paralyzable, matching the stochastic event-filtering
    semantics used by `photonstrust.physics.detector.simulate_detector`.
    """

    r = max(0.0, float(rate_in_hz))
    tau = max(0.0, float(dead_time_s))
    if r <= 0.0 or tau <= 0.0:
        return r, 1.0

    m = str(model or "nonparalyzable").strip().lower()
    if m in {"nonparalyzable", "non_paralyzable", "np"}:
        # Non-paralyzable: r_out = r_in / (1 + r_in * tau)
        r_out = r / (1.0 + r * tau)
    elif m in {"paralyzable", "p"}:
        # Paralyzable: r_out = r_in * exp(-r_in * tau)
        r_out = r * math.exp(-r * tau)
    elif m in {"legacy", "first_order", "linear"}:
        # Legacy first-order approximation.
        r_out = r * max(0.0, 1.0 - r * tau)
    else:
        raise ValueError(f"Unsupported dead_time_model: {model!r}")

    scale = (r_out / r) if r > 0.0 else 0.0
    return max(0.0, float(r_out)), clamp(float(scale), 0.0, 1.0)


def protocol_misalignment_error(proto: dict) -> float:
    """Return a misalignment error probability in [0, 0.5]."""

    optical_visibility = proto.get("optical_visibility")
    if optical_visibility is not None:
        vis = clamp(float(optical_visibility), 0.0, 1.0)
        return clamp((1.0 - vis) / 2.0, 0.0, 0.5)
    try:
        return clamp(float(proto.get("misalignment_prob", 0.0) or 0.0), 0.0, 0.5)
    except Exception:
        return 0.0


def misalignment_error_with_visibility_factor(proto: dict, visibility_factor: float) -> float:
    """Protocol misalignment error with an extra multiplicative visibility factor.

    Useful for fiber polarization drift and similar effects that primarily reduce
    interference visibility rather than attenuating throughput.
    """

    vfac = clamp(float(visibility_factor), 0.0, 1.0)
    optical_visibility = proto.get("optical_visibility")
    if optical_visibility is not None:
        v0 = clamp(float(optical_visibility), 0.0, 1.0)
    else:
        e0 = protocol_misalignment_error(proto)
        v0 = clamp(1.0 - 2.0 * e0, 0.0, 1.0)
    v_eff = clamp(v0 * vfac, 0.0, 1.0)
    return clamp((1.0 - v_eff) / 2.0, 0.0, 0.5)
