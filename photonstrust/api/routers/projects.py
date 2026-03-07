"""Project and approval routes."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, Request

from photonstrust.api import projects as project_store
from photonstrust.api import runs as run_store
from photonstrust.api.auth import enforce_project_scope_or_403, require_roles
from photonstrust.api.common import allowed_projects_from_ctx
from photonstrust.api.common import project_id_value_or_400
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.common import run_project_id_from_manifest
from photonstrust.api.routers.runs import runs_get
from photonstrust.utils import hash_dict


router = APIRouter()


@router.get("/v0/projects")
def projects_list(request: Request, limit: int = Query(200, ge=1, le=500)) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    projects = project_store.list_projects(limit=int(limit))
    allowed = allowed_projects_from_ctx(ctx)
    if allowed is not None:
        projects = [
            row
            for row in projects
            if isinstance(row, dict) and str(row.get("project_id") or "default").strip().lower() in allowed
        ]
    return {
        "generated_at": generated_at_utc(),
        "runs_root": str(run_store.runs_root()),
        "projects": projects,
        "provenance": runtime_provenance(),
    }


@router.get("/v0/projects/{project_id}/approvals")
def projects_approvals_list(request: Request, project_id: str, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    ctx = require_roles(request, "viewer", "runner", "approver")
    pid = project_id_value_or_400(project_id)
    enforce_project_scope_or_403(ctx, pid)

    approvals = project_store.list_approval_events(pid, limit=int(limit))
    return {
        "generated_at": generated_at_utc(),
        "project_id": pid,
        "approvals": approvals,
        "provenance": runtime_provenance(),
    }


@router.post("/v0/projects/{project_id}/approvals")
def projects_approvals_create(request: Request, project_id: str, payload: dict = Body(...)) -> dict[str, Any]:
    ctx = require_roles(request, "approver")
    pid = project_id_value_or_400(project_id)
    enforce_project_scope_or_403(ctx, pid)

    run_id = str((payload or {}).get("run_id", "")).strip()
    if not run_id:
        raise HTTPException(status_code=400, detail="run_id is required")
    try:
        run_dir = run_store.run_dir_for_id(run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    manifest = run_store.read_run_manifest(run_dir) or runs_get(run_id, request)
    run_pid = run_project_id_from_manifest(manifest)
    if run_pid != pid:
        raise HTTPException(status_code=400, detail="run project_id does not match requested project_id")

    if str(ctx.get("mode", "off")) == "header":
        actor = str(ctx.get("actor", "")).strip() or "unknown"
    else:
        actor = str((payload or {}).get("actor", "")).strip() or "unknown"
    note = str((payload or {}).get("note", "")).strip()
    if len(actor) > 120:
        actor = actor[:120]
    if len(note) > 4000:
        note = note[:4000]

    outputs_summary = (manifest or {}).get("outputs_summary", {}) or {}
    if not isinstance(outputs_summary, dict):
        outputs_summary = {}

    event = {
        "schema_version": "0.1",
        "event_id": uuid.uuid4().hex[:12],
        "event_type": "run_approved",
        "created_at": generated_at_utc(),
        "project_id": pid,
        "run_id": run_id,
        "actor": actor,
        "note": note,
        "run_manifest_hash": hash_dict(manifest or {}),
        "outputs_summary_hash": hash_dict(outputs_summary),
    }
    try:
        project_store.append_approval_event(pid, event)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "generated_at": generated_at_utc(),
        "event": event,
        "provenance": runtime_provenance(),
    }
