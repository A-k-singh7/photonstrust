"""MDI-QKD key-rate model.

Implements the analytical model from:

- Feihu Xu, Marcos Curty, Bing Qi, Li Qian, Hoi-Kwong Lo,
  "Practical aspects of measurement-device-independent quantum key distribution",
  arXiv:1305.6965

Key anchors used:

- Asymptotic key rate: Eq. (1)
- Two-decoy Y11 bound: Sec. 4 / Table 2 / Eqs. (6)-(7)
- Coherent-state gain/QBER system model: Appendix B.2, Eqs. (B.4)-(B.12)
- Single-photon yield and phase error proxy: Appendix B.1, Eq. (B.1)
"""

from __future__ import annotations

import math

import numpy as np

from photonstrust.channels.engine import compute_channel_diagnostics
from photonstrust.channels.fiber import polarization_drift
from photonstrust.physics import build_detector_profile
from photonstrust.qkd_types import QKDResult
from photonstrust.qkd_protocols.common import (
    apply_dead_time,
    effective_coincidence_window_s,
    misalignment_error_with_visibility_factor,
    per_pulse_prob_from_rate,
    relay_split_distances_km,
)
from photonstrust.utils import binary_entropy, clamp


def compute_point_mdi_qkd(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    source = scenario.get("source", {}) or {}
    channel = scenario.get("channel", {}) or {}
    detector = scenario.get("detector", {}) or {}
    timing = scenario.get("timing", {}) or {}
    proto = scenario.get("protocol", {}) or {}

    channel_model = str(channel.get("model", "fiber")).lower()
    if channel_model != "fiber":
        raise ValueError(f"MDI_QKD currently supports fiber channel only, got model={channel_model!r}")

    rep_rate_hz = float(source.get("rep_rate_mhz", 0.0) or 0.0) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("source.rep_rate_mhz must be > 0 for MDI_QKD")

    relay_fraction = proto.get("relay_fraction")
    da_km, db_km = relay_split_distances_km(float(distance_km), relay_fraction)

    # Reuse the unified channel diagnostics per relay segment for attenuation/noise
    # decomposition while preserving relay-model semantics.
    seg_a = _relay_segment_channel_diag(channel=channel, distance_km=da_km, wavelength_nm=scenario.get("wavelength_nm", 1550.0))
    seg_b = _relay_segment_channel_diag(channel=channel, distance_km=db_km, wavelength_nm=scenario.get("wavelength_nm", 1550.0))
    ta = float(seg_a["eta_channel"])
    tb = float(seg_b["eta_channel"])

    eta_total = max(1e-300, ta * tb)
    loss_db = -10.0 * math.log10(eta_total)

    detector_profile = build_detector_profile(detector)

    # Timing window: use worst segment for dispersion.
    window_s = effective_coincidence_window_s(distance_km=max(da_km, db_km), channel=channel, detector=detector, timing=timing)
    window_ps = window_s * 1e12

    eta_d = detector_profile.pde_in_window(window_ps)
    if eta_d <= 0.0:
        # No detection efficiency -> no key.
        return _empty_result(distance_km=float(distance_km), loss_db=loss_db)

    # Background/dark probability per detector per window.
    dark_cps = float(detector_profile.dark_counts_cps)
    det_bg_cps = float(detector_profile.background_counts_cps)
    # Keep backward-compatible channel-background semantics (configured value is
    # interpreted as aggregate channel background contribution, not per segment).
    ch_bg_cps = float(channel.get("background_counts_cps", 0.0) or 0.0)
    raman_cps = float(seg_a.get("raman_counts_cps", 0.0) or 0.0) + float(seg_b.get("raman_counts_cps", 0.0) or 0.0)
    noise_cps = detector_profile.effective_noise_cps(ch_bg_cps + raman_cps)
    y0 = per_pulse_prob_from_rate(noise_cps, window_s)
    y0 = clamp(y0, 0.0, 1.0)

    pol_vis = 1.0
    coherence_length = channel.get("polarization_coherence_length_km")
    if coherence_length is not None:
        pol_vis = polarization_drift(float(distance_km), float(coherence_length))
    ed = misalignment_error_with_visibility_factor(proto, pol_vis)
    f_ec = float(proto.get("ec_efficiency", 1.16) or 1.16)
    f_ec = max(1.0, f_ec)

    # Intensities: signal mu and decoys nu, omega.
    mu = proto.get("mu")
    nu = proto.get("nu")
    omega = proto.get("omega")
    if mu is None or nu is None:
        raise ValueError("MDI_QKD requires protocol.mu and protocol.nu")
    mu = float(mu)
    nu = float(nu)
    omega = float(omega if omega is not None else 0.0)
    if not (mu > nu >= omega >= 0.0):
        raise ValueError(f"MDI_QKD requires mu > nu >= omega >= 0, got mu={mu} nu={nu} omega={omega}")

    # Allow asymmetric intensity settings.
    mu_a = float(proto.get("mu_a", mu))
    mu_b = float(proto.get("mu_b", mu))
    nu_a = float(proto.get("nu_a", nu))
    nu_b = float(proto.get("nu_b", nu))
    om_a = float(proto.get("omega_a", omega))
    om_b = float(proto.get("omega_b", omega))

    # Gain/QBER for signal intensities.
    qz_sig, ez_sig = _gain_qber_z(mu_a=mu_a, mu_b=mu_b, ta=ta, tb=tb, eta_d=eta_d, y0=y0, ed=ed, proto=proto)

    # Finite two-decoy estimate for Y11_Z (lower bound), per Xu et al. Table 2 / Eq. (6)-(7).
    y11_z_l = _y11_z_lower_bound_two_decoy(
        mu_a=mu_a,
        mu_b=mu_b,
        nu_a=nu_a,
        nu_b=nu_b,
        om_a=om_a,
        om_b=om_b,
        ta=ta,
        tb=tb,
        eta_d=eta_d,
        y0=y0,
        ed=ed,
        proto=proto,
    )

    # Single-photon phase error proxy from Appendix B.1, Eq. (B.1).
    y11 = _y11_single_photon(ta=ta, tb=tb, eta_d=eta_d, y0=y0)
    e11_x = _e11_x_single_photon(ta=ta, tb=tb, eta_d=eta_d, y0=y0, ed=ed, y11=y11)

    p11_z = mu_a * mu_b * math.exp(-(mu_a + mu_b))

    # Asymptotic key rate per pulse pair (Eq. (1)).
    r_pulse = p11_z * y11_z_l * max(0.0, 1.0 - binary_entropy(e11_x)) - qz_sig * f_ec * binary_entropy(ez_sig)
    r_pulse = max(0.0, float(r_pulse))

    # Overall sifting/scaling knob (defaults to 1.0 for relay protocols).
    sifting = float(proto.get("sifting_factor", 1.0) or 1.0)
    sifting = clamp(sifting, 0.0, 1.0)

    key_rate_bps = rep_rate_hz * sifting * r_pulse
    event_rate_hz = rep_rate_hz * qz_sig

    # Dead-time saturation (non-paralyzable default; matches stochastic detector semantics).
    dead_time_s = float(detector.get("dead_time_ns", 0.0) or 0.0) * 1e-9
    dead_time_model = detector.get("dead_time_model")
    event_rate_hz_out, sat = apply_dead_time(event_rate_hz, dead_time_s, model=dead_time_model)
    event_rate_hz = event_rate_hz_out
    key_rate_bps = float(key_rate_bps) * sat

    qber_total = clamp(float(ez_sig), 0.0, 0.5)
    fidelity = clamp(1.0 - qber_total, 0.0, 1.0)

    p_single = p11_z * y11_z_l
    p_total = qz_sig
    p_false = max(0.0, p_total - p_single)

    # Rough attribution of QBER to noise sources (for v1.0-style error budget fields).
    bg_cps = max(0.0, det_bg_cps + ch_bg_cps)
    denom_noise = max(1e-30, dark_cps + bg_cps + raman_cps)
    q_dark_detector = qber_total * (dark_cps / denom_noise)
    q_background = qber_total * (bg_cps / denom_noise)
    q_raman = qber_total * (raman_cps / denom_noise)

    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=float(event_rate_hz),
        key_rate_bps=float(key_rate_bps),
        qber_total=float(qber_total),
        fidelity=float(fidelity),
        p_pair=float(p_single),
        p_false=float(p_false),
        q_multi=0.0,
        q_dark=float(p_false / p_total) if p_total > 0 else 0.0,
        q_timing=0.0,
        q_misalignment=float(ed),
        q_source=0.0,
        q_dark_detector=float(q_dark_detector),
        q_background=float(q_background),
        q_raman=float(q_raman),
        background_counts_cps=float(bg_cps),
        raman_counts_cps=float(raman_cps),
        finite_key_enabled=False,
        privacy_term_asymptotic=0.0,
        privacy_term_effective=0.0,
        finite_key_penalty=0.0,
        loss_db=float(loss_db),
    )


