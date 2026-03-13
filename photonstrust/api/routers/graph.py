"""Graph validation and compilation routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from photonstrust.api import compile_cache as compile_cache_store
from photonstrust.api.common import graph_from_payload
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.graph.diagnostics import validate_graph_semantics
from photonstrust.graph.schema import validate_graph
from photonstrust.utils import hash_dict


router = APIRouter()


@router.post("/v0/graph/validate")
def graph_validate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    try:
        validate_graph(graph, require_jsonschema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "generated_at": generated_at_utc(),
        "graph_id": graph.get("graph_id"),
        "profile": str(graph.get("profile", "")).strip().lower(),
        "graph_hash": hash_dict(graph),
        "diagnostics": validate_graph_semantics(graph),
        "provenance": runtime_provenance(),
    }


@router.post("/v0/graph/compile")
def graph_compile(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    include_cache_stats = bool(payload.get("include_cache_stats", False)) if isinstance(payload, dict) else False
    try:
        compiled_payload, compile_cache = compile_cache_store.compile_graph_cached(graph, require_schema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    compile_cache_payload: dict[str, Any] = {"key": compile_cache.get("key")}
    if include_cache_stats:
        compile_cache_payload["hit"] = bool(compile_cache.get("hit", False))

    return {
        "generated_at": compiled_payload.get("generated_at") or generated_at_utc(),
        "graph_id": compiled_payload.get("graph_id"),
        "profile": compiled_payload.get("profile"),
        "graph_hash": compiled_payload.get("graph_hash"),
        "diagnostics": compiled_payload.get("diagnostics"),
        "compiled": compiled_payload.get("compiled"),
        "warnings": compiled_payload.get("warnings"),
        "assumptions_md": compiled_payload.get("assumptions_md"),
        "compile_cache": compile_cache_payload,
        "provenance": runtime_provenance(),
    }
