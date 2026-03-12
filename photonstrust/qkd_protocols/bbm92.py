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
from photonstrust.qkd_protocols.common import (
    apply_dead_time,
    misalignment_error_with_visibility_factor,
    relay_split_distances_km,
)
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

    topology = _resolve_entanglement_topology(protocol)
    wavelength_nm = float(scenario.get("wavelength_nm", 1550.0) or 1550.0)
    connector_loss_db = max(0.0, float(channel.get("connector_loss_db", 0.0) or 0.0))

    distance_a_km = float(distance_km)
    distance_b_km = float(distance_km)
    channel_a_cfg = dict(channel)
    channel_b_cfg = dict(channel)
    split_connector_loss = False
    if topology == "midpoint_source":
        distance_a_km, distance_b_km = relay_split_distances_km(float(distance_km), protocol.get("relay_fraction"))
        split_connector_loss = bool(protocol.get("split_connector_loss", True))
        if split_connector_loss:
            half_connector_loss = connector_loss_db * 0.5
            channel_a_cfg["connector_loss_db"] = half_connector_loss
            channel_b_cfg["connector_loss_db"] = half_connector_loss

    ch_diag_a = compute_channel_diagnostics(
        distance_km=float(distance_a_km),
        wavelength_nm=wavelength_nm,
        channel_cfg=channel_a_cfg,
    )
    ch_diag_b = compute_channel_diagnostics(
        distance_km=float(distance_b_km),
        wavelength_nm=wavelength_nm,
        channel_cfg=channel_b_cfg,
    )

    eta_channel_a = float(ch_diag_a["eta_channel"])
    eta_channel_b = float(ch_diag_b["eta_channel"])
    if topology == "midpoint_source":
        total_loss_db = _linear_to_db_loss(eta_channel_a * eta_channel_b)
    else:
        total_loss_db = float(ch_diag_a["total_loss_db"])

    channel_background_counts_cps_a = float(ch_diag_a.get("background_counts_cps", 0.0) or 0.0)
    channel_background_counts_cps_b = float(ch_diag_b.get("background_counts_cps", 0.0) or 0.0)
    raman_counts_cps_a = float(ch_diag_a.get("raman_counts_cps", 0.0) or 0.0)
    raman_counts_cps_b = float(ch_diag_b.get("raman_counts_cps", 0.0) or 0.0)

    pol_vis = 1.0
    if channel_model == "fiber":
        pol_vis_a = float(ch_diag_a.get("decomposition", {}).get("eta_polarization", 1.0) or 1.0)
        pol_vis_b = float(ch_diag_b.get("decomposition", {}).get("eta_polarization", 1.0) or 1.0)
        pol_vis = clamp(math.sqrt(max(0.0, pol_vis_a * pol_vis_b)), 0.0, 1.0)

    detector_background_counts_cps = float(detector.get("background_counts_cps", 0.0) or 0.0)
    background_counts_cps_a = max(0.0, float(channel_background_counts_cps_a) + float(detector_background_counts_cps))
    background_counts_cps_b = max(0.0, float(channel_background_counts_cps_b) + float(detector_background_counts_cps))
    raman_counts_cps_a = max(0.0, float(raman_counts_cps_a))
    raman_counts_cps_b = max(0.0, float(raman_counts_cps_b))
    background_counts_cps = 0.5 * (background_counts_cps_a + background_counts_cps_b)
    raman_counts_cps = 0.5 * (raman_counts_cps_a + raman_counts_cps_b)

    detector_profile = build_detector_profile(detector)

    eta_channel_a = clamp(float(eta_channel_a), 0.0, 1.0)
    eta_channel_b = clamp(float(eta_channel_b), 0.0, 1.0)
    eta_det_base = detector_profile.pde

    eta_total_a = clamp(float(eta_source) * float(eta_channel_a) * float(eta_det_base), 0.0, 1.0)
    eta_total_b = clamp(float(eta_source) * float(eta_channel_b) * float(eta_det_base), 0.0, 1.0)

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
    eta_total_a = clamp(float(eta_source) * float(eta_channel_a) * float(eta_det), 0.0, 1.0)
    eta_total_b = clamp(float(eta_source) * float(eta_channel_b) * float(eta_det), 0.0, 1.0)

    dark_counts_cps = max(0.0, float(detector_profile.dark_counts_cps))
    noise_counts_cps_a = detector_profile.effective_noise_cps(background_counts_cps_a + raman_counts_cps_a)
    noise_counts_cps_b = detector_profile.effective_noise_cps(background_counts_cps_b + raman_counts_cps_b)
    noise_counts_cps = 0.5 * (noise_counts_cps_a + noise_counts_cps_b)

    # Base Poisson noise parameter per side.
    b_a = max(0.0, float(noise_counts_cps_a)) * max(0.0, float(window_s))
    b_b = max(0.0, float(noise_counts_cps_b)) * max(0.0, float(window_s))

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

        Q, Q0 = _spdc_total_coincidence_asym(mu=mu, eta_a=eta_total_a, eta_b=eta_total_b, b_a=b_a, b_b=b_b)
        Q_true, Q_true0 = _spdc_true_coincidence_asym(mu=mu, eta_a=eta_total_a, eta_b=eta_total_b, b_a=b_a, b_b=b_b)
    else:
        source_profile = build_source_profile(source)
        emission_prob = clamp(float(source_profile.emission_prob), 0.0, 1.0)
        p_multi = clamp(float(source_profile.p_multi), 0.0, 1.0)
        # Simple 0/1/2-pair mixture for emitter sources.
        p0 = 1.0 - emission_prob
        p1 = emission_prob * (1.0 - p_multi)
        p2 = emission_prob * p_multi

        Q = (
            p0 * _q_click_side(eta=eta_total_a, b=b_a, n_pairs=0) * _q_click_side(eta=eta_total_b, b=b_b, n_pairs=0)
            + p1 * _q_click_side(eta=eta_total_a, b=b_a, n_pairs=1) * _q_click_side(eta=eta_total_b, b=b_b, n_pairs=1)
            + p2 * _q_click_side(eta=eta_total_a, b=b_a, n_pairs=2) * _q_click_side(eta=eta_total_b, b=b_b, n_pairs=2)
        )
        Q0 = (
            p0 * _q_click_side(eta=eta_total_a, b=0.0, n_pairs=0) * _q_click_side(eta=eta_total_b, b=0.0, n_pairs=0)
            + p1 * _q_click_side(eta=eta_total_a, b=0.0, n_pairs=1) * _q_click_side(eta=eta_total_b, b=0.0, n_pairs=1)
            + p2 * _q_click_side(eta=eta_total_a, b=0.0, n_pairs=2) * _q_click_side(eta=eta_total_b, b=0.0, n_pairs=2)
        )

        Q_true0 = p1 * _q_true_given_n_asym(eta_a=eta_total_a, eta_b=eta_total_b, n_pairs=1) + p2 * _q_true_given_n_asym(
            eta_a=eta_total_a,
            eta_b=eta_total_b,
            n_pairs=2,
        )
        Q_true = math.exp(-(b_a + b_b)) * Q_true0

    Q = clamp(float(Q), 0.0, 1.0)
    Q_true = clamp(float(Q_true), 0.0, Q)
    Q_acc = clamp(float(Q - Q_true), 0.0, 1.0)

    # Decompose accidentals into multi-pair (no-noise) vs noise-involved.
    Q0 = clamp(float(Q0), 0.0, 1.0)
    Q_true0 = clamp(float(Q_true0), 0.0, 1.0)
    Q_acc_mp = math.exp(-(b_a + b_b)) * max(0.0, Q0 - Q_true0)
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
    parallel_mode_count = _parallel_mode_count(source)
    r_herald_per_mode = rep_rate_hz * Q

    dead_time_s = float(detector["dead_time_ns"]) * 1e-9
    dead_time_model = detector.get("dead_time_model")
    r_herald_per_mode, _ = apply_dead_time(r_herald_per_mode, dead_time_s, model=dead_time_model)
    r_herald = r_herald_per_mode * parallel_mode_count

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
        protocol_diagnostics={
            "entanglement_topology": topology,
            "distance_a_km": float(distance_a_km),
            "distance_b_km": float(distance_b_km),
            "eta_channel_a": float(eta_channel_a),
            "eta_channel_b": float(eta_channel_b),
            "eta_channel_pair": float(clamp(eta_channel_a * eta_channel_b, 0.0, 1.0)),
            "parallel_mode_count": float(parallel_mode_count),
            "split_connector_loss": bool(split_connector_loss),
        },
    )


