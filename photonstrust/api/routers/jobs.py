"""Background job routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from photonstrust.api import jobs as job_store
from photonstrust.api.auth import enforce_project_scope_or_403, require_roles
from photonstrust.api.common import allowed_projects_from_ctx
from photonstrust.api.runtime import generated_at_utc, runtime_provenance


router = APIRouter()


def _job_project_id(manifest: dict[str, Any]) -> str:
    input_obj = manifest.get("input") if isinstance(manifest.get("input"), dict) else {}
    return str((input_obj or {}).get("project_id") or "default").strip().lower() or "default"


@router.get("/v0/jobs")
def jobs_list(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    status: str | None = Query(None, description="Optional status filter: queued|running|succeeded|failed"),
) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    try:
        jobs = job_store.list_jobs(limit=int(limit), status=status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    allowed = allowed_projects_from_ctx(ctx)
    if allowed is not None:
        jobs = [
            row
            for row in jobs
            if isinstance(row, dict) and _job_project_id(row) in allowed
        ]

    normalized_status = str(status).strip().lower() if isinstance(status, str) and str(status).strip() else None
    return {
        "generated_at": generated_at_utc(),
        "jobs_root": str(job_store.jobs_root()),
        "status": normalized_status,
        "jobs": jobs,
        "provenance": runtime_provenance(),
    }


@router.get("/v0/jobs/{job_id}")
def jobs_get(job_id: str, request: Request) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    try:
        manifest = job_store.read_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not isinstance(manifest, dict):
        raise HTTPException(status_code=404, detail="job not found")
    enforce_project_scope_or_403(ctx, _job_project_id(manifest))
    return manifest


@router.get("/v0/jobs/{job_id}/status")
def jobs_status(job_id: str, request: Request) -> dict[str, Any]:
    manifest = jobs_get(job_id, request)
    return {
        "job_id": manifest.get("job_id"),
        "job_type": manifest.get("job_type"),
        "status": manifest.get("status"),
        "updated_at": manifest.get("updated_at"),
        "result": manifest.get("result"),
        "error": manifest.get("error"),
    }
