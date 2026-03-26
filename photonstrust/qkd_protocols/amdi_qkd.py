"""Asynchronous-pairing MDI-QKD effective model.

This surface extends the canonical MDI-QKD point model with a post-processing
pairing gain term that captures asynchronous/mode-pairing style matching over
multiple detection bins.

The baseline physical channel/yield/error terms are still computed by the
MDI-QKD model (`compute_point_mdi_qkd`). AMDI then applies:

- a bounded pairing gain on useful paired events
- an optional pairing-induced error penalty

This keeps AMDI-family benchmarks isolated from canonical MDI assumptions.
"""

from __future__ import annotations

import math

from photonstrust.qkd_protocols.mdi_qkd import compute_point_mdi_qkd
from photonstrust.qkd_types import QKDResult
from photonstrust.utils import binary_entropy, clamp


def compute_point_amdi_qkd(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    """Compute one AMDI-QKD point.

    Protocol parameters (all optional):

    - pairing_window_bins: matching window length (default: 2048)
    - pairing_efficiency: effective usable-pair fraction in [0, 1] (default: 0.6)
    - pairing_gain_max: hard cap on gain (default: 1e6)
    - pairing_error_prob: additional random-pairing error probability in [0, 0.5]
      (default: 0.0)
    """

    base = compute_point_mdi_qkd(scenario, distance_km, runtime_overrides)

    protocol = ((scenario or {}).get("protocol") or {})
    source = ((scenario or {}).get("source") or {})

    rep_rate_hz = float(source.get("rep_rate_mhz", 0.0) or 0.0) * 1e6
    q_sync = float(base.entanglement_rate_hz) / max(1e-30, rep_rate_hz)

    window_bins = int(protocol.get("pairing_window_bins", 2048) or 2048)
    window_bins = max(1, window_bins)
    pairing_eff = clamp(float(protocol.get("pairing_efficiency", 0.6) or 0.6), 0.0, 1.0)
    gain_cap = max(1.0, float(protocol.get("pairing_gain_max", 1e6) or 1e6))

    # For tiny synchronous click fractions, asynchronous pairing can recover
    # approximately O(window_bins) additional usable matches; collision pressure
    # at larger q_sync reduces the effective gain.
    gain_raw = 1.0 + pairing_eff * float(max(0, window_bins - 1))
    collision_penalty = 1.0 / (1.0 + q_sync * float(window_bins))
    pairing_gain = 1.0 + (gain_raw - 1.0) * collision_penalty
    pairing_gain = clamp(float(pairing_gain), 1.0, gain_cap)

    pairing_error = clamp(float(protocol.get("pairing_error_prob", 0.0) or 0.0), 0.0, 0.5)
    qber_base = clamp(float(base.qber_total), 0.0, 0.5)
    qber_total = qber_base + (1.0 - qber_base) * pairing_error * (1.0 - (1.0 / pairing_gain))
    qber_total = clamp(float(qber_total), 0.0, 0.5)

    # Re-scale key fraction for any pairing-induced error inflation.
    privacy_base = max(1e-12, 1.0 - binary_entropy(qber_base))
    privacy_eff = max(0.0, 1.0 - binary_entropy(qber_total))
    privacy_scale = privacy_eff / privacy_base

    entanglement_rate_hz = float(base.entanglement_rate_hz) * pairing_gain
    key_rate_bps = max(0.0, float(base.key_rate_bps) * pairing_gain * privacy_scale)

    fidelity = clamp(1.0 - qber_total, 0.0, 1.0)

    q_dark = clamp(float(base.q_dark) + max(0.0, qber_total - qber_base), 0.0, 0.5)
    q_scale = q_dark / max(1e-30, float(base.q_dark)) if base.q_dark > 0.0 else 1.0
    q_dark_detector = clamp(float(base.q_dark_detector) * q_scale, 0.0, 0.5)
    q_background = clamp(float(base.q_background) * q_scale, 0.0, 0.5)
    q_raman = clamp(float(base.q_raman) * q_scale, 0.0, 0.5)

    protocol_diagnostics = {
        "baseline_protocol": "mdi_qkd",
        "pairing_window_bins": int(window_bins),
        "pairing_efficiency": float(pairing_eff),
        "pairing_gain": float(pairing_gain),
        "pairing_collision_penalty": float(collision_penalty),
        "pairing_error_prob": float(pairing_error),
        "q_sync": float(q_sync),
    }

    return QKDResult(
        distance_km=float(base.distance_km),
        entanglement_rate_hz=float(entanglement_rate_hz),
        key_rate_bps=float(key_rate_bps),
        qber_total=float(qber_total),
        fidelity=float(fidelity),
        p_pair=float(base.p_pair),
        p_false=float(base.p_false),
        q_multi=float(base.q_multi),
        q_dark=float(q_dark),
        q_timing=float(base.q_timing),
        q_misalignment=float(base.q_misalignment),
        q_source=float(base.q_source),
        q_dark_detector=float(q_dark_detector),
        q_background=float(q_background),
        q_raman=float(q_raman),
        background_counts_cps=float(base.background_counts_cps),
        raman_counts_cps=float(base.raman_counts_cps),
        finite_key_enabled=bool(base.finite_key_enabled),
        privacy_term_asymptotic=float(base.privacy_term_asymptotic),
        privacy_term_effective=float(base.privacy_term_effective),
        finite_key_penalty=float(base.finite_key_penalty),
        loss_db=float(base.loss_db),
        protocol_name="amdi_qkd",
        single_photon_yield_lb=float(base.single_photon_yield_lb),
        single_photon_error_ub=float(base.single_photon_error_ub),
        finite_key_epsilon=float(base.finite_key_epsilon),
        protocol_diagnostics=protocol_diagnostics,
    )


# ---------------------------------------------------------------------------
# QKDProtocolBase wrapper
# ---------------------------------------------------------------------------

from typing import Any

from pydantic import BaseModel, Field

from photonstrust.qkd_protocols.protocol_base import QKDProtocolBase, QKDProtocolMeta
from photonstrust.qkd_protocols.base import ProtocolApplicability


class AMDIQKDParams(BaseModel):
    """Protocol-specific parameters for Asynchronous MDI-QKD."""

    pairing_gain: float = Field(
        1.0, ge=1.0, description="Effective pairing gain from async matching"
    )
    pairing_penalty_error_rate: float = Field(
        0.0, ge=0.0, le=0.5,
        description="Additional error probability from random pairing",
    )
    pairing_window_bins: int = Field(
        2048, ge=1, description="Async matching window length in bins"
    )
    pairing_efficiency: float = Field(
        0.6, ge=0.0, le=1.0, description="Usable-pair fraction"
    )
    mu_s: float = Field(0.5, gt=0.0, description="Signal intensity (inherited from MDI)")
    mu_1: float = Field(0.1, gt=0.0, description="Weak decoy intensity")
    mu_2: float = Field(0.0, ge=0.0, description="Vacuum/second decoy intensity")
    misalignment_prob: float = Field(
        0.015, ge=0.0, le=0.5, description="Optical misalignment probability"
    )
    ec_efficiency: float = Field(
        1.16, ge=1.0, description="Error-correction efficiency factor (f >= 1)"
    )


class AMDIQKDProtocol(QKDProtocolBase):
    """QKDProtocolBase wrapper for the AMDI-QKD (Asynchronous MDI) protocol."""

    @classmethod
    def meta(cls) -> QKDProtocolMeta:
        return QKDProtocolMeta(
            protocol_id="amdi_qkd",
            title="AMDI-QKD (Asynchronous MDI)",
            aliases=("amdi", "async_mdi", "mp_qkd", "mode_pairing"),
            description=(
                "Asynchronous/mode-pairing MDI-QKD that applies a post-processing "
                "pairing gain on top of the canonical MDI-QKD physical model."
            ),
            channel_models=("fiber",),
            gate_policy={"plob_repeaterless_bound": "skip"},
        )

    @classmethod
    def params_schema(cls) -> type[BaseModel]:
        return AMDIQKDParams

    @classmethod
    def compute_point(
        cls,
        scenario: dict[str, Any],
        distance_km: float,
        runtime_overrides: dict[str, Any] | None = None,
    ) -> QKDResult:
        return compute_point_amdi_qkd(scenario, distance_km, runtime_overrides)

    @classmethod
    def applicability(cls, scenario: dict[str, Any]) -> ProtocolApplicability:
        channel = (scenario or {}).get("channel", {}) or {}
        model = str(channel.get("model", "fiber")).lower()
        if model != "fiber":
            return ProtocolApplicability(
                status="fail",
                reasons=(
                    f"AMDI-QKD currently supports fiber channel only, got model={model!r}",
                ),
            )
        return ProtocolApplicability(status="pass", reasons=())
