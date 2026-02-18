"""PM-QKD / TF-QKD key-rate model.

Implements the analytical (simulation-ready) model from:

- Xiongfeng Ma, Pan Zeng, Hongwei Zhou,
  "Phase-Matching Quantum Key Distribution",
  Phys. Rev. X 8, 031043 (2018).
  arXiv:1805.05538

Key anchors used (arXiv:1805.05538):

- Practical key rate with phase slicing: Appendix B.2, Eq. (B23)
- Total gain Q_mu: Appendix B.2, Eq. (B14)
- QBER E^Z_mu: Appendix B.2, Eq. (B22) with e_delta from Eq. (B19)
- k-photon yields Y_k: Appendix B.2, Eq. (B13) (approx.)
- k-photon bit error e_k^Z: Appendix B.2, Eq. (B20) (approx.)
- Phase error bound: Appendix B.2, Eq. (B27) (truncated at k=0,1,3,5 with
  worst-case assignment to remaining components, as in the paper's MATLAB
  reference code).

Notes:

- This is a relay-based protocol family. The PLOB repeaterless bound is not a
  valid sanity gate for the end-to-end distance because the physical model is
  two-segment (Alice->relay and Bob->relay).
- The paper's Appendix B.2 assumes symmetric links. We support asymmetric link
  splits by using an effective transmittance eta = sqrt(eta_a * eta_b), which
  preserves the single-photon interference scaling term.
"""

from __future__ import annotations

import math

from photonstrust.channels.engine import compute_channel_diagnostics
from photonstrust.channels.fiber import polarization_drift
from photonstrust.physics import build_detector_profile
from photonstrust.qkd_protocols.common import (
    apply_dead_time,
    effective_coincidence_window_s,
    misalignment_error_with_visibility_factor,
    per_pulse_prob_from_rate,
    relay_split_distances_km,
)
from photonstrust.qkd_types import QKDResult
from photonstrust.utils import binary_entropy, clamp