def _relay_segment_channel_diag(*, channel: dict, distance_km: float, wavelength_nm: float | None) -> dict:
    """Unified channel diagnostics for one relay segment.

    Relay key-rate models treat polarization drift as a visibility term in QBER,
    so we disable attenuation-side polarization here to preserve legacy behavior.
    """

    channel_cfg = dict(channel)
    channel_cfg["model"] = "fiber"
    channel_cfg["polarization_coherence_length_km"] = None
    return compute_channel_diagnostics(
        distance_km=float(distance_km),
        wavelength_nm=float(wavelength_nm or 1550.0),
        channel_cfg=channel_cfg,
    )


def _empty_result(distance_km: float, loss_db: float) -> QKDResult:
    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=0.0,
        key_rate_bps=0.0,
        qber_total=0.0,
        fidelity=1.0,
        p_pair=0.0,
        p_false=0.0,
        q_multi=0.0,
        q_dark=0.0,
        q_timing=0.0,
        q_misalignment=0.0,
        q_source=0.0,
        q_dark_detector=0.0,
        q_background=0.0,
        q_raman=0.0,
        background_counts_cps=0.0,
        raman_counts_cps=0.0,
        finite_key_enabled=False,
        privacy_term_asymptotic=0.0,
        privacy_term_effective=0.0,
        finite_key_penalty=0.0,
        loss_db=float(loss_db),
    )


