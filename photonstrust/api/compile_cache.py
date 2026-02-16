"""Compile cache helpers for API graph compilation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.api import runs as run_store
from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.diagnostics import validate_graph_semantics
from photonstrust.utils import hash_dict


def compile_cache_root() -> Path:
    root = run_store.runs_root() / "_compile_cache"
    root.mkdir(parents=True, exist_ok=True)
    return root


def compile_cache_key(graph: dict[str, Any], *, require_schema: bool) -> str:
    return hash_dict(
        {
            "kind": "graph_compile_cache",
            "schema_version": "0.1",
            "require_schema": bool(require_schema),
            "graph": graph,
        }
    )


def compile_graph_cached(graph: dict[str, Any], *, require_schema: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    key = compile_cache_key(graph, require_schema=require_schema)
    path = compile_cache_root() / f"{key}.json"
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            payload = None
        if isinstance(payload, dict) and _is_valid_compiled_payload(payload):
            return payload, {"key": key, "hit": True, "path": str(path)}

    compiled = compile_graph(graph, require_schema=require_schema)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": graph.get("graph_id"),
        "profile": compiled.profile,
        "graph_hash": hash_dict(graph),
        "diagnostics": validate_graph_semantics(graph),
        "compiled": compiled.compiled,
        "warnings": compiled.warnings,
        "assumptions_md": compiled.assumptions_md,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload, {"key": key, "hit": False, "path": str(path)}


def _is_valid_compiled_payload(payload: dict[str, Any]) -> bool:
    required = {"profile", "compiled", "warnings", "assumptions_md", "diagnostics"}
    for key in required:
        if key not in payload:
            return False
    return isinstance(payload.get("compiled"), dict)