def compute_point_pm_qkd(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
    *,
    tf_variant: bool = False,
) -> QKDResult:
    """Compute a PM-QKD/TF-QKD point.

    The TF-QKD surface is exposed as a variant flag on the same analytical model
    (with identical math by default). If future variants need additional
    assumptions, they can branch on `tf_variant`.
    """

    source = scenario.get("source", {}) or {}
    channel = scenario.get("channel", {}) or {}
    detector = scenario.get("detector", {}) or {}
    timing = scenario.get("timing", {}) or {}
    proto = scenario.get("protocol", {}) or {}

    channel_model = str(channel.get("model", "fiber")).lower()
    if channel_model != "fiber":
        raise ValueError(f"PM_QKD/TF_QKD currently supports fiber channel only, got model={channel_model!r}")

    rep_rate_hz = float(source.get("rep_rate_mhz", 0.0) or 0.0) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("source.rep_rate_mhz must be > 0 for PM_QKD/TF_QKD")

    relay_fraction = proto.get("relay_fraction")
    da_km, db_km = relay_split_distances_km(float(distance_km), relay_fraction)

    seg_a = _relay_segment_channel_diag(channel=channel, distance_km=da_km, wavelength_nm=scenario.get("wavelength_nm", 1550.0))
    seg_b = _relay_segment_channel_diag(channel=channel, distance_km=db_km, wavelength_nm=scenario.get("wavelength_nm", 1550.0))
    ta = float(seg_a["eta_channel"])
    tb = float(seg_b["eta_channel"])

    eta_link_product = max(1e-300, float(ta) * float(tb))
    loss_db = -10.0 * math.log10(eta_link_product)

    detector_profile = build_detector_profile(detector)

    # Timing window: use the longer segment for dispersion.
    window_s = effective_coincidence_window_s(
        distance_km=max(da_km, db_km),
        channel=channel,
        detector=detector,
        timing=timing,
    )
    window_ps = window_s * 1e12

    eta_d = detector_profile.pde_in_window(window_ps)
    if eta_d <= 0.0:
        return _empty_result(distance_km=float(distance_km), loss_db=float(loss_db))

    dark_cps = float(detector_profile.dark_counts_cps)
    det_bg_cps = float(detector_profile.background_counts_cps)
    # Keep backward-compatible channel-background semantics (configured value is
    # interpreted as aggregate channel background contribution, not per segment).
    ch_bg_cps = float(channel.get("background_counts_cps", 0.0) or 0.0)
    raman_cps = float(seg_a.get("raman_counts_cps", 0.0) or 0.0) + float(seg_b.get("raman_counts_cps", 0.0) or 0.0)

    noise_cps = detector_profile.effective_noise_cps(ch_bg_cps + raman_cps)

    # Dark-count probability per detector per window.
    pd = per_pulse_prob_from_rate(noise_cps, window_s)
    # The Appendix-B approximation assumes pd << 1.
    pd = clamp(float(pd), 0.0, 0.499999)

    mu = proto.get("mu")
    if mu is None:
        raise ValueError("PM_QKD/TF_QKD requires protocol.mu")
    mu = float(mu)
    if not math.isfinite(mu) or mu <= 0.0:
        raise ValueError(f"PM_QKD/TF_QKD requires protocol.mu > 0, got mu={mu}")

    m_raw = proto.get("phase_slices")
    if m_raw is None:
        m_raw = proto.get("M")
    if m_raw is None:
        m_raw = 16
    m = int(m_raw)
    if m < 2:
        raise ValueError(f"PM_QKD/TF_QKD requires phase_slices (M) >= 2, got {m}")

    f_ec = float(proto.get("ec_efficiency", 1.16) or 1.16)
    f_ec = max(1.0, f_ec)

    # Effective per-photon transmittance. For asymmetric links, PM/TF
    # interference scaling follows sqrt(eta_a * eta_b).
    eta_a = float(ta) * float(eta_d)
    eta_b = float(tb) * float(eta_d)
    eta = math.sqrt(max(0.0, eta_a * eta_b))
    eta = clamp(float(eta), 0.0, 1.0)
    if eta <= 0.0:
        return _empty_result(distance_km=float(distance_km), loss_db=float(loss_db))

    # Misalignment term from Appendix B.2 (Eq. (B19)), plus optional explicit
    # misalignment floor from PhotonTrust scenario config.
    edelta = _edelta_from_phase_slices(m)
    pol_vis = 1.0
    coherence_length = channel.get("polarization_coherence_length_km")
    if coherence_length is not None:
        pol_vis = polarization_drift(float(distance_km), float(coherence_length))
    ed_hw = misalignment_error_with_visibility_factor(proto, pol_vis)
    e_mis = clamp(float(edelta + ed_hw), 0.0, 0.5)

    # Appendix B.2 formulas.
    y0 = 2.0 * pd
    y1 = _yield_k(pd=pd, eta=eta, k=1)
    y3 = _yield_k(pd=pd, eta=eta, k=3)
    y5 = _yield_k(pd=pd, eta=eta, k=5)

    qmu = 1.0 - (1.0 - 2.0 * pd) * math.exp(-mu * eta)
    qmu = clamp(float(qmu), 0.0, 1.0)
    if qmu <= 0.0:
        return _empty_result(distance_km=float(distance_km), loss_db=float(loss_db))

    # Dead-time saturation (non-paralyzable default; matches stochastic detector semantics).
    dead_time_s = float(detector.get("dead_time_ns", 0.0) or 0.0) * 1e-9
    dead_time_model = detector.get("dead_time_model")
    raw_event_rate_hz = rep_rate_hz * qmu
    _, sat = apply_dead_time(raw_event_rate_hz, dead_time_s, model=dead_time_model)

    # Z-basis QBER (Eq. (B22)) using the paper's corrected expression.
    ez = ((pd + eta * mu * e_mis) * math.exp(-eta * mu)) / max(1e-30, qmu)
    ez = clamp(float(ez), 0.0, 0.5)

    # Phase error bound (Eq. (B27) truncation in paper's MATLAB code).
    q0, q1, q3, q5 = _clicked_fractions(mu=mu, qmu=qmu, y0=y0, y1=y1, y3=y3, y5=y5)
    e0 = 0.5
    e1z = _bit_error_k(pd=pd, eta=eta, e_mis=e_mis, k=1, yk=y1)
    e3z = _bit_error_k(pd=pd, eta=eta, e_mis=e_mis, k=3, yk=y3)
    e5z = _bit_error_k(pd=pd, eta=eta, e_mis=e_mis, k=5, yk=y5)
    ex = q0 * e0 + q1 * e1z + q3 * e3z + q5 * e5z + max(0.0, 1.0 - (q0 + q1 + q3 + q5))
    ex = clamp(float(ex), 0.0, 0.5)

    # Secret fraction per signal use (Eq. (B23)).
    r_pm = 1.0 - f_ec * binary_entropy(ez) - binary_entropy(ex)
    r_pm = max(0.0, float(r_pm))

    phase_sift = 2.0 / float(m)
    extra_sift = float(proto.get("sifting_factor", 1.0) or 1.0)
    extra_sift = clamp(extra_sift, 0.0, 1.0)

    key_rate_bps = rep_rate_hz * extra_sift * phase_sift * qmu * r_pm
    key_rate_bps = max(0.0, float(key_rate_bps)) * sat

    event_rate_hz = (rep_rate_hz * qmu) * sat
    qber_total = ez
    fidelity = clamp(1.0 - qber_total, 0.0, 1.0)

    # Rough false-event proxy: vacuum contribution to valid detections.
    p0 = math.exp(-mu)
    p_false = p0 * y0
    p_pair = max(0.0, qmu - p_false)

    denom_noise = max(1e-30, dark_cps + (det_bg_cps + ch_bg_cps) + raman_cps)
    q_dark_detector = qber_total * (dark_cps / denom_noise)
    q_background = qber_total * ((det_bg_cps + ch_bg_cps) / denom_noise)
    q_raman = qber_total * (raman_cps / denom_noise)

    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=float(event_rate_hz),
        key_rate_bps=float(key_rate_bps),
        qber_total=float(qber_total),
        fidelity=float(fidelity),
        p_pair=float(p_pair),
        p_false=float(p_false),
        q_multi=0.0,
        q_dark=float(p_false / qmu) if qmu > 0 else 0.0,
        q_timing=0.0,
        q_misalignment=float(e_mis),
        q_source=0.0,
        q_dark_detector=float(q_dark_detector),
        q_background=float(q_background),
        q_raman=float(q_raman),
        background_counts_cps=float(det_bg_cps + ch_bg_cps),
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


