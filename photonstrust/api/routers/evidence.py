"""Evidence bundle routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse

from photonstrust.api import runs as run_store
from photonstrust.api.auth import enforce_project_scope_or_403, require_roles
from photonstrust.api.common import run_project_id_from_manifest
from photonstrust.api.routers.runs import runs_get
from photonstrust.api.services.evidence_bundles import export_bundle_for_run
from photonstrust.api.services.evidence_bundles import published_bundle_path
from photonstrust.api.services.evidence_bundles import publish_bundle_for_run
from photonstrust.api.services.evidence_bundles import resolve_include_children
from photonstrust.api.services.evidence_bundles import validate_bundle_digest
from photonstrust.api.services.evidence_bundles import verify_published_bundle


router = APIRouter()


@router.get("/v0/runs/{run_id}/bundle")
def runs_bundle(
    run_id: str,
    request: Request,
    include_children: bool | None = Query(None, description="Include workflow child runs (default: true for workflow runs)."),
    rebuild: bool = Query(False, description="Rebuild bundle even if cached zip exists."),
) -> FileResponse:
    ctx = require_roles(request, "viewer", "runner", "approver")

    try:
        root_dir = run_store.run_dir_for_id(run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not root_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    root_manifest = run_store.read_run_manifest(root_dir) or runs_get(run_id, request)
    if not isinstance(root_manifest, dict):
        root_manifest = runs_get(run_id, request)
    enforce_project_scope_or_403(ctx, run_project_id_from_manifest(root_manifest))

    include_children_resolved = resolve_include_children(root_manifest, include_children)
    bundle_path = export_bundle_for_run(
        run_id=run_id,
        root_dir=root_dir,
        root_manifest=root_manifest,
        include_children=include_children_resolved,
        rebuild=rebuild,
        fetch_manifest=lambda rid: runs_get(rid, request),
    )

    headers = {
        "cache-control": "no-store",
        "content-disposition": f'attachment; filename="{Path(bundle_path).name}"',
    }
    return FileResponse(path=str(bundle_path), media_type="application/zip", headers=headers)


@router.post("/v0/runs/{run_id}/bundle/publish")
def runs_bundle_publish(
    run_id: str,
    request: Request,
    include_children: bool | None = Query(None, description="Include workflow child runs (default: true for workflow runs)."),
    rebuild: bool = Query(False, description="Rebuild bundle before publish."),
) -> dict[str, object]:
    ctx = require_roles(request, "viewer", "runner", "approver")

    try:
        root_dir = run_store.run_dir_for_id(run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not root_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    root_manifest = run_store.read_run_manifest(root_dir) or runs_get(run_id, request)
    if not isinstance(root_manifest, dict):
        root_manifest = runs_get(run_id, request)
    enforce_project_scope_or_403(ctx, run_project_id_from_manifest(root_manifest))

    include_children_resolved = resolve_include_children(root_manifest, include_children)
    return publish_bundle_for_run(
        run_id=run_id,
        root_dir=root_dir,
        root_manifest=root_manifest,
        include_children=include_children_resolved,
        rebuild=rebuild,
        fetch_manifest=lambda rid: runs_get(rid, request),
    )


@router.get("/v0/evidence/bundle/by-digest/{digest}")
def evidence_bundle_by_digest(digest: str, request: Request) -> FileResponse:
    require_roles(request, "viewer", "runner", "approver")
    value = validate_bundle_digest(digest)
    zip_path = published_bundle_path(value)
    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=404, detail="published bundle not found")

    headers = {
        "cache-control": "no-store",
        "content-disposition": f'attachment; filename="{zip_path.name}"',
    }
    return FileResponse(path=str(zip_path), media_type="application/zip", headers=headers)


@router.get("/v0/evidence/bundle/by-digest/{digest}/verify")
def evidence_bundle_verify_by_digest(digest: str, request: Request) -> dict[str, object]:
    require_roles(request, "viewer", "runner", "approver")
    return verify_published_bundle(digest)
