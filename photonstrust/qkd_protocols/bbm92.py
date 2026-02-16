"""BBM92/E91 direct-link entanglement-based QKD model.

This module implements a coincidence-based analytical model for an entangled
photon-pair source with threshold detectors.

For SPDC (two-mode squeezed vacuum), the photon-pair number follows a thermal
(geometric) distribution with mean pair number mu. We use closed-form averages
for:

- total coincidence probability per pulse (Q)
- "true" single-pair coincidence probability (Q_true)
- accidental coincidence probability (Q_acc = Q - Q_true)

Noise clicks (dark/background/Raman) are modeled as Poisson arrivals within the
coincidence window.

Model anchors (standard SPDC entanglement-based QKD / coincidence counting):

- Two-mode squeezed vacuum pair-number distribution:
    P(n) = mu^n / (1+mu)^(n+1)
- Poisson noise probability within a window:
    p_noise = 1 - exp(-noise_cps * window_s)

The Q/Q_true expressions are derived by averaging threshold-click patterns over
P(n) using the geometric generating function.
"""

from __future__ import annotations

import math

from photonstrust.channels.engine import compute_channel_diagnostics
from photonstrust.channels.fiber import dispersion_ps
from photonstrust.physics import build_detector_profile, build_source_profile
from photonstrust.qkd_protocols.common import apply_dead_time, misalignment_error_with_visibility_factor
from photonstrust.qkd_protocols.finite_key import apply_composable_finite_key
from photonstrust.qkd_types import QKDResult
from photonstrust.utils import binary_entropy, clamp


