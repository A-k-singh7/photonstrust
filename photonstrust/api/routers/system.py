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