def _i0(x: float) -> float:
    # numpy provides modified Bessel I0.
    return float(np.i0(float(x)))


def _gain_qber_z(
    *,
    mu_a: float,
    mu_b: float,
    ta: float,
    tb: float,
    eta_d: float,
    y0: float,
    ed: float,
    proto: dict,
) -> tuple[float, float]:
    """Return (QZ, EZ) for coherent-state inputs in Z basis."""

    # Per-channel misalignment proxy used by Appendix B.2.
    ed1 = proto.get("ed1")
    if ed1 is None:
        ed1 = 0.5 * float(ed)
    ed1 = clamp(float(ed1), 0.0, 0.5)

    gamma_a = math.sqrt(max(0.0, float(mu_a)) * max(0.0, ta) * float(eta_d))
    gamma_b = math.sqrt(max(0.0, float(mu_b)) * max(0.0, tb) * float(eta_d))
    beta = gamma_a * gamma_b
    gamma = gamma_a**2 + gamma_b**2
    lam = gamma_a * gamma_b * math.sqrt(max(0.0, ed1 * (1.0 - ed1)))
    omega = gamma_a**2 + ed1 * (gamma_b**2 - gamma_a**2)

    one_minus_y0 = 1.0 - clamp(float(y0), 0.0, 1.0)
    pref = 2.0 * math.exp(-gamma / 2.0) * (one_minus_y0**2)
    common = (one_minus_y0**2) * math.exp(-gamma / 2.0)

    a = one_minus_y0 * math.exp(-gamma * (1.0 - ed1) / 2.0) * _i0(ed1 * beta)
    b = one_minus_y0 * math.exp(-gamma * ed1 / 2.0) * _i0(beta * (1.0 - ed1))

    qhh_psi_plus = pref * (_i0(beta) + common - a - b)
    qhh_psi_minus = pref * (_i0(beta * (1.0 - 2.0 * ed1)) + common - a - b)
    qhh = qhh_psi_plus + qhh_psi_minus

    c = one_minus_y0 * math.exp(-omega / 2.0) * _i0(lam)
    d = one_minus_y0 * math.exp(-(gamma - omega) / 2.0) * _i0(lam)

    qhv_psi_plus = pref * (_i0(2.0 * lam) + common - c - d)
    qhv_psi_minus = pref * (1.0 + common - c - d)
    qhv = qhv_psi_plus + qhv_psi_minus

    qz = max(0.0, float(qhh + qhv / 2.0))
    denom = max(1e-30, float(qhh + qhv))
    ez = clamp(float(qhh) / denom, 0.0, 0.5)
    return qz, ez


