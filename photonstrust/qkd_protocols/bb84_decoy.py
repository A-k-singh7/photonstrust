"""BB84 weak-coherent-pulse model with vacuum+weak decoy scaffolding."""

from __future__ import annotations

import math

from photonstrust.channels.coexistence import compute_raman_counts_cps
from photonstrust.channels.fiber import apply_fiber_loss, dispersion_ps
from photonstrust.channels.free_space import total_free_space_efficiency
from photonstrust.qkd_protocols.common import apply_dead_time, per_pulse_prob_from_rate
from photonstrust.qkd_protocols.finite_key import apply_composable_finite_key
from photonstrust.qkd_types import QKDResult
from photonstrust.utils import binary_entropy, clamp


def compute_point_bb84_decoy(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    """Compute a BB84 decoy-state key-rate point.

    The implementation uses a practical analytical approximation with
    vacuum+weak decoy bounds (asymptotic), plus a composable finite-key
    scaffold hook for parity with other protocol families.
    """

    source = scenario.get("source", {}) or {}
    channel = scenario.get("channel", {}) or {}
    detector = scenario.get("detector", {}) or {}
    timing = scenario.get("timing", {}) or {}
    proto = scenario.get("protocol", {}) or {}

    rep_rate_hz = float(source.get("rep_rate_mhz", 0.0) or 0.0) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("source.rep_rate_mhz must be > 0 for BB84 decoy-state")

    eta_source = float(source.get("collection_efficiency", 1.0) or 1.0) * float(source.get("coupling_efficiency", 1.0) or 1.0)

    channel_model = str(channel.get("model", "fiber")).lower()
    if channel_model == "free_space":
        fs = total_free_space_efficiency(
            distance_km=float(distance_km),
            wavelength_nm=float(scenario.get("wavelength_nm", 1550.0)),
            channel_cfg=channel,
        )
        eta_channel = float(fs["eta_channel"])
        loss_db = float(fs["total_loss_db"])
        channel_bg_cps = float(fs.get("background_counts_cps", 0.0) or 0.0)
        raman_cps = 0.0
    else:
        alpha = float(channel.get("fiber_loss_db_per_km", 0.2) or 0.2)
        connector_loss_db = float(channel.get("connector_loss_db", 0.0) or 0.0)
        eta_channel = apply_fiber_loss(float(distance_km), alpha) * 10 ** (-connector_loss_db / 10.0)
        eta_channel = clamp(float(eta_channel), 0.0, 1.0)
        loss_db = float(distance_km) * alpha + connector_loss_db
        channel_bg_cps = float(channel.get("background_counts_cps", 0.0) or 0.0)
        raman_cps = float(
            compute_raman_counts_cps(
                float(distance_km),
                channel.get("coexistence"),
                fiber_loss_db_per_km=alpha,
            )
        )

    eta_d = clamp(float(detector.get("pde", 0.0) or 0.0), 0.0, 1.0)
    eta = clamp(float(eta_source) * float(eta_channel) * float(eta_d), 0.0, 1.0)

    jitter_ps_fwhm = float(detector.get("jitter_ps_fwhm", 0.0) or 0.0)
    jitter_sigma_ps = jitter_ps_fwhm / 2.355 if jitter_ps_fwhm > 0 else 0.0
    drift_ps_rms = float(timing.get("sync_drift_ps_rms", 0.0) or 0.0)
    disp_ps = float(dispersion_ps(float(distance_km), channel.get("dispersion_ps_per_km", 0.0)))
    sigma_eff_ps = math.sqrt(jitter_sigma_ps**2 + drift_ps_rms**2 + disp_ps**2)
    window_ps = timing.get("coincidence_window_ps")
    if window_ps is None:
        window_ps = max(3.0 * sigma_eff_ps, 200.0)
    window_s = max(0.0, float(window_ps)) * 1e-12

    dark_cps = float(detector.get("dark_counts_cps", 0.0) or 0.0)
    det_bg_cps = float(detector.get("background_counts_cps", 0.0) or 0.0)
    noise_cps = max(0.0, dark_cps + det_bg_cps + channel_bg_cps + raman_cps)

    # Two-detector receiver: total noise-click probability in basis choice.
    p_noise_det = per_pulse_prob_from_rate(noise_cps, window_s)
    p_noise = 1.0 - (1.0 - p_noise_det) ** 2
    p_noise = clamp(float(p_noise), 0.0, 0.999999)

    mu = float(proto.get("mu", 0.5) or 0.5)
    nu = float(proto.get("nu", 0.1) or 0.1)
    omega = float(proto.get("omega", 0.0) or 0.0)
    if not (mu > nu >= omega >= 0.0):
        raise ValueError(f"BB84 decoy requires mu > nu >= omega >= 0, got mu={mu} nu={nu} omega={omega}")

    e_opt = clamp(float(proto.get("misalignment_prob", 0.015) or 0.015), 0.0, 0.5)
    f_ec = max(1.0, float(proto.get("ec_efficiency", 1.16) or 1.16))
    sifting = clamp(float(proto.get("sifting_factor", 0.5) or 0.5), 0.0, 1.0)

    q_mu, e_mu = _gain_error(mu=mu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_nu, e_nu = _gain_error(mu=nu, eta=eta, p_noise=p_noise, e_opt=e_opt)
    q_om, _ = _gain_error(mu=omega, eta=eta, p_noise=p_noise, e_opt=e_opt)

    y0 = clamp(float(q_om), 0.0, 1.0)
    y1_l = _y1_lower_bound(mu=mu, nu=nu, q_mu=q_mu, q_nu=q_nu, y0=y0)
    q1_l = clamp(float(mu * math.exp(-mu) * y1_l), 0.0, 1.0)

    e1_u = _e1_upper_bound(nu=nu, q_nu=q_nu, e_nu=e_nu, y0=y0, y1_l=y1_l)
    privacy_term_asymptotic = max(0.0, 1.0 - binary_entropy(e1_u))

    fk = apply_composable_finite_key(
        finite_key_cfg=scenario.get("finite_key"),
        sifting=sifting,
        privacy_term_asymptotic=privacy_term_asymptotic,
    )

    r_pulse = q1_l * fk.privacy_term_effective - q_mu * f_ec * binary_entropy(e_mu)
    r_pulse = max(0.0, float(r_pulse))
    key_rate_bps = rep_rate_hz * fk.sifting_effective * r_pulse

    dead_time_s = float(detector.get("dead_time_ns", 0.0) or 0.0) * 1e-9
    event_rate_hz = rep_rate_hz * q_mu
    event_rate_hz, sat = apply_dead_time(event_rate_hz, dead_time_s, model=detector.get("dead_time_model"))
    key_rate_bps *= sat

    qber_total = clamp(float(e_mu), 0.0, 0.5)
    fidelity = clamp(1.0 - qber_total, 0.0, 1.0)

    denom_noise = max(1e-30, dark_cps + det_bg_cps + channel_bg_cps + raman_cps)
    q_dark_detector = qber_total * (dark_cps / denom_noise)
    q_background = qber_total * ((det_bg_cps + channel_bg_cps) / denom_noise)
    q_raman = qber_total * (raman_cps / denom_noise)

    p_false = max(0.0, q_mu - q1_l)

    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=float(event_rate_hz),
        key_rate_bps=float(max(0.0, key_rate_bps)),
        qber_total=float(qber_total),
        fidelity=float(fidelity),
        p_pair=float(q1_l),
        p_false=float(p_false),
        q_multi=0.0,
        q_dark=float(p_false / q_mu) if q_mu > 0 else 0.0,
        q_timing=0.0,
        q_misalignment=float(e_opt),
        q_source=0.0,
        q_dark_detector=float(q_dark_detector),
        q_background=float(q_background),
        q_raman=float(q_raman),
        background_counts_cps=float(det_bg_cps + channel_bg_cps),
        raman_counts_cps=float(raman_cps),
        finite_key_enabled=bool(fk.enabled),
        privacy_term_asymptotic=float(privacy_term_asymptotic),
        privacy_term_effective=float(fk.privacy_term_effective),
        finite_key_penalty=float(fk.finite_key_penalty),
        loss_db=float(loss_db),
        protocol_name="bb84_decoy",
        single_photon_yield_lb=float(y1_l),
        single_photon_error_ub=float(e1_u),
        finite_key_epsilon=float(fk.security_epsilon),
    )


def _gain_error(*, mu: float, eta: float, p_noise: float, e_opt: float) -> tuple[float, float]:
    p_sig = 1.0 - math.exp(-max(0.0, float(mu)) * clamp(float(eta), 0.0, 1.0))
    p_noise = clamp(float(p_noise), 0.0, 0.999999)
    q = 1.0 - (1.0 - p_sig) * (1.0 - p_noise)
    q = clamp(float(q), 0.0, 1.0)
    if q <= 0.0:
        return 0.0, 0.0

    e_opt = clamp(float(e_opt), 0.0, 0.5)
    err = (e_opt * p_sig * (1.0 - p_noise) + 0.5 * p_noise) / q
    return q, clamp(float(err), 0.0, 0.5)


def _y1_lower_bound(*, mu: float, nu: float, q_mu: float, q_nu: float, y0: float) -> float:
    """Vacuum+weak decoy lower bound on Y1 (asymptotic approximation)."""

    mu = float(mu)
    nu = float(nu)
    if mu <= nu or nu <= 0.0:
        return 0.0

    num = (
        q_nu * math.exp(nu)
        - q_mu * math.exp(mu) * (nu**2 / mu**2)
        - ((mu**2 - nu**2) / mu**2) * y0
    )
    den = mu * nu - nu**2
    if den <= 0.0:
        return 0.0
    y1 = (mu / den) * num
    return clamp(float(y1), 0.0, 1.0)


def _e1_upper_bound(*, nu: float, q_nu: float, e_nu: float, y0: float, y1_l: float) -> float:
    """Vacuum+weak decoy upper bound on e1 (asymptotic approximation)."""

    if nu <= 0.0 or y1_l <= 0.0:
        return 0.5
    e0 = 0.5
    numer = q_nu * math.exp(nu) * e_nu - e0 * y0
    denom = nu * y1_l
    if denom <= 0.0:
        return 0.5
    return clamp(float(numer / denom), 0.0, 0.5)
