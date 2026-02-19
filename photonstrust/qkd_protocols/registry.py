"""Registry and dispatch helpers for QKD protocol modules."""

from __future__ import annotations

from typing import Any

from photonstrust.qkd_protocols.base import ProtocolApplicability, QKDProtocolModule
from photonstrust.qkd_protocols.amdi_qkd import compute_point_amdi_qkd
from photonstrust.qkd_protocols.bb84_decoy import compute_point_bb84_decoy
from photonstrust.qkd_protocols.bbm92 import compute_point_bbm92
from photonstrust.qkd_protocols.common import normalize_protocol_name
from photonstrust.qkd_protocols.mdi_qkd import compute_point_mdi_qkd
from photonstrust.qkd_protocols.pm_qkd import compute_point_pm_qkd


def _applicability_direct(_: dict) -> ProtocolApplicability:
    return ProtocolApplicability(status="pass", reasons=())


def _applicability_mdi(scenario: dict) -> ProtocolApplicability:
    channel = (scenario or {}).get("channel", {}) or {}
    model = str(channel.get("model", "fiber") or "fiber").strip().lower()
    if model != "fiber":
        return ProtocolApplicability(
            status="fail",
            reasons=("MDI_QKD currently supports only fiber channel model",),
        )
    return ProtocolApplicability(status="pass", reasons=())


def _applicability_pm_tf(scenario: dict) -> ProtocolApplicability:
    channel = (scenario or {}).get("channel", {}) or {}
    model = str(channel.get("model", "fiber") or "fiber").strip().lower()
    if model != "fiber":
        return ProtocolApplicability(
            status="fail",
            reasons=("PM_QKD/TF_QKD currently support only fiber channel model",),
        )
    return ProtocolApplicability(status="pass", reasons=())


def _compute_point_tf_qkd(scenario: dict, distance_km: float, runtime_overrides: dict | None) -> Any:
    return compute_point_pm_qkd(scenario, distance_km, runtime_overrides, tf_variant=True)


_PROTOCOLS: dict[str, QKDProtocolModule] = {
    "bbm92": QKDProtocolModule(
        protocol_id="bbm92",
        aliases=("e91",),
        evaluator=compute_point_bbm92,
        applicability_fn=_applicability_direct,
        gate_policy={
            "plob_repeaterless_bound": "apply",
            "rationale": "Direct-link protocol; repeaterless bound sanity gate is applicable.",
        },
    ),
    "bb84_decoy": QKDProtocolModule(
        protocol_id="bb84_decoy",
        aliases=("bb84", "decoy_bb84", "bb84_wcp", "decoy"),
        evaluator=compute_point_bb84_decoy,
        applicability_fn=_applicability_direct,
        gate_policy={
            "plob_repeaterless_bound": "apply",
            "rationale": "Prepare-and-measure direct-link protocol; repeaterless bound sanity gate is applicable.",
        },
    ),
    "mdi_qkd": QKDProtocolModule(
        protocol_id="mdi_qkd",
        aliases=("mdi",),
        evaluator=compute_point_mdi_qkd,
        applicability_fn=_applicability_mdi,
        gate_policy={
            "plob_repeaterless_bound": "skip",
            "rationale": "Relay-based protocol; direct-link repeaterless bound is not applied as a global gate.",
        },
    ),
    "amdi_qkd": QKDProtocolModule(
        protocol_id="amdi_qkd",
        aliases=("amdi", "async_mdi", "mp_qkd", "mode_pairing"),
        evaluator=compute_point_amdi_qkd,
        applicability_fn=_applicability_mdi,
        gate_policy={
            "plob_repeaterless_bound": "skip",
            "rationale": "Asynchronous/mode-pairing relay protocol; direct-link repeaterless bound is not applied as a global gate.",
        },
    ),
    "pm_qkd": QKDProtocolModule(
        protocol_id="pm_qkd",
        aliases=("pm",),
        evaluator=compute_point_pm_qkd,
        applicability_fn=_applicability_pm_tf,
        gate_policy={
            "plob_repeaterless_bound": "skip",
            "rationale": "Relay/interference protocol family; direct-link repeaterless bound is not applied as a global gate.",
        },
    ),
    "tf_qkd": QKDProtocolModule(
        protocol_id="tf_qkd",
        aliases=("tf", "twin_field", "twinfield"),
        evaluator=_compute_point_tf_qkd,
        applicability_fn=_applicability_pm_tf,
        gate_policy={
            "plob_repeaterless_bound": "skip",
            "rationale": "TF-family protocol; naive direct-link repeaterless bound gate would produce false assertions.",
        },
    ),
}


def available_protocols() -> tuple[str, ...]:
    return tuple(sorted(_PROTOCOLS.keys()))


def resolve_protocol_module(name: str | None) -> QKDProtocolModule:
    normalized = normalize_protocol_name(name)
    if normalized in {"", "bbm92", "e91"}:
        return _PROTOCOLS["bbm92"]
    protocol = _PROTOCOLS.get(normalized)
    if protocol is None:
        raise ValueError(f"Unsupported QKD protocol name: {name!r}")
    return protocol


def protocol_applicability(name: str | None, scenario: dict) -> ProtocolApplicability:
    protocol = resolve_protocol_module(name)
    return protocol.applicability(scenario)


def protocol_gate_policy(name: str | None) -> dict[str, Any]:
    protocol = resolve_protocol_module(name)
    gate_policy = protocol.gate_policy if isinstance(protocol.gate_policy, dict) else {}
    return {
        "protocol_name": protocol.protocol_id,
        **dict(gate_policy),
    }