def _y11_single_photon(*, ta: float, tb: float, eta_d: float, y0: float) -> float:
    """Single-photon yield Y11 from Xu et al., Appendix B.1."""

    one_minus_y0 = 1.0 - clamp(float(y0), 0.0, 1.0)
    a = max(0.0, float(ta)) * float(eta_d)
    b = max(0.0, float(tb)) * float(eta_d)

    y11 = (
        4.0 * (y0**2) * (1.0 - a) * (1.0 - b)
        + 2.0 * y0 * (a + b - 1.5 * a * b)
        + 0.5 * a * b
    )
    return max(0.0, float(one_minus_y0**2 * y11))


def _e11_x_single_photon(*, ta: float, tb: float, eta_d: float, y0: float, ed: float, y11: float) -> float:
    """Single-photon phase error proxy e11^X from Xu et al., Appendix B.1."""

    one_minus_y0 = 1.0 - clamp(float(y0), 0.0, 1.0)
    ed = clamp(float(ed), 0.0, 0.5)
    numer = max(0.0, float(ta)) * max(0.0, float(tb)) * float(eta_d) ** 2
    numer *= (1.0 - ed) ** 2 * (one_minus_y0**2)
    denom = max(1e-30, 4.0 * max(1e-30, float(y11)))
    e = 0.5 - numer / denom
    return clamp(float(e), 0.0, 0.5)


def _y11_z_lower_bound_two_decoy(
    *,
    mu_a: float,
    mu_b: float,
    nu_a: float,
    nu_b: float,
    om_a: float,
    om_b: float,
    ta: float,
    tb: float,
    eta_d: float,
    y0: float,
    ed: float,
    proto: dict,
) -> float:
    # Compute the required gains Q^Z for the intensity pairs.
    def qz(qa: float, qb: float) -> float:
        return _gain_qber_z(mu_a=qa, mu_b=qb, ta=ta, tb=tb, eta_d=eta_d, y0=y0, ed=ed, proto=proto)[0]

    qm1 = (
        qz(nu_a, nu_b) * math.exp(nu_a + nu_b)
        + qz(om_a, om_b) * math.exp(om_a + om_b)
        - qz(nu_a, om_b) * math.exp(nu_a + om_b)
        - qz(om_a, nu_b) * math.exp(om_a + nu_b)
    )
    qm2 = (
        qz(mu_a, mu_b) * math.exp(mu_a + mu_b)
        + qz(om_a, om_b) * math.exp(om_a + om_b)
        - qz(mu_a, om_b) * math.exp(mu_a + om_b)
        - qz(om_a, mu_b) * math.exp(om_a + mu_b)
    )

    # Choose which cross term to eliminate (Xu et al., Eq. (6)-(7)).
    left = (mu_a + om_a) / max(1e-30, (nu_a + om_a))
    right = (mu_b + om_b) / max(1e-30, (nu_b + om_b))

    denom_common = (mu_a - om_a) * (mu_b - om_b) * (nu_a - om_a) * (nu_b - om_b)
    if denom_common == 0.0:
        return 0.0

    if left <= right:
        denom = denom_common * (mu_a - nu_a)
        numer = (mu_a**2 - om_a**2) * (mu_b - om_b) * qm1 - (nu_a**2 - om_a**2) * (nu_b - om_b) * qm2
    else:
        denom = denom_common * (mu_b - nu_b)
        numer = (mu_b**2 - om_b**2) * (mu_a - om_a) * qm1 - (nu_b**2 - om_b**2) * (nu_a - om_a) * qm2

    if denom == 0.0:
        return 0.0
    y11_l = numer / denom
    return max(0.0, float(y11_l))