def compute_point_bbm92(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    source = scenario["source"]
    channel = scenario["channel"]
    detector = scenario["detector"]
    timing = scenario["timing"]
    protocol = scenario["protocol"]

    rep_rate_hz = float(source["rep_rate_mhz"]) * 1e6

    eta_source = float(source["collection_efficiency"]) * float(source["coupling_efficiency"])
    channel_model = str(channel.get("model", "fiber")).lower()

    ch_diag = compute_channel_diagnostics(
        distance_km=float(distance_km),
        wavelength_nm=float(scenario.get("wavelength_nm", 1550.0) or 1550.0),
        channel_cfg=channel,
    )
    eta_channel = float(ch_diag["eta_channel"])
    total_loss_db = float(ch_diag["total_loss_db"])
    channel_background_counts_cps = float(ch_diag.get("background_counts_cps", 0.0) or 0.0)
    raman_counts_cps = float(ch_diag.get("raman_counts_cps", 0.0) or 0.0)

    pol_vis = 1.0
    if channel_model == "fiber":
        pol_vis = float(ch_diag.get("decomposition", {}).get("eta_polarization", 1.0) or 1.0)

    detector_background_counts_cps = float(detector.get("background_counts_cps", 0.0) or 0.0)
    background_counts_cps = max(0.0, float(channel_background_counts_cps) + float(detector_background_counts_cps))
    raman_counts_cps = max(0.0, float(raman_counts_cps))

    detector_profile = build_detector_profile(detector)

    eta_channel = clamp(float(eta_channel), 0.0, 1.0)
    eta_det_base = detector_profile.pde

    eta_total = clamp(float(eta_source) * float(eta_channel) * float(eta_det_base), 0.0, 1.0)

    # Effective coincidence window.
    jitter_sigma_ps = float(detector["jitter_ps_fwhm"]) / 2.355
    dispersion_ps_value = float(dispersion_ps(float(distance_km), channel.get("dispersion_ps_per_km", 0.0)))
    sigma_eff_ps = math.sqrt(
        jitter_sigma_ps**2 + float(timing["sync_drift_ps_rms"]) ** 2 + dispersion_ps_value**2
    )
    window_ps = timing.get("coincidence_window_ps")
    if window_ps is None:
        window_ps = max(3.0 * sigma_eff_ps, 200.0)
    window_ps = max(0.0, float(window_ps))
    window_s = window_ps * 1e-12

    eta_det = detector_profile.pde_in_window(window_ps)
    eta_total = clamp(float(eta_source) * float(eta_channel) * float(eta_det), 0.0, 1.0)

    dark_counts_cps = max(0.0, float(detector_profile.dark_counts_cps))
    noise_counts_cps = detector_profile.effective_noise_cps(background_counts_cps + raman_counts_cps)

    # Base Poisson noise parameter per side.
    b = max(0.0, float(noise_counts_cps)) * max(0.0, float(window_s))

    # Visibility-driven error for true single-pair coincidences.
    e_mis = misalignment_error_with_visibility_factor(protocol, pol_vis)
    v_mis = clamp(1.0 - 2.0 * float(e_mis), 0.0, 1.0)

    source_visibility = source.get("hom_visibility")
    if source_visibility is None:
        source_visibility = source.get("indistinguishability")
    v_src = clamp(float(source_visibility), 0.0, 1.0) if source_visibility is not None else 1.0

    v_eff = clamp(v_mis * v_src, 0.0, 1.0)
    e_vis = clamp((1.0 - v_eff) / 2.0, 0.0, 0.5)

    # Compute coincidence probabilities.
    if source["type"] == "spdc":
        mu = float(source["mu"])
        if not math.isfinite(mu) or mu < 0.0:
            raise ValueError(f"SPDC requires source.mu >= 0, got {mu!r}")

        Q, Q0 = _spdc_total_coincidence(mu=mu, eta=eta_total, b=b)
        Q_true, Q_true0 = _spdc_true_coincidence(mu=mu, eta=eta_total, b=b)
    else:
        source_profile = build_source_profile(source)
        emission_prob = clamp(float(source_profile.emission_prob), 0.0, 1.0)
        p_multi = clamp(float(source_profile.p_multi), 0.0, 1.0)
        # Simple 0/1/2-pair mixture for emitter sources.
        p0 = 1.0 - emission_prob
        p1 = emission_prob * (1.0 - p_multi)
        p2 = emission_prob * p_multi

        Q = (
            p0 * _q_click_side(eta=eta_total, b=b, n_pairs=0) ** 2
            + p1 * _q_click_side(eta=eta_total, b=b, n_pairs=1) ** 2
            + p2 * _q_click_side(eta=eta_total, b=b, n_pairs=2) ** 2
        )
        Q0 = (
            p0 * _q_click_side(eta=eta_total, b=0.0, n_pairs=0) ** 2
            + p1 * _q_click_side(eta=eta_total, b=0.0, n_pairs=1) ** 2
            + p2 * _q_click_side(eta=eta_total, b=0.0, n_pairs=2) ** 2
        )

        Q_true0 = p1 * _q_true_given_n(eta=eta_total, n_pairs=1) + p2 * _q_true_given_n(eta=eta_total, n_pairs=2)
        Q_true = math.exp(-2.0 * b) * Q_true0

    Q = clamp(float(Q), 0.0, 1.0)
    Q_true = clamp(float(Q_true), 0.0, Q)
    Q_acc = clamp(float(Q - Q_true), 0.0, 1.0)

    # Decompose accidentals into multi-pair (no-noise) vs noise-involved.
    Q0 = clamp(float(Q0), 0.0, 1.0)
    Q_true0 = clamp(float(Q_true0), 0.0, 1.0)
    Q_acc_mp = math.exp(-2.0 * b) * max(0.0, Q0 - Q_true0)
    Q_acc_mp = clamp(float(Q_acc_mp), 0.0, Q_acc)
    Q_acc_noise = clamp(float(Q_acc - Q_acc_mp), 0.0, Q_acc)

    if Q <= 0.0:
        qber_total = 0.0
    else:
        qber_total = (e_vis * Q_true + 0.5 * (Q_acc_mp + Q_acc_noise)) / Q
    qber_total = clamp(float(qber_total), 0.0, 0.5)
    fidelity = clamp(1.0 - qber_total, 0.0, 1.0)

    # QBER contribution breakdown terms.
    q_vis_total = (e_vis * Q_true / Q) if Q > 0.0 else 0.0
    q_multi = (0.5 * Q_acc_mp / Q) if Q > 0.0 else 0.0
    q_dark = (0.5 * Q_acc_noise / Q) if Q > 0.0 else 0.0

    # Split visibility-driven contribution between misalignment and source visibility.
    loss_mis = 1.0 - v_mis
    loss_src = 1.0 - v_src
    loss_sum = loss_mis + loss_src
    if loss_sum > 0.0:
        w_mis = loss_mis / loss_sum
        w_src = loss_src / loss_sum
    else:
        w_mis = 0.0
        w_src = 0.0
    q_mis = clamp(float(q_vis_total * w_mis), 0.0, 0.5)
    q_src = clamp(float(q_vis_total * w_src), 0.0, 0.5)

    # Enforce decomposition consistency (numerical).
    qber_total = clamp(float(q_multi + q_dark + q_mis + q_src), 0.0, 0.5)
    fidelity = clamp(1.0 - qber_total, 0.0, 1.0)

    # Event rate and dead-time saturation use coincidence probability Q.
    r_herald = rep_rate_hz * Q

    dead_time_s = float(detector["dead_time_ns"]) * 1e-9
    dead_time_model = detector.get("dead_time_model")
    r_herald, _ = apply_dead_time(r_herald, dead_time_s, model=dead_time_model)

    sifting = float(protocol.get("sifting_factor", 0.5) or 0.5)
    sifting = clamp(sifting, 0.0, 1.0)
    f_ec = max(1.0, float(protocol.get("ec_efficiency", 1.16) or 1.16))
    h2 = binary_entropy(qber_total)
    privacy_term_asymptotic = max(0.0, 1.0 - f_ec * h2 - h2)

    fk = apply_composable_finite_key(
        finite_key_cfg=scenario.get("finite_key"),
        sifting=sifting,
        privacy_term_asymptotic=privacy_term_asymptotic,
    )

    key_rate = r_herald * fk.sifting_effective * fk.privacy_term_effective

    q_dark_detector = q_background = q_raman = 0.0
    if q_dark > 0.0:
        denom_noise = max(1e-15, noise_counts_cps)
        q_dark_detector = q_dark * (dark_counts_cps / denom_noise)
        q_background = q_dark * (background_counts_cps / denom_noise)
        q_raman = q_dark * (raman_counts_cps / denom_noise)

    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=float(r_herald),
        key_rate_bps=float(key_rate),
        qber_total=float(qber_total),
        fidelity=float(fidelity),
        p_pair=float(Q_true),
        p_false=float(Q_acc),
        q_multi=float(q_multi),
        q_dark=float(q_dark),
        q_timing=0.0,
        q_misalignment=float(q_mis),
        q_source=float(q_src),
        q_dark_detector=float(q_dark_detector),
        q_background=float(q_background),
        q_raman=float(q_raman),
        background_counts_cps=float(background_counts_cps),
        raman_counts_cps=float(raman_counts_cps),
        finite_key_enabled=bool(fk.enabled),
        privacy_term_asymptotic=float(privacy_term_asymptotic),
        privacy_term_effective=float(fk.privacy_term_effective),
        finite_key_penalty=float(fk.finite_key_penalty),
        loss_db=float(total_loss_db),
        protocol_name="bbm92",
        finite_key_epsilon=float(fk.security_epsilon),
    )