def _resolve_entanglement_topology(protocol: dict) -> str:
    raw = str(protocol.get("entanglement_topology", protocol.get("link_topology", "direct_link")) or "").strip().lower()
    if raw in {
        "midpoint_source",
        "source_in_middle",
        "relay_midpoint",
        "symmetric_two_arm",
        "two_arm",
    }:
        return "midpoint_source"
    return "direct_link"


def _parallel_mode_count(source: dict) -> float:
    try:
        value = float(source.get("parallel_mode_count", 1.0) or 1.0)
    except Exception:
        return 1.0
    if not math.isfinite(value) or value <= 0.0:
        return 1.0
    return max(1.0, value)


def _linear_to_db_loss(eta: float) -> float:
    eta = max(float(eta), 1e-300)
    return -10.0 * math.log10(eta)


def _q_click_side(*, eta: float, b: float, n_pairs: int) -> float:
    """Probability a side registers >=1 click given n pairs and noise mean b."""

    eta = clamp(float(eta), 0.0, 1.0)
    b = max(0.0, float(b))
    n = max(0, int(n_pairs))
    return clamp(1.0 - ((1.0 - eta) ** n) * math.exp(-b), 0.0, 1.0)


def _q_true_given_n(*, eta: float, n_pairs: int) -> float:
    """True single-pair coincidence probability conditioned on n pairs, no noise."""

    return _q_true_given_n_asym(eta_a=eta, eta_b=eta, n_pairs=n_pairs)


