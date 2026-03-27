"""Shared helpers for API routes and services."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from photonstrust.api import projects as project_store
from photonstrust.api import runs as run_store


_EXECUTION_MODES = {"preview", "certification"}


def normalize_utc_timestamp(value: Any, *, field_name: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be ISO-8601 timestamp") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def run_project_id_from_manifest(manifest: dict[str, Any] | None) -> str:
    data = manifest if isinstance(manifest, dict) else {}
    input_obj = data.get("input") if isinstance(data.get("input"), dict) else {}
    return str((input_obj or {}).get("project_id") or "default").strip().lower() or "default"


def parse_execution_mode(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return "preview"
    mode = str(payload.get("execution_mode", "preview") or "preview").strip().lower() or "preview"
    if mode not in _EXECUTION_MODES:
        raise HTTPException(
            status_code=400,
            detail="execution_mode must be 'preview' or 'certification' when provided",
        )
    return mode


def graph_from_payload(payload: Any) -> dict[str, Any]:
    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")
    return graph


def reject_output_root_override(payload: dict[str, Any]) -> None:
    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )


def project_id_or_400(payload: dict[str, Any]) -> str:
    try:
        return project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid project_id format") from exc


def project_id_value_or_400(value: Any) -> str:
    try:
        return project_store.validate_project_id(str(value or "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid project_id format") from exc


def allowed_projects_from_ctx(ctx: dict[str, Any]) -> set[str] | None:
    projects = ctx.get("projects")
    if not isinstance(projects, set):
        return None
    if "*" in projects:
        return None
    return projects


def resolve_reference_run(payload: dict[str, Any]) -> tuple[str, str | None, Path]:
    layout_run_id = str(payload.get("layout_run_id", "")).strip()
    source_run_id = str(payload.get("source_run_id", "") or payload.get("run_id", "")).strip()
    if source_run_id and layout_run_id and source_run_id != layout_run_id:
        raise HTTPException(status_code=400, detail="source_run_id and layout_run_id must match when both are provided")

    ref_run_id = source_run_id or layout_run_id
    if not ref_run_id:
        raise HTTPException(status_code=400, detail="Provide source_run_id (preferred) or layout_run_id")
    try:
        ref_dir = run_store.run_dir_for_id(ref_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid source_run_id/layout_run_id format") from exc
    if not ref_dir.exists():
        raise HTTPException(status_code=404, detail="source_run_id not found" if source_run_id else "layout_run_id not found")
    return ref_run_id, layout_run_id or None, ref_dir


def dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def safe_read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def run_artifact_relpath(run_dir: Path, artifact_path: str | Path) -> str | None:
    try:
        base = os.path.realpath(os.fspath(run_dir))
        candidate = os.path.realpath(os.fspath(Path(str(artifact_path))))
        if os.path.commonpath([candidate, base]) != base:
            return None
        return str(Path(candidate).relative_to(Path(base))).replace("\\", "/")
    except Exception:
        return None
