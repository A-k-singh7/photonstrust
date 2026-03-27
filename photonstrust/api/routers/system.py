"""System and registry routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from photonstrust.api.runtime import api_version, runtime_provenance
from photonstrust.registry.kinds import build_kinds_registry
from photonstrust.utils import hash_dict


router = APIRouter()


@router.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "version": api_version()}


@router.get("/v0/registry/kinds")
def registry_kinds() -> dict[str, Any]:
    registry = build_kinds_registry()
    return {
        "schema_version": str(registry.get("schema_version", "0.0")),
        "registry_hash": hash_dict(registry),
        "registry": registry,
        "provenance": runtime_provenance(),
    }


@router.get("/v0/registry/components")
def registry_components() -> dict[str, Any]:
    """Serve PIC component definitions with JSON Schema for parameters."""
    from photonstrust.components.pic.library import all_component_classes

    components: dict[str, Any] = {}
    for kind, cls in sorted(all_component_classes().items()):
        meta = cls.meta()
        components[kind] = {
            "kind": meta.kind,
            "title": meta.title,
            "category": meta.category,
            "description": meta.description,
            "ports": {"in": list(meta.in_ports), "out": list(meta.out_ports)},
            "port_domains": meta.port_domains,
            "params_schema": cls.params_schema().model_json_schema(),
        }
    return {"components": components, "provenance": runtime_provenance()}


@router.get("/v0/registry/protocols")
def registry_protocols() -> dict[str, Any]:
    """Serve QKD protocol definitions with JSON Schema for parameters."""
    from photonstrust.qkd_protocols.registry import all_protocol_classes

    protocols: dict[str, Any] = {}
    for pid, cls in sorted(all_protocol_classes().items()):
        meta = cls.meta()
        protocols[pid] = {
            "protocol_id": meta.protocol_id,
            "title": meta.title,
            "aliases": list(meta.aliases),
            "description": meta.description,
            "channel_models": list(meta.channel_models),
            "gate_policy": meta.gate_policy,
            "params_schema": cls.params_schema().model_json_schema(),
        }
    return {"protocols": protocols, "provenance": runtime_provenance()}
