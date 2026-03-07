"""Foundry sealed verification routes."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from photonstrust.api import runs as run_store
from photonstrust.api.common import parse_execution_mode
from photonstrust.api.common import project_id_or_400
from photonstrust.api.common import reject_output_root_override
from photonstrust.api.common import resolve_reference_run
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.services.foundry_runs import append_foundry_metric_event
from photonstrust.api.services.foundry_runs import enforce_foundry_certification_provenance
from photonstrust.api.services.foundry_runs import parse_foundry_drc_backend
from photonstrust.api.services.foundry_runs import parse_foundry_lvs_backend
from photonstrust.api.services.foundry_runs import parse_foundry_pex_backend
from photonstrust.api.services.foundry_runs import parse_optional_sealed_run_id
from photonstrust.api.services.pdk_manifests import resolve_run_pdk_manifest
from photonstrust.api.services.pdk_manifests import write_pdk_manifest_artifact
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.layout.pic.foundry_drc_sealed import run_foundry_drc_sealed
from photonstrust.layout.pic.foundry_lvs_sealed import run_foundry_lvs_sealed
from photonstrust.layout.pic.foundry_pex_sealed import run_foundry_pex_sealed
from photonstrust.workflow.schema import pic_foundry_drc_sealed_summary_schema_path
from photonstrust.workflow.schema import pic_foundry_lvs_sealed_summary_schema_path
from photonstrust.workflow.schema import pic_foundry_pex_sealed_summary_schema_path


router = APIRouter()


def _resolve_pdk_manifest_or_400(
    *,
    payload: dict[str, Any],
    execution_mode: str,
    ref_run_id: str,
    ref_dir: Path,
) -> dict[str, Any]:
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None
    pdk_manifest = resolve_run_pdk_manifest(
        pdk_request=pdk_req,
        execution_mode=execution_mode,
        source_run_dir=ref_dir,
        source_run_id=ref_run_id,
        require_context_in_cert=True,
    )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(
            status_code=400,
            detail=(
                "certification mode requires source pdk_manifest context; provide source_run_id/layout_run_id with "
                "pdk_manifest_json or provide payload.pdk"
            ),
        )
    return pdk_manifest


def _persist_foundry_run(
    *,
    stage: str,
    project_id: str,
    execution_mode: str,
    ref_run_id: str,
    layout_run_id: str | None,
    pdk_manifest: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    pdk_manifest = dict(pdk_manifest)
    summary = dict(summary)
    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    generated_at = generated_at_utc()
    summary_rel = f"foundry_{stage}_sealed_summary.json"
    (Path(run_dir) / summary_rel).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pdk_manifest_rel = write_pdk_manifest_artifact(run_dir, pdk_manifest)

    counts_raw = summary.get("check_counts")
    counts: dict[str, Any] = counts_raw if isinstance(counts_raw, dict) else {}
    pdk_info_raw = pdk_manifest.get("pdk")
    pdk_info: dict[str, Any] = pdk_info_raw if isinstance(pdk_info_raw, dict) else {}
    outputs_key = f"pic_foundry_{stage}_sealed"
    artifact_key = f"foundry_{stage}_sealed_summary_json"
    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": outputs_key,
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "source_run_id": ref_run_id,
            "layout_run_id": layout_run_id,
            "execution_mode": execution_mode,
            "pdk": pdk_info.get("name"),
            "deck_fingerprint": summary.get("deck_fingerprint"),
        },
        "outputs_summary": {
            outputs_key: {
                "status": summary.get("status"),
                "execution_backend": summary.get("execution_backend"),
                "failed_checks": counts.get("failed"),
                "errored_checks": counts.get("errored"),
                "source_run_id": ref_run_id,
                "layout_run_id": layout_run_id,
            }
        },
        "artifacts": {
            artifact_key: summary_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)
    append_foundry_metric_event(stage=stage, run_id=run_id, summary=summary)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "summary": summary,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {
            artifact_key: summary_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }


@router.post("/v0/pic/layout/foundry_drc/run")
def pic_layout_foundry_drc_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)
    backend = parse_foundry_drc_backend(payload, execution_mode=execution_mode)
    sealed_run_id = parse_optional_sealed_run_id(payload, field_name="run_id")
    ref_run_id, layout_run_id, ref_dir = resolve_reference_run(payload)
    pdk_manifest = _resolve_pdk_manifest_or_400(
        payload=payload,
        execution_mode=execution_mode,
        ref_run_id=ref_run_id,
        ref_dir=ref_dir,
    )

    sealed_request: dict[str, Any] = {"backend": backend}
    if sealed_run_id is not None:
        sealed_request["run_id"] = sealed_run_id
    if payload.get("deck_fingerprint") is not None:
        sealed_request["deck_fingerprint"] = str(payload.get("deck_fingerprint"))
    if isinstance(payload.get("mock_result"), dict):
        sealed_request["mock_result"] = payload.get("mock_result")
    if backend in {"local_rules", "local"}:
        if isinstance(payload.get("routes"), (dict, list)):
            sealed_request["routes"] = payload.get("routes")
        if isinstance(payload.get("pdk"), dict):
            sealed_request["pdk"] = payload.get("pdk")
    if execution_mode == "certification":
        sealed_request["require_explicit_pdk_rules"] = True

    try:
        summary = run_foundry_drc_sealed(sealed_request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        validate_instance(summary, pic_foundry_drc_sealed_summary_schema_path())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"foundry drc sealed summary schema validation failed: {exc}") from exc
    if execution_mode == "certification":
        enforce_foundry_certification_provenance(summary, stage_label="drc")

    return _persist_foundry_run(
        stage="drc",
        project_id=project_id,
        execution_mode=execution_mode,
        ref_run_id=ref_run_id,
        layout_run_id=layout_run_id,
        pdk_manifest=pdk_manifest,
        summary=summary,
    )


@router.post("/v0/pic/layout/foundry_lvs/run")
def pic_layout_foundry_lvs_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)
    backend = parse_foundry_lvs_backend(payload, execution_mode=execution_mode)
    sealed_run_id = parse_optional_sealed_run_id(payload, field_name="run_id")
    ref_run_id, layout_run_id, ref_dir = resolve_reference_run(payload)
    pdk_manifest = _resolve_pdk_manifest_or_400(
        payload=payload,
        execution_mode=execution_mode,
        ref_run_id=ref_run_id,
        ref_dir=ref_dir,
    )

    sealed_request: dict[str, Any] = {"backend": backend}
    if sealed_run_id is not None:
        sealed_request["run_id"] = sealed_run_id
    if payload.get("deck_fingerprint") is not None:
        sealed_request["deck_fingerprint"] = str(payload.get("deck_fingerprint"))
    if isinstance(payload.get("mock_result"), dict):
        sealed_request["mock_result"] = payload.get("mock_result")
    if isinstance(payload.get("generic_cli"), dict):
        sealed_request["generic_cli"] = payload.get("generic_cli")
    if isinstance(payload.get("generic_cli_command"), list):
        sealed_request["generic_cli_command"] = payload.get("generic_cli_command")
    if payload.get("generic_cli_timeout_sec") is not None:
        sealed_request["generic_cli_timeout_sec"] = payload.get("generic_cli_timeout_sec")
    if backend in {"local_lvs", "local"}:
        if isinstance(payload.get("graph"), dict):
            sealed_request["graph"] = payload.get("graph")
        if isinstance(payload.get("routes"), dict):
            sealed_request["routes"] = payload.get("routes")
        if isinstance(payload.get("ports"), dict):
            sealed_request["ports"] = payload.get("ports")
        if isinstance(payload.get("settings"), dict):
            sealed_request["settings"] = payload.get("settings")
        if payload.get("coord_tol_um") is not None:
            sealed_request["coord_tol_um"] = payload.get("coord_tol_um")

    try:
        summary = run_foundry_lvs_sealed(sealed_request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        validate_instance(summary, pic_foundry_lvs_sealed_summary_schema_path())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"foundry lvs sealed summary schema validation failed: {exc}") from exc
    if execution_mode == "certification":
        enforce_foundry_certification_provenance(summary, stage_label="lvs")

    return _persist_foundry_run(
        stage="lvs",
        project_id=project_id,
        execution_mode=execution_mode,
        ref_run_id=ref_run_id,
        layout_run_id=layout_run_id,
        pdk_manifest=pdk_manifest,
        summary=summary,
    )


@router.post("/v0/pic/layout/foundry_pex/run")
def pic_layout_foundry_pex_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)
    backend = parse_foundry_pex_backend(payload, execution_mode=execution_mode)
    sealed_run_id = parse_optional_sealed_run_id(payload, field_name="run_id")
    ref_run_id, layout_run_id, ref_dir = resolve_reference_run(payload)
    pdk_manifest = _resolve_pdk_manifest_or_400(
        payload=payload,
        execution_mode=execution_mode,
        ref_run_id=ref_run_id,
        ref_dir=ref_dir,
    )

    sealed_request: dict[str, Any] = {"backend": backend}
    if sealed_run_id is not None:
        sealed_request["run_id"] = sealed_run_id
    if payload.get("deck_fingerprint") is not None:
        sealed_request["deck_fingerprint"] = str(payload.get("deck_fingerprint"))
    if isinstance(payload.get("mock_result"), dict):
        sealed_request["mock_result"] = payload.get("mock_result")
    if isinstance(payload.get("generic_cli"), dict):
        sealed_request["generic_cli"] = payload.get("generic_cli")
    if isinstance(payload.get("generic_cli_command"), list):
        sealed_request["generic_cli_command"] = payload.get("generic_cli_command")
    if payload.get("generic_cli_timeout_sec") is not None:
        sealed_request["generic_cli_timeout_sec"] = payload.get("generic_cli_timeout_sec")
    if backend in {"local_pex", "local"}:
        if isinstance(payload.get("graph"), dict):
            sealed_request["graph"] = payload.get("graph")
        if isinstance(payload.get("routes"), (dict, list)):
            sealed_request["routes"] = payload.get("routes")
        if isinstance(payload.get("pdk"), dict):
            sealed_request["pdk"] = payload.get("pdk")
    if execution_mode == "certification":
        sealed_request["require_explicit_pex_rules"] = True

    try:
        summary = run_foundry_pex_sealed(sealed_request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        validate_instance(summary, pic_foundry_pex_sealed_summary_schema_path())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"foundry pex sealed summary schema validation failed: {exc}") from exc
    if execution_mode == "certification":
        enforce_foundry_certification_provenance(summary, stage_label="pex")

    return _persist_foundry_run(
        stage="pex",
        project_id=project_id,
        execution_mode=execution_mode,
        ref_run_id=ref_run_id,
        layout_run_id=layout_run_id,
        pdk_manifest=pdk_manifest,
        summary=summary,
    )