def _q_click_side(*, eta: float, b: float, n_pairs: int) -> float:
    """Probability a side registers >=1 click given n pairs and noise mean b."""

    eta = clamp(float(eta), 0.0, 1.0)
    b = max(0.0, float(b))
    n = max(0, int(n_pairs))
    return clamp(1.0 - ((1.0 - eta) ** n) * math.exp(-b), 0.0, 1.0)


def _q_true_given_n(*, eta: float, n_pairs: int) -> float:
    """True single-pair coincidence probability conditioned on n pairs, no noise."""

    eta = clamp(float(eta), 0.0, 1.0)
    n = max(0, int(n_pairs))
    if n <= 0:
        return 0.0
    return float(n * (eta**2) * ((1.0 - eta) ** (2 * (n - 1))))


def _spdc_total_coincidence(*, mu: float, eta: float, b: float) -> tuple[float, float]:
    """Return (Q_total, Q_total_no_noise) for SPDC."""

    mu = max(0.0, float(mu))
    eta = clamp(float(eta), 0.0, 1.0)
    b = max(0.0, float(b))

    exp_b = math.exp(-b)
    exp_2b = math.exp(-2.0 * b)
    d1 = 1.0 + mu * eta
    d2 = 1.0 + mu * (2.0 * eta - eta * eta)
    q_total = 1.0 - 2.0 * exp_b / d1 + exp_2b / d2
    q0 = 1.0 - 2.0 / d1 + 1.0 / d2
    return float(q_total), float(q0)


def _spdc_true_coincidence(*, mu: float, eta: float, b: float) -> tuple[float, float]:
    """Return (Q_true, Q_true_no_noise) for SPDC."""

    mu = max(0.0, float(mu))
    eta = clamp(float(eta), 0.0, 1.0)
    b = max(0.0, float(b))

    exp_2b = math.exp(-2.0 * b)
    d2 = 1.0 + mu * (2.0 * eta - eta * eta)
    q_true0 = (mu * (eta**2) / (d2**2)) if mu > 0.0 and d2 > 0.0 else 0.0
    q_true = exp_2b * q_true0
    return float(q_true), float(q_true0)
