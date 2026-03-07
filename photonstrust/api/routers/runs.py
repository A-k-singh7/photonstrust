"""Run registry and artifact routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import FileResponse

from photonstrust.api import runs as run_store
from photonstrust.api.auth import enforce_project_scope_or_403, require_roles
from photonstrust.api.common import allowed_projects_from_ctx
from photonstrust.api.common import project_id_value_or_400
from photonstrust.api.common import run_project_id_from_manifest
from photonstrust.api.http_layer import request_id
from photonstrust.api.models.v1 import V1RunGetResponse, V1RunManifest, V1RunsListResponse
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.services.run_diffs import build_runs_diff_payload


router = APIRouter()


@router.get("/v0/runs")
def runs_list(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    project_id: str | None = Query(None, description="Optional project_id filter"),
) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    pid = None
    if project_id is not None:
        raw = str(project_id or "").strip()
        if raw:
            pid = project_id_value_or_400(raw)
            enforce_project_scope_or_403(ctx, pid)

    runs = run_store.list_runs(limit=int(limit), project_id=pid)
    allowed = allowed_projects_from_ctx(ctx)
    if allowed is not None:
        runs = [
            row
            for row in runs
            if isinstance(row, dict) and str(row.get("project_id") or "default").strip().lower() in allowed
        ]

    return {
        "generated_at": generated_at_utc(),
        "runs_root": str(run_store.runs_root()),
        "project_id": pid,
        "runs": runs,
        "provenance": runtime_provenance(),
    }


@router.get("/v0/runs/{run_id}")
def runs_get(run_id: str, request: Request) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    try:
        run_dir = run_store.run_dir_for_id(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    manifest = run_store.read_run_manifest(run_dir)
    if manifest:
        enforce_project_scope_or_403(ctx, run_project_id_from_manifest(manifest))
        return manifest

    enforce_project_scope_or_403(ctx, "default")
    generated_at = datetime.fromtimestamp(float(run_dir.stat().st_mtime), tz=timezone.utc).isoformat()
    return {
        "schema_version": "0.0",
        "run_id": str(run_id),
        "run_type": "unknown",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {},
        "artifacts": {},
        "provenance": {},
    }


@router.get("/v1/runs", response_model=V1RunsListResponse)
def v1_runs_list(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    project_id: str | None = Query(None, description="Optional project_id filter"),
) -> V1RunsListResponse:
    payload = runs_list(request=request, limit=limit, project_id=project_id)
    return V1RunsListResponse.model_validate({**payload, "request_id": request_id(request)})


@router.get("/v1/runs/{run_id}", response_model=V1RunGetResponse)
def v1_runs_get(run_id: str, request: Request) -> V1RunGetResponse:
    manifest = runs_get(run_id=run_id, request=request)
    return V1RunGetResponse.model_validate(
        {
            "request_id": request_id(request),
            "run": V1RunManifest.model_validate(manifest).model_dump(),
        }
    )


@router.get("/v0/runs/{run_id}/artifact")
def runs_artifact(
    run_id: str,
    request: Request,
    path: str = Query(..., description="Relative path within the run directory"),
) -> FileResponse:
    require_roles(request, "viewer", "runner", "approver")
    try:
        run_dir = run_store.run_dir_for_id(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    runs_get(run_id, request)

    try:
        artifact = run_store.resolve_artifact_path(run_dir, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    suffix = str(artifact.suffix).lower()
    media_type = "application/octet-stream"
    if suffix == ".html":
        media_type = "text/html; charset=utf-8"
    elif suffix == ".json":
        media_type = "application/json"
    elif suffix == ".png":
        media_type = "image/png"
    elif suffix == ".pdf":
        media_type = "application/pdf"
    elif suffix in (".sp", ".cir", ".log", ".txt", ".md"):
        media_type = "text/plain; charset=utf-8"

    headers = {
        "cache-control": "no-store",
        "content-disposition": f'inline; filename="{artifact.name}"',
    }
    return FileResponse(path=str(artifact), media_type=media_type, headers=headers)


@router.post("/v0/runs/diff")
def runs_diff(request: Request, payload: dict = Body(...)) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    lhs_run_id = str((payload or {}).get("lhs_run_id", "")).strip()
    rhs_run_id = str((payload or {}).get("rhs_run_id", "")).strip()
    scope = str((payload or {}).get("scope", "input")).strip().lower() or "input"
    limit = int((payload or {}).get("limit", 200) or 200)

    if not lhs_run_id or not rhs_run_id:
        raise HTTPException(status_code=400, detail="lhs_run_id and rhs_run_id are required")
    if scope not in ("input", "outputs_summary", "all"):
        raise HTTPException(status_code=400, detail="scope must be one of: input, outputs_summary, all")

    try:
        lhs_dir = run_store.run_dir_for_id(lhs_run_id)
        rhs_dir = run_store.run_dir_for_id(rhs_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not lhs_dir.exists():
        raise HTTPException(status_code=404, detail="lhs run not found")
    if not rhs_dir.exists():
        raise HTTPException(status_code=404, detail="rhs run not found")

    lhs_manifest = run_store.read_run_manifest(lhs_dir) or runs_get(lhs_run_id, request)
    rhs_manifest = run_store.read_run_manifest(rhs_dir) or runs_get(rhs_run_id, request)
    if isinstance(lhs_manifest, dict):
        enforce_project_scope_or_403(ctx, run_project_id_from_manifest(lhs_manifest))
    if isinstance(rhs_manifest, dict):
        enforce_project_scope_or_403(ctx, run_project_id_from_manifest(rhs_manifest))

    payload_out = build_runs_diff_payload(
        lhs_manifest=lhs_manifest if isinstance(lhs_manifest, dict) else {},
        rhs_manifest=rhs_manifest if isinstance(rhs_manifest, dict) else {},
        scope=scope,
        limit=limit,
    )
    return {
        "generated_at": generated_at_utc(),
        "scope": scope,
        "lhs": payload_out["lhs"],
        "rhs": payload_out["rhs"],
        "diff": payload_out["diff"],
        "provenance": runtime_provenance(),
    }
