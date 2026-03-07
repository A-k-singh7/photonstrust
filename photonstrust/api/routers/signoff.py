"""Signoff-adjacent verification routes."""

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
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.services.pdk_manifests import coerce_pdk_manifest_payload
from photonstrust.api.services.pdk_manifests import resolve_run_pdk_manifest
from photonstrust.api.services.pdk_manifests import write_pdk_manifest_artifact
from photonstrust.utils import hash_dict
from photonstrust.verification.performance_drc import run_parallel_waveguide_crosstalk_check


router = APIRouter()


@router.post("/v0/performance_drc/crosstalk")
def performance_drc_crosstalk(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    pdk_manifest = None
    if isinstance(payload.get("pdk_manifest"), dict):
        pdk_manifest = coerce_pdk_manifest_payload(
            payload.get("pdk_manifest"),
            execution_mode=execution_mode,
        )
    if not isinstance(pdk_manifest, dict):
        pdk_manifest = resolve_run_pdk_manifest(
            pdk_request=pdk_req,
            execution_mode=execution_mode,
            require_context_in_cert=True,
        )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(
            status_code=400,
            detail="certification mode requires explicit pdk manifest context (provide payload.pdk or payload.pdk_manifest)",
        )
    pdk_manifest = dict(pdk_manifest)

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    try:
        report = run_parallel_waveguide_crosstalk_check(payload, output_dir=run_dir, run_id=run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    report = dict(report)

    generated_at = generated_at_utc()
    report_json_rel = "performance_drc_report.json"
    report_html_rel = "performance_drc_report.html"
    pdk_manifest_rel = write_pdk_manifest_artifact(run_dir, pdk_manifest)

    drc_results = report.get("results") if isinstance(report.get("results"), dict) else {}
    report_check_raw = report.get("check")
    report_check = report_check_raw if isinstance(report_check_raw, dict) else {}
    report_provenance_raw = report.get("provenance")
    report_provenance = report_provenance_raw if isinstance(report_provenance_raw, dict) else {}
    pdk_info_raw = pdk_manifest.get("pdk")
    pdk_info = pdk_info_raw if isinstance(pdk_info_raw, dict) else {}
    drc_loss = drc_results.get("loss_budget") if isinstance(drc_results.get("loss_budget"), dict) else None
    drc_violations = drc_results.get("violations") if isinstance(drc_results.get("violations"), list) else []
    drc_violation_summary = drc_results.get("violation_summary") if isinstance(drc_results.get("violation_summary"), dict) else {}
    outputs_summary = {
        "performance_drc": {
            "status": drc_results.get("status"),
            "worst_xt_db": drc_results.get("worst_xt_db"),
            "recommended_min_gap_um": drc_results.get("recommended_min_gap_um"),
            "violation_summary": drc_violation_summary,
            "violations_annotated": drc_violations,
            "loss_budget": {
                "pass": (drc_loss or {}).get("pass") if isinstance(drc_loss, dict) else None,
                "route_count": (drc_loss or {}).get("route_count") if isinstance(drc_loss, dict) else None,
                "worst_route_id": (drc_loss or {}).get("worst_route_id") if isinstance(drc_loss, dict) else None,
                "worst_route_loss_db": (drc_loss or {}).get("worst_route_loss_db") if isinstance(drc_loss, dict) else None,
            }
            if isinstance(drc_loss, dict)
            else None,
        }
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "performance_drc",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "execution_mode": execution_mode,
            "pdk": pdk_info.get("name"),
            "check_kind": report_check.get("kind"),
            "input_hash": report_provenance.get("input_hash"),
            "model_hash": report_provenance.get("model_hash"),
        },
        "outputs_summary": outputs_summary,
        "artifacts": {
            "performance_drc_report_json": report_json_rel,
            "performance_drc_report_html": report_html_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "report": report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {
            "performance_drc_report_json": report_json_rel,
            "performance_drc_report_html": report_html_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }
