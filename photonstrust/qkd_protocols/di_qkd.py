"""Device-independent QKD from CHSH violation.

Implements a DI-QKD key rate model based on the CHSH inequality
violation. Security requires no assumptions about the internal
workings of Alice's and Bob's devices.

Key references:
    - Pironio et al., NJP 11, 045021 (2009) -- DI randomness
    - Arnon-Friedman et al., Nature Comms 9, 459 (2018) -- EAT
    - Acin et al., PRL 98, 230501 (2007) -- DI-QKD key rate
    - Schwonnek et al., Nature Comms 12, 2880 (2021) -- tight bound
    - Liu et al., Nature 607, 634 (2022) -- experimental DI-QKD

Key rate:
    r = 1 - H(A|E) - H(A|B)
    H(A|E) >= 1 - h((1 + sqrt((S/2)^2 - 1)) / 2)
    H(A|B) = h(Q)

Detection loophole: requires eta > 2/(1 + sqrt(2)) ~ 82.8%
CHSH: S = 2*sqrt(2) ~ 2.828 for maximally entangled state
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from photonstrust.qkd_types import QKDResult
from photonstrust.utils import clamp


def _binary_entropy(x: float) -> float:
    x = clamp(x, 1e-15, 1.0 - 1e-15)
    return -x * math.log2(x) - (1.0 - x) * math.log2(1.0 - x)


def chsh_value(
    visibility: float,
    detection_efficiency: float,
) -> float:
    """Compute expected CHSH value for a Werner state with detection loss.

    For a Werner state with visibility V and detection efficiency eta:
        S = 2*sqrt(2) * V * eta^2

    The factor eta^2 accounts for both Alice and Bob needing a detection.

    Args:
        visibility: Bell state visibility (0 to 1)
        detection_efficiency: Per-side detection efficiency

    Returns:
        Expected CHSH S value
    """
    V = clamp(float(visibility), 0.0, 1.0)
    eta = clamp(float(detection_efficiency), 0.0, 1.0)
    return 2.0 * math.sqrt(2.0) * V * eta ** 2


def detection_loophole_threshold() -> float:
    """Minimum detection efficiency to close the detection loophole.

    eta_min = 2 / (1 + sqrt(2)) ~ 82.84%

    Returns:
        Minimum detection efficiency
    """
    return 2.0 / (1.0 + math.sqrt(2.0))


def di_qkd_key_rate(
    S: float,
    qber: float,
    *,
    f_ec: float = 1.16,
) -> float:
    """Compute DI-QKD key rate per detected pair.

    Key rate from CHSH violation:
        r = 1 - h((1 + sqrt((S/2)^2 - 1)) / 2) - f_ec * h(Q)

    For S <= 2 (no CHSH violation), no key can be extracted.

    Args:
        S: CHSH value (max 2*sqrt(2))
        qber: Quantum bit error rate
        f_ec: Error correction efficiency

    Returns:
        Key rate per detected pair (bits/pair)

    Ref: Acin et al., PRL 98, 230501 (2007)
    """
    S = clamp(float(S), 0.0, 2.0 * math.sqrt(2.0))
    Q = clamp(float(qber), 0.0, 0.5)
    f = max(1.0, float(f_ec))

    # No violation -> no key
    if S <= 2.0:
        return 0.0

    # Eve's information bounded by CHSH value
    # H(A|E) >= 1 - h(p_guess)
    # p_guess = (1 + sqrt((S/2)^2 - 1)) / 2
    s_half = S / 2.0
    inner = s_half ** 2 - 1.0
    if inner <= 0:
        return 0.0
    p_guess = (1.0 + math.sqrt(inner)) / 2.0
    p_guess = clamp(p_guess, 0.5, 1.0)

    h_eve = _binary_entropy(p_guess)  # Eve's guessing entropy
    H_AE = 1.0 - h_eve  # min-entropy bound on A|E

    # Error correction cost
    h_Q = _binary_entropy(Q) if Q > 0 else 0.0

    r = H_AE - f * h_Q
    return max(0.0, r)


def di_qkd_finite_key_rate(
    S: float,
    qber: float,
    *,
    n_rounds: int = 10**8,
    epsilon_total: float = 1e-10,
    f_ec: float = 1.16,
) -> float:
    """DI-QKD key rate with finite-size entropy accumulation correction.

    Uses the entropy accumulation theorem (EAT) correction:
        r_finite = r_asymptotic - O(1/sqrt(n))

    The correction term accounts for statistical fluctuations
    in estimating S and Q from finite data.

    Args:
        S: Observed CHSH value
        qber: Observed QBER
        n_rounds: Number of rounds
        epsilon_total: Total security parameter
        f_ec: Error correction efficiency

    Returns:
        Finite-key rate per round

    Ref: Arnon-Friedman et al., Nature Comms 9, 459 (2018)
    """
    r_asymp = di_qkd_key_rate(S, qber, f_ec=f_ec)
    if r_asymp <= 0:
        return 0.0

    n = max(1, int(n_rounds))
    eps = max(1e-30, float(epsilon_total))

    # EAT finite-size penalty ~ sqrt(log(1/eps) / n)
    penalty = math.sqrt(2.0 * math.log(1.0 / eps) / n)
    # Additional second-order term
    penalty += math.log2(1.0 / eps) / n

    return max(0.0, r_asymp - penalty)


def compute_point_di_qkd(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    """Compute DI-QKD key rate at a given distance.

    The scenario dict should include:
        - protocol.visibility: Bell state visibility (default 0.99)
        - detector.pde: detection efficiency (must be > 82.8%)
        - source.rep_rate_mhz: source repetition rate
        - channel.fiber_loss_db_per_km: fiber loss

    Args:
        scenario: Protocol/channel/detector scenario dict
        distance_km: Alice-Bob distance in km
        runtime_overrides: Optional parameter overrides

    Returns:
        QKDResult with DI-QKD key rate
    """
    distance_km = max(0.0, float(distance_km))
    overrides = runtime_overrides or {}
    proto = dict((scenario or {}).get("protocol", {}) or {})
    proto.update(overrides.get("protocol", {}) or {})
    detector = dict((scenario or {}).get("detector", {}) or {})
    detector.update(overrides.get("detector", {}) or {})
    channel = dict((scenario or {}).get("channel", {}) or {})
    channel.update(overrides.get("channel", {}) or {})
    source = dict((scenario or {}).get("source", {}) or {})
    source.update(overrides.get("source", {}) or {})

    # Parameters
    visibility = float(proto.get("visibility", 0.99))
    pde = float(detector.get("pde", 0.90))
    rep_rate_hz = float(source.get("rep_rate_mhz", 1.0)) * 1e6
    loss_db_per_km = float(channel.get("fiber_loss_db_per_km", 0.2))
    connector_loss_db = float(channel.get("connector_loss_db", 0.0))
    dark_counts_cps = float(detector.get("dark_counts_cps", 1.0))
    f_ec = float(proto.get("f_ec", 1.16))

    finite_key_cfg = proto.get("finite_key", {}) or {}
    finite_key_enabled = bool(finite_key_cfg.get("enabled", False))

    # Channel loss
    from photonstrust.channels.fiber import apply_fiber_loss
    eta_fiber = apply_fiber_loss(distance_km, loss_db_per_km)
    eta_connector = 10 ** (-connector_loss_db / 10.0)
    eta_channel = eta_fiber * eta_connector
    loss_db = -10.0 * math.log10(max(1e-30, eta_channel))

    # Total detection efficiency (both sides)
    eta_total = eta_channel * pde

    # CHSH value
    S = chsh_value(visibility, math.sqrt(eta_total))
    # Using sqrt because each side sees sqrt(eta_channel) * pde
    # Actually for DI-QKD with entangled source at midpoint:
    # Each arm has loss sqrt(eta_channel), so eta_per_side = sqrt(eta_channel) * pde
    eta_per_side = math.sqrt(eta_channel) * pde
    S = chsh_value(visibility, eta_per_side)

    # QBER from dark counts
    p_signal = eta_per_side
    p_dark = dark_counts_cps / max(rep_rate_hz, 1.0)
    p_total = p_signal + p_dark
    if p_total > 0:
        qber_dark = 0.5 * p_dark / p_total
    else:
        qber_dark = 0.5
    qber_vis = (1.0 - visibility) / 2.0
    qber = min(0.5, qber_dark + qber_vis)

    # Key rate
    if finite_key_enabled:
        n_rounds = int(finite_key_cfg.get("signals_per_block", 1e8))
        eps = float(finite_key_cfg.get("security_epsilon", 1e-10))
        r = di_qkd_finite_key_rate(S, qber, n_rounds=n_rounds, epsilon_total=eps, f_ec=f_ec)
    else:
        r = di_qkd_key_rate(S, qber, f_ec=f_ec)

    # Detected pair rate
    pair_rate = rep_rate_hz * eta_per_side ** 2
    key_rate_bps = pair_rate * r

    # Detection loophole check
    eta_threshold = detection_loophole_threshold()
    loophole_closed = eta_per_side >= eta_threshold

    fidelity = 0.5 + 0.5 * visibility * eta_per_side ** 2

    return QKDResult(
        distance_km=distance_km,
        entanglement_rate_hz=pair_rate,
        key_rate_bps=max(0.0, key_rate_bps),
        qber_total=qber,
        fidelity=clamp(fidelity, 0.5, 1.0),
        p_pair=eta_per_side ** 2,
        p_false=p_dark,
        q_multi=0.0,
        q_dark=qber_dark,
        q_timing=0.0,
        q_misalignment=0.0,
        q_source=qber_vis,
        q_dark_detector=qber_dark,
        q_background=0.0,
        q_raman=0.0,
        background_counts_cps=0.0,
        raman_counts_cps=0.0,
        finite_key_enabled=finite_key_enabled,
        privacy_term_asymptotic=di_qkd_key_rate(S, qber, f_ec=f_ec),
        privacy_term_effective=r,
        finite_key_penalty=max(0.0, di_qkd_key_rate(S, qber, f_ec=f_ec) - r),
        loss_db=loss_db,
        protocol_name="di_qkd",
        protocol_diagnostics={
            "chsh_S": S,
            "chsh_classical_bound": 2.0,
            "chsh_quantum_max": 2.0 * math.sqrt(2.0),
            "eta_per_side": eta_per_side,
            "eta_threshold_loophole": eta_threshold,
            "detection_loophole_closed": loophole_closed,
            "key_rate_per_pair": r,
            "visibility": visibility,
        },
    )


# ---------------------------------------------------------------------------
# QKDProtocolBase wrapper
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field

from photonstrust.qkd_protocols.protocol_base import QKDProtocolBase, QKDProtocolMeta
from photonstrust.qkd_protocols.base import ProtocolApplicability


class DIQKDParams(BaseModel):
    """Protocol-specific parameters for DI-QKD."""

    S_CHSH: float = Field(
        2.828, gt=2.0, le=2.8284271247461903,
        description="Observed CHSH S value (must violate classical bound S > 2)",
    )
    gamma: float = Field(
        0.01, ge=0.0, le=1.0, description="Noise tolerance parameter"
    )
    n_rounds: int = Field(
        100_000_000, ge=1, description="Number of measurement rounds"
    )
    ec_efficiency: float = Field(
        1.16, ge=1.0, description="Error-correction efficiency factor (f >= 1)"
    )
    visibility: float = Field(
        0.99, gt=0.0, le=1.0, description="Bell state visibility"
    )


class DIQKDProtocol(QKDProtocolBase):
    """QKDProtocolBase wrapper for the DI-QKD protocol."""

    @classmethod
    def meta(cls) -> QKDProtocolMeta:
        return QKDProtocolMeta(
            protocol_id="di_qkd",
            title="DI-QKD (Device-Independent)",
            aliases=("di", "device_independent", "chsh_qkd"),
            description=(
                "Device-independent QKD whose security relies on observed "
                "CHSH Bell inequality violation, requiring no assumptions "
                "about the internal workings of Alice's and Bob's devices."
            ),
            channel_models=("fiber", "free_space"),
            gate_policy={"plob_repeaterless_bound": "apply"},
        )

    @classmethod
    def params_schema(cls) -> type[BaseModel]:
        return DIQKDParams

    @classmethod
    def compute_point(
        cls,
        scenario: dict[str, Any],
        distance_km: float,
        runtime_overrides: dict[str, Any] | None = None,
    ) -> QKDResult:
        return compute_point_di_qkd(scenario, distance_km, runtime_overrides)