def _q_true_given_n_asym(*, eta_a: float, eta_b: float, n_pairs: int) -> float:
    """True single-pair coincidence probability for asymmetric side efficiencies."""

    eta_a = clamp(float(eta_a), 0.0, 1.0)
    eta_b = clamp(float(eta_b), 0.0, 1.0)
    n = max(0, int(n_pairs))
    if n <= 0:
        return 0.0
    return float(n * eta_a * eta_b * ((1.0 - eta_a) ** (n - 1)) * ((1.0 - eta_b) ** (n - 1)))


def _spdc_total_coincidence(*, mu: float, eta: float, b: float) -> tuple[float, float]:
    """Return (Q_total, Q_total_no_noise) for SPDC."""

    return _spdc_total_coincidence_asym(mu=mu, eta_a=eta, eta_b=eta, b_a=b, b_b=b)


def _spdc_total_coincidence_asym(*, mu: float, eta_a: float, eta_b: float, b_a: float, b_b: float) -> tuple[float, float]:
    """Return (Q_total, Q_total_no_noise) for SPDC with asymmetric side efficiencies/noise."""

    mu = max(0.0, float(mu))
    eta_a = clamp(float(eta_a), 0.0, 1.0)
    eta_b = clamp(float(eta_b), 0.0, 1.0)
    b_a = max(0.0, float(b_a))
    b_b = max(0.0, float(b_b))

    exp_a = math.exp(-b_a)
    exp_b = math.exp(-b_b)
    d_a = 1.0 + mu * eta_a
    d_b = 1.0 + mu * eta_b
    d_ab = 1.0 + mu * (eta_a + eta_b - eta_a * eta_b)
    q_total = 1.0 - exp_a / d_a - exp_b / d_b + (exp_a * exp_b) / d_ab
    q0 = 1.0 - 1.0 / d_a - 1.0 / d_b + 1.0 / d_ab
    return float(q_total), float(q0)


def _spdc_true_coincidence(*, mu: float, eta: float, b: float) -> tuple[float, float]:
    """Return (Q_true, Q_true_no_noise) for SPDC."""

    return _spdc_true_coincidence_asym(mu=mu, eta_a=eta, eta_b=eta, b_a=b, b_b=b)


def _spdc_true_coincidence_asym(*, mu: float, eta_a: float, eta_b: float, b_a: float, b_b: float) -> tuple[float, float]:
    """Return (Q_true, Q_true_no_noise) for SPDC with asymmetric side efficiencies/noise."""

    mu = max(0.0, float(mu))
    eta_a = clamp(float(eta_a), 0.0, 1.0)
    eta_b = clamp(float(eta_b), 0.0, 1.0)
    b_a = max(0.0, float(b_a))
    b_b = max(0.0, float(b_b))

    exp_pair_noise = math.exp(-(b_a + b_b))
    d_ab = 1.0 + mu * (eta_a + eta_b - eta_a * eta_b)
    q_true0 = (mu * eta_a * eta_b / (d_ab**2)) if mu > 0.0 and d_ab > 0.0 else 0.0
    q_true = exp_pair_noise * q_true0
    return float(q_true), float(q_true0)
