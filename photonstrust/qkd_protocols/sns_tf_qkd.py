"""Sending-or-Not-Sending Twin-Field QKD (SNS-TF-QKD) key-rate model.

Implements the SNS variant of TF-QKD that achieves O(sqrt(eta)) key-rate
scaling without requiring global phase locking.

Key references:
    - Wang, Yu, Hu, PRA 98, 062323 (2018) -- SNS protocol
    - Yu, Hu, Jiang, PRL 125, 010502 (2020) -- 4-intensity SNS
    - Jiang et al., PRA 100, 062334 (2019) -- finite-key SNS
    - Lucamarini, Yuan, Dynes, Shields, Nature 557, 400 (2018) -- TF-QKD

In the SNS protocol, Alice and Bob each independently decide to "send"
(with intensity mu_z in the Z window) or "not send" in each time window.
Key bits are generated only from the Z windows, while X windows (with
decoy intensities) are used for parameter estimation.

The key rate formula is:
    R = (2/N) * {s1_L * [1 - H(e1_ph_U)] - f_EC * n_t * H(E_mu)}

where:
    s1_L: lower bound on single-photon detection events
    e1_ph_U: upper bound on single-photon phase error rate
    n_t: total detection events in signal (Z) windows
    N: total number of pulses

Notes:
    - This is a relay-based protocol. The PLOB bound does not apply directly.
    - Rate scales as O(sqrt(eta)) vs O(eta) for BB84, enabling longer distances.
    - Supports asymmetric links via geometric mean transmittance.
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


def compute_point_sns_tf_qkd(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    """Compute an SNS-TF-QKD key-rate point.

    The protocol uses three or four intensity settings:
    - mu_z: signal intensity for Z windows (key generation)
    - mu_1: decoy intensity 1 for X windows (parameter estimation)
    - mu_2: decoy intensity 2 for X windows (lighter decoy)
    - vacuum (mu=0) for X windows

    Ref: Wang, Yu, Hu, PRA 98, 062323 (2018)
    """

    source = scenario.get("source", {}) or {}
    channel = scenario.get("channel", {}) or {}
    detector = scenario.get("detector", {}) or {}
    timing = scenario.get("timing", {}) or {}
    proto = scenario.get("protocol", {}) or {}

    channel_model = str(channel.get("model", "fiber")).lower()
    if channel_model != "fiber":
        raise ValueError(
            f"SNS-TF-QKD currently supports fiber channel only, got model={channel_model!r}"
        )

    rep_rate_hz = float(source.get("rep_rate_mhz", 0.0) or 0.0) * 1e6
    if rep_rate_hz <= 0.0:
        raise ValueError("source.rep_rate_mhz must be > 0 for SNS-TF-QKD")

    # Relay segment splitting
    relay_fraction = proto.get("relay_fraction")
    da_km, db_km = relay_split_distances_km(float(distance_km), relay_fraction)

    seg_a = _relay_segment_channel_diag(
        channel=channel, distance_km=da_km,
        wavelength_nm=scenario.get("wavelength_nm", 1550.0),
    )
    seg_b = _relay_segment_channel_diag(
        channel=channel, distance_km=db_km,
        wavelength_nm=scenario.get("wavelength_nm", 1550.0),
    )
    ta = float(seg_a["eta_channel"])
    tb = float(seg_b["eta_channel"])

    eta_link_product = max(1e-300, ta * tb)
    loss_db = -10.0 * math.log10(eta_link_product)

    # Detector
    detector_profile = build_detector_profile(detector)
    window_s = effective_coincidence_window_s(
        distance_km=max(da_km, db_km),
        channel=channel, detector=detector, timing=timing,
    )
    window_ps = window_s * 1e12
    eta_d = detector_profile.pde_in_window(window_ps)
    if eta_d <= 0.0:
        return _empty_result(float(distance_km), loss_db)

    # Noise
    noise_cps = detector_profile.effective_noise_cps(
        float(channel.get("background_counts_cps", 0.0) or 0.0)
        + float(seg_a.get("raman_counts_cps", 0.0) or 0.0)
        + float(seg_b.get("raman_counts_cps", 0.0) or 0.0)
    )
    pd = clamp(per_pulse_prob_from_rate(noise_cps, window_s), 0.0, 0.499999)

    # Protocol parameters
    mu_z = float(proto.get("mu_z", proto.get("mu", 0.3)) or 0.3)
    mu_1 = float(proto.get("mu_1", 0.1) or 0.1)
    mu_2 = float(proto.get("mu_2", 0.02) or 0.02)
    p_z = clamp(float(proto.get("p_z", 0.5) or 0.5), 0.01, 0.99)
    f_ec = max(1.0, float(proto.get("ec_efficiency", 1.16) or 1.16))

    if mu_z <= 0 or mu_1 <= 0 or mu_2 <= 0:
        raise ValueError("SNS-TF-QKD requires mu_z, mu_1, mu_2 > 0")

    # Effective per-photon transmittance: sqrt(eta_a * eta_b) scaling
    eta_a = ta * eta_d
    eta_b = tb * eta_d
    eta = clamp(math.sqrt(max(0.0, eta_a * eta_b)), 0.0, 1.0)
    if eta <= 0.0:
        return _empty_result(float(distance_km), loss_db)

    # Misalignment
    pol_vis = 1.0
    coherence_length = channel.get("polarization_coherence_length_km")
    if coherence_length is not None:
        pol_vis = polarization_drift(float(distance_km), float(coherence_length))
    e_mis = misalignment_error_with_visibility_factor(proto, pol_vis)

    # --- SNS parameter estimation (Wang et al. 2018) ---

    # Gains at each intensity
    S_z = _sns_gain(mu_z, eta, pd)  # signal gain
    S_1 = _sns_gain(mu_1, eta, pd)  # decoy 1 gain
    S_2 = _sns_gain(mu_2, eta, pd)  # decoy 2 gain
    S_0 = 2.0 * pd  # vacuum gain (Y_0)

    if S_z <= 0:
        return _empty_result(float(distance_km), loss_db)

    # Z-basis QBER
    E_z = _sns_error_rate(mu_z, eta, pd, e_mis)

    # Single-photon yield lower bound (Eq. 16 of Wang et al. 2018)
    s1_lower = _sns_single_photon_yield_bound(
        mu_z=mu_z, mu_1=mu_1, mu_2=mu_2,
        S_z=S_z, S_1=S_1, S_2=S_2, S_0=S_0,
    )

    if s1_lower <= 0:
        return _empty_result(float(distance_km), loss_db)

    # Phase error rate upper bound (Eq. 18 of Wang et al. 2018)
    # X-basis error rate for single-photon events
    T_1 = _sns_x_basis_error_count(mu_1, eta, pd, e_mis)
    e1_phase_upper = _sns_phase_error_bound(
        mu_1=mu_1, S_1=S_1, T_1=T_1, s1=s1_lower,
    )

    if e1_phase_upper >= 0.5:
        return _empty_result(float(distance_km), loss_db)

    # --- Key rate ---
    privacy = 1.0 - binary_entropy(e1_phase_upper)
    correction = f_ec * binary_entropy(E_z)

    key_rate_per_use = max(0.0, p_z * (s1_lower * privacy - S_z * correction))
    key_rate_bps = rep_rate_hz * key_rate_per_use

    # Dead time saturation
    dead_time_s = float(detector.get("dead_time_ns", 0.0) or 0.0) * 1e-9
    dead_time_model = detector.get("dead_time_model")
    raw_rate = rep_rate_hz * S_z
    _, sat = apply_dead_time(raw_rate, dead_time_s, model=dead_time_model)
    key_rate_bps *= sat

    # Background
    bg_cps = float(channel.get("background_counts_cps", 0.0) or 0.0)
    raman_cps = (
        float(seg_a.get("raman_counts_cps", 0.0) or 0.0)
        + float(seg_b.get("raman_counts_cps", 0.0) or 0.0)
    )

    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=0.0,
        key_rate_bps=key_rate_bps,
        qber_total=E_z,
        fidelity=1.0 - E_z,
        p_pair=0.0,
        p_false=float(pd),
        q_multi=0.0,
        q_dark=float(pd),
        q_timing=0.0,
        q_misalignment=float(e_mis),
        q_source=0.0,
        q_dark_detector=float(detector_profile.dark_counts_cps),
        q_background=float(bg_cps),
        q_raman=float(raman_cps),
        background_counts_cps=bg_cps,
        raman_counts_cps=raman_cps,
        finite_key_enabled=False,
        privacy_term_asymptotic=key_rate_per_use,
        privacy_term_effective=key_rate_per_use,
        finite_key_penalty=0.0,
        loss_db=loss_db,
        protocol_name="sns_tf_qkd",
        single_photon_yield_lb=s1_lower,
        single_photon_error_ub=e1_phase_upper,
        protocol_diagnostics={
            "mu_z": mu_z,
            "mu_1": mu_1,
            "mu_2": mu_2,
            "p_z": p_z,
            "eta": eta,
            "eta_a": eta_a,
            "eta_b": eta_b,
            "S_z": S_z,
            "S_1": S_1,
            "S_2": S_2,
            "S_0": S_0,
            "E_z": E_z,
            "s1_lower": s1_lower,
            "e1_phase_upper": e1_phase_upper,
            "privacy_term": privacy,
            "correction_term": correction,
        },
    )


# ---------------------------------------------------------------------------
# SNS gain and error formulas
# ---------------------------------------------------------------------------

def _sns_gain(mu: float, eta: float, pd: float) -> float:
    """Detection probability (gain) for intensity mu.

    Q_mu = 1 - (1 - 2*pd) * exp(-mu*eta)

    Ref: Wang et al., PRA 98, 062323 (2018), Eq. (10)
    """
    return clamp(1.0 - (1.0 - 2.0 * pd) * math.exp(-mu * eta), 0.0, 1.0)


def _sns_error_rate(mu: float, eta: float, pd: float, e_mis: float) -> float:
    """QBER for intensity mu in Z basis.

    E_mu = [pd + eta*mu*e_mis * exp(-eta*mu)] / Q_mu

    Ref: Wang et al., PRA 98, 062323 (2018), Eq. (12)
    """
    q = _sns_gain(mu, eta, pd)
    if q <= 0:
        return 0.5
    num = pd + eta * mu * e_mis * math.exp(-eta * mu)
    return clamp(num / q, 0.0, 0.5)


def _sns_x_basis_error_count(mu: float, eta: float, pd: float, e_mis: float) -> float:
    """Error count in X basis for decoy intensity mu.

    T_mu = S_mu * E_mu (total error events)
    """
    return _sns_gain(mu, eta, pd) * _sns_error_rate(mu, eta, pd, e_mis)


def _sns_single_photon_yield_bound(
    *,
    mu_z: float, mu_1: float, mu_2: float,
    S_z: float, S_1: float, S_2: float, S_0: float,
) -> float:
    """Lower bound on single-photon yield s1.

    Using the decoy-state method adapted for SNS protocol:

    s1_L >= (1/(mu_1 - mu_2)) * (S_1*exp(mu_1) - S_2*exp(mu_2)
            - (mu_1^2 - mu_2^2)/(mu_z^2) * (S_z*exp(mu_z) - S_0))

    Simplified form for the case mu_1 > mu_2:

    Ref: Wang et al., PRA 98, 062323 (2018), Eq. (16)
    """
    if mu_1 <= mu_2:
        return 0.0

    denom = mu_1 - mu_2
    term_decoy = S_1 * math.exp(mu_1) - S_2 * math.exp(mu_2)
    mu_sq_ratio = (mu_1 ** 2 - mu_2 ** 2) / max(1e-30, mu_z ** 2)
    term_signal = mu_sq_ratio * (S_z * math.exp(mu_z) - S_0)

    s1 = (term_decoy - term_signal) / denom
    return max(0.0, s1)


def _sns_phase_error_bound(
    *,
    mu_1: float, S_1: float, T_1: float, s1: float,
) -> float:
    """Upper bound on phase error rate for single-photon events.

    e1_phase_U = T_1 / (mu_1 * exp(-mu_1) * s1)

    This is a conservative bound from the X-basis error statistics.

    Ref: Wang et al., PRA 98, 062323 (2018), Eq. (18)
    """
    denom = mu_1 * math.exp(-mu_1) * s1
    if denom <= 0:
        return 0.5
    return clamp(T_1 / denom, 0.0, 0.5)


# ---------------------------------------------------------------------------
# Channel diagnostics helper
# ---------------------------------------------------------------------------

def _relay_segment_channel_diag(
    *,
    channel: dict,
    distance_km: float,
    wavelength_nm: float,
) -> dict:
    """Compute channel diagnostics for a single relay segment."""
    seg_cfg = dict(channel)
    seg_cfg["model"] = "fiber"
    return compute_channel_diagnostics(
        distance_km=distance_km,
        wavelength_nm=float(wavelength_nm),
        channel_cfg=seg_cfg,
    )


# ---------------------------------------------------------------------------
# Empty result
# ---------------------------------------------------------------------------

def _empty_result(distance_km: float, loss_db: float) -> QKDResult:
    return QKDResult(
        distance_km=float(distance_km),
        entanglement_rate_hz=0.0,
        key_rate_bps=0.0,
        qber_total=0.5,
        fidelity=0.5,
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
        loss_db=loss_db,
        protocol_name="sns_tf_qkd",
    )
