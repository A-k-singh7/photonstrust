"""PDK adapter contract types and conformance validators."""

from __future__ import annotations

from typing import Any, Mapping, Protocol, TypedDict


PDK_ADAPTER_CONTRACT_SCHEMA_VERSION = "0"


class PDKCapabilityMatrix(TypedDict):
    supports_layout: bool
    supports_performance_drc: bool
    supports_lvs_lite_signoff: bool
    supports_spice_export: bool


class PDKPayload(TypedDict):
    name: str
    version: str
    design_rules: dict[str, Any]
    notes: list[str]


class PDKRequestRef(TypedDict):
    name: str | None
    manifest_path: str | None


class PDKAdapterContract(TypedDict):
    schema_version: str
    adapter: str
    request: PDKRequestRef
    pdk: PDKPayload
    capabilities: PDKCapabilityMatrix


class PDKPayloadResolver(Protocol):
    """Typed resolver contract for adapter implementations."""

    def resolve(self, pdk_request: Mapping[str, Any] | None) -> PDKAdapterContract:
        ...


def default_pdk_capability_matrix() -> PDKCapabilityMatrix:
    return {
        "supports_layout": True,
        "supports_performance_drc": True,
        "supports_lvs_lite_signoff": True,
        "supports_spice_export": True,
    }


def _normalize_capability_matrix(raw: Any) -> PDKCapabilityMatrix:
    defaults = default_pdk_capability_matrix()
    if not isinstance(raw, Mapping):
        return dict(defaults)

    out = dict(defaults)
    for k in defaults.keys():
        if k in raw:
            out[k] = bool(raw[k])
    return out


def validate_pdk_adapter_contract(payload: Mapping[str, Any]) -> PDKAdapterContract:
    """Validate and normalize a serialized adapter contract payload."""

    if not isinstance(payload, Mapping):
        raise TypeError("adapter contract must be an object")

    schema_version = str(payload.get("schema_version", "")).strip()
    if schema_version != PDK_ADAPTER_CONTRACT_SCHEMA_VERSION:
        raise ValueError(
            f"adapter contract schema_version must be {PDK_ADAPTER_CONTRACT_SCHEMA_VERSION!r}"
        )

    adapter = str(payload.get("adapter", "")).strip()
    if not adapter:
        raise ValueError("adapter contract missing required field: adapter")

    request = payload.get("request")
    if request is None:
        request = {}
    if not isinstance(request, Mapping):
        raise ValueError("adapter contract request must be an object")
    request_name_raw = request.get("name")
    request_manifest_raw = request.get("manifest_path")
    request_name = str(request_name_raw).strip() if request_name_raw is not None else None
    request_manifest_path = (
        str(request_manifest_raw).strip() if request_manifest_raw is not None else None
    )
    if request_name == "":
        request_name = None
    if request_manifest_path == "":
        request_manifest_path = None

    pdk = payload.get("pdk")
    if not isinstance(pdk, Mapping):
        raise ValueError("adapter contract pdk must be an object")

    name = str(pdk.get("name", "")).strip()
    if not name:
        raise ValueError("adapter contract pdk missing required field: name")
    version = str(pdk.get("version", "0")).strip() or "0"

    design_rules = pdk.get("design_rules")
    if design_rules is None:
        design_rules = {}
    if not isinstance(design_rules, dict):
        raise ValueError("adapter contract pdk.design_rules must be an object")

    notes_raw = pdk.get("notes")
    if notes_raw is None:
        notes_raw = []
    if not isinstance(notes_raw, list):
        raise ValueError("adapter contract pdk.notes must be an array")
    notes = [str(v) for v in notes_raw]

    raw_caps = payload.get("capabilities")
    if raw_caps is None:
        raw_caps = {}
    if not isinstance(raw_caps, Mapping):
        raise ValueError("adapter contract capabilities must be an object")

    capabilities = _normalize_capability_matrix(raw_caps)
    for key in default_pdk_capability_matrix().keys():
        if key in raw_caps and not isinstance(raw_caps[key], bool):
            raise ValueError(f"adapter contract capabilities.{key} must be a boolean")

    return {
        "schema_version": PDK_ADAPTER_CONTRACT_SCHEMA_VERSION,
        "adapter": adapter,
        "request": {
            "name": request_name,
            "manifest_path": request_manifest_path,
        },
        "pdk": {
            "name": name,
            "version": version,
            "design_rules": dict(design_rules),
            "notes": notes,
        },
        "capabilities": capabilities,
    }


__all__ = [
    "PDK_ADAPTER_CONTRACT_SCHEMA_VERSION",
    "PDKAdapterContract",
    "PDKCapabilityMatrix",
    "PDKPayloadResolver",
    "default_pdk_capability_matrix",
    "validate_pdk_adapter_contract",
]