def _yield_k(*, pd: float, eta: float, k: int) -> float:
    """Yield Y_k approximation (Eq. (B13))."""

    eta = clamp(float(eta), 0.0, 1.0)
    pd = clamp(float(pd), 0.0, 0.499999)
    k = int(k)
    return clamp(1.0 - (1.0 - 2.0 * pd) * (1.0 - eta) ** k, 0.0, 1.0)


def _bit_error_k(*, pd: float, eta: float, e_mis: float, k: int, yk: float) -> float:
    """Bit error rate e_k^Z approximation (Eq. (B20))."""

    yk = float(yk)
    if yk <= 0.0:
        return 0.5
    eta = clamp(float(eta), 0.0, 1.0)
    pd = clamp(float(pd), 0.0, 0.499999)
    e_mis = clamp(float(e_mis), 0.0, 0.5)
    k = int(k)

    numer = pd * (1.0 - eta) ** k + e_mis * (1.0 - (1.0 - eta) ** k)
    return clamp(float(numer / yk), 0.0, 0.5)


def _clicked_fractions(
    *,
    mu: float,
    qmu: float,
    y0: float,
    y1: float,
    y3: float,
    y5: float,
) -> tuple[float, float, float, float]:
    """Clicked fractions q_k from Eq. (B25) for k=0,1,3,5."""

    qmu = max(1e-30, float(qmu))
    mu = float(mu)
    p0 = math.exp(-mu)

    q0 = float(y0) * p0 / qmu
    q1 = float(y1) * (mu * p0) / qmu
    q3 = float(y3) * (mu**3 * p0) / (math.factorial(3) * qmu)
    q5 = float(y5) * (mu**5 * p0) / (math.factorial(5) * qmu)

    # Numerical safety; these are conditional fractions and should sum <= 1.
    q0 = clamp(q0, 0.0, 1.0)
    q1 = clamp(q1, 0.0, 1.0)
    q3 = clamp(q3, 0.0, 1.0)
    q5 = clamp(q5, 0.0, 1.0)
    return q0, q1, q3, q5


def _edelta_from_phase_slices(m: int) -> float:
    """Misalignment proxy e_delta from Eq. (B19)."""

    m = int(m)
    if m <= 0:
        return 0.0
    x = math.pi / float(m)
    return float(x - (float(m) / math.pi) ** 2 * (math.sin(x) ** 3))
