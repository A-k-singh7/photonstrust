"""PIC workflow routes."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from photonstrust.api import runs as run_store
from photonstrust.api.common import dict_or_empty
from photonstrust.api.common import graph_from_payload
from photonstrust.api.common import project_id_or_400
from photonstrust.api.common import parse_execution_mode
from photonstrust.api.common import reject_output_root_override
from photonstrust.api.routers.layout import pic_layout_build
from photonstrust.api.routers.layout import pic_layout_klayout_run
from photonstrust.api.routers.layout import pic_layout_lvs_lite
from photonstrust.api.routers.pic import pic_invdesign_coupler_ratio
from photonstrust.api.routers.pic import pic_invdesign_mzi_phase
from photonstrust.api.routers.pic import pic_spice_export
from photonstrust.api.routers.runs import runs_get
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.utils import hash_dict


router = APIRouter()


def _safe_workflow_error_message(*, fallback: str) -> str:
    return str(fallback).strip() or "workflow step failed"


def _normalize_invdesign_kind(payload: dict[str, Any], inv_cfg: dict[str, Any]) -> str:
    inv_kind_raw = inv_cfg.get("kind")
    if inv_kind_raw is None:
        inv_kind_raw = payload.get("invdesign_kind")
    inv_kind = str(inv_kind_raw or "mzi_phase").strip().lower()
    if inv_kind in {"pic.invdesign.mzi_phase", "mzi_phase"}:
        return "mzi_phase"
    if inv_kind in {"pic.invdesign.coupler_ratio", "coupler_ratio"}:
        return "coupler_ratio"
    raise HTTPException(status_code=400, detail="Unsupported invdesign.kind (expected 'mzi_phase' or 'coupler_ratio')")


@router.post("/v0/pic/workflow/invdesign_chain")
def pic_workflow_invdesign_chain(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Run a chained PIC workflow."""

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object payload")

    graph = graph_from_payload(payload)

    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)

    require_schema = bool(payload.get("require_schema", False))
    execution_mode = parse_execution_mode(payload)

    inv_cfg = dict_or_empty(payload.get("invdesign"))
    inv_kind = _normalize_invdesign_kind(payload, inv_cfg)

    inv_payload: dict[str, Any] = {
        "graph": graph,
        "project_id": project_id,
        "execution_mode": execution_mode,
    }
    if inv_kind == "mzi_phase":
        if str(inv_cfg.get("phase_node_id", "")).strip():
            inv_payload["phase_node_id"] = str(inv_cfg.get("phase_node_id", "")).strip()
        inv_payload["target_power_fraction"] = float(inv_cfg.get("target_power_fraction", 0.9))
        inv_payload["steps"] = int(inv_cfg.get("steps", 181) or 181)
    else:
        if str(inv_cfg.get("coupler_node_id", "")).strip():
            inv_payload["coupler_node_id"] = str(inv_cfg.get("coupler_node_id", "")).strip()
        inv_payload["target_power_fraction"] = float(inv_cfg.get("target_power_fraction", 0.5))
        inv_payload["steps"] = int(inv_cfg.get("steps", 101) or 101)

    if str(inv_cfg.get("target_output_node", "")).strip():
        inv_payload["target_output_node"] = str(inv_cfg.get("target_output_node", "")).strip()
    if str(inv_cfg.get("target_output_port", "")).strip():
        inv_payload["target_output_port"] = str(inv_cfg.get("target_output_port", "")).strip()
    if isinstance(inv_cfg.get("wavelength_sweep_nm"), list):
        inv_payload["wavelength_sweep_nm"] = inv_cfg.get("wavelength_sweep_nm")
    if isinstance(inv_cfg.get("robustness_cases"), list):
        inv_payload["robustness_cases"] = inv_cfg.get("robustness_cases")
    if isinstance(inv_cfg.get("robustness_thresholds"), dict):
        inv_payload["robustness_thresholds"] = inv_cfg.get("robustness_thresholds")
    if inv_cfg.get("robustness_required") is not None:
        inv_payload["robustness_required"] = bool(inv_cfg.get("robustness_required"))
    if str(inv_cfg.get("wavelength_objective_agg", "")).strip():
        inv_payload["wavelength_objective_agg"] = str(inv_cfg.get("wavelength_objective_agg", "")).strip()
    if str(inv_cfg.get("case_objective_agg", "")).strip():
        inv_payload["case_objective_agg"] = str(inv_cfg.get("case_objective_agg", "")).strip()
    if str(inv_cfg.get("solver_backend", "")).strip():
        inv_payload["solver_backend"] = str(inv_cfg.get("solver_backend", "")).strip()
    if isinstance(inv_cfg.get("solver_plugin"), dict):
        inv_payload["solver_plugin"] = inv_cfg.get("solver_plugin")

    inv_res = pic_invdesign_mzi_phase(inv_payload) if inv_kind == "mzi_phase" else pic_invdesign_coupler_ratio(inv_payload)
    optimized_graph = inv_res.get("optimized_graph") if isinstance(inv_res, dict) else None
    if not isinstance(optimized_graph, dict):
        raise HTTPException(status_code=400, detail="invdesign did not return optimized_graph")

    layout_cfg = dict_or_empty(payload.get("layout"))
    layout_payload: dict[str, Any] = {
        "graph": optimized_graph,
        "project_id": project_id,
        "require_schema": bool(layout_cfg.get("require_schema", require_schema)),
        "execution_mode": execution_mode,
    }
    if isinstance(layout_cfg.get("pdk"), dict):
        layout_payload["pdk"] = layout_cfg.get("pdk")
    if isinstance(layout_cfg.get("settings"), dict):
        layout_payload["settings"] = layout_cfg.get("settings")
    layout_res = pic_layout_build(layout_payload)

    layout_run_id = str(layout_res.get("run_id", "")).strip() if isinstance(layout_res, dict) else ""
    if not layout_run_id:
        raise HTTPException(status_code=400, detail="layout build did not return run_id")

    lvs_cfg = dict_or_empty(payload.get("lvs_lite"))
    lvs_payload: dict[str, Any] = {
        "graph": optimized_graph,
        "project_id": project_id,
        "layout_run_id": layout_run_id,
        "require_schema": bool(lvs_cfg.get("require_schema", require_schema)),
        "execution_mode": execution_mode,
    }
    if isinstance(lvs_cfg.get("settings"), dict):
        lvs_payload["settings"] = lvs_cfg.get("settings")
    if isinstance(lvs_cfg.get("signoff_bundle"), dict):
        lvs_payload["signoff_bundle"] = lvs_cfg.get("signoff_bundle")
    lvs_res = pic_layout_lvs_lite(lvs_payload)

    klayout_cfg = dict_or_empty(payload.get("klayout"))
    klayout_enabled = bool(klayout_cfg.get("enabled", True))
    klayout_settings = klayout_cfg.get("settings") if isinstance(klayout_cfg.get("settings"), dict) else {}
    klayout_step: dict[str, Any] = {"status": "skipped", "run_id": None, "note": "optional"}
    if klayout_enabled:
        try:
            layout_dir = run_store.run_dir_for_id(layout_run_id)
            layout_manifest = dict_or_empty(run_store.read_run_manifest(layout_dir))
            layout_artifacts = dict_or_empty(layout_manifest.get("artifacts"))
            gds_rel = layout_artifacts.get("layout_gds")
            if isinstance(klayout_cfg.get("gds_artifact_path"), str) and str(klayout_cfg.get("gds_artifact_path")).strip():
                gds_rel = str(klayout_cfg.get("gds_artifact_path")).strip()
        except Exception:
            gds_rel = None

        if isinstance(gds_rel, str) and gds_rel.strip():
            try:
                k_res = pic_layout_klayout_run(
                    {
                        "project_id": project_id,
                        "source_run_id": layout_run_id,
                        "gds_artifact_path": str(gds_rel).strip(),
                        "settings": klayout_settings,
                        "execution_mode": execution_mode,
                    }
                )
                pack = k_res.get("pack") if isinstance(k_res, dict) else None
                pack_status = pack.get("status") if isinstance(pack, dict) else None
                klayout_step = {
                    "status": str(pack_status or "ok"),
                    "run_id": k_res.get("run_id") if isinstance(k_res, dict) else None,
                    "artifact_relpaths": k_res.get("artifact_relpaths") if isinstance(k_res, dict) else None,
                }
            except HTTPException as exc:
                klayout_step = {
                    "status": "error",
                    "run_id": None,
                    "error": _safe_workflow_error_message(fallback="klayout pack step failed"),
                }
            except Exception:
                klayout_step = {
                    "status": "error",
                    "run_id": None,
                    "error": _safe_workflow_error_message(fallback="klayout pack step failed"),
                }
        else:
            klayout_step = {"status": "skipped", "run_id": None, "reason": "layout did not emit a .gds artifact"}

    spice_cfg = dict_or_empty(payload.get("spice"))
    spice_payload: dict[str, Any] = {
        "graph": optimized_graph,
        "project_id": project_id,
        "require_schema": bool(spice_cfg.get("require_schema", require_schema)),
    }
    if isinstance(spice_cfg.get("settings"), dict):
        spice_payload["settings"] = spice_cfg.get("settings")
    spice_res = pic_spice_export(spice_payload)

    workflow_run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(workflow_run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    generated_at = generated_at_utc()
    replayed_from_run_id = str(payload.get("replayed_from_run_id", "")).strip() or None

    request_rel = "workflow_request.json"
    try:
        request_snapshot = json.loads(json.dumps(payload))
    except Exception:
        request_snapshot = {}
    request_snapshot = dict_or_empty(request_snapshot)
    request_snapshot.pop("output_root", None)
    request_snapshot["project_id"] = project_id
    if isinstance(request_snapshot.get("invdesign"), dict):
        request_snapshot["invdesign"]["kind"] = inv_kind
    (Path(run_dir) / request_rel).write_text(json.dumps(request_snapshot, indent=2), encoding="utf-8")

    lvs_report = dict_or_empty(lvs_res.get("report") if isinstance(lvs_res, dict) else None)
    lvs_summary = dict_or_empty(lvs_report.get("summary"))
    lvs_pass = bool(lvs_summary.get("pass"))
    overall_status = "pass" if lvs_pass else "fail"

    provenance = runtime_provenance()
    report_rel = "workflow_report.json"
    report = {
        "schema_version": "0.1",
        "generated_at": generated_at,
        "kind": "pic.workflow.invdesign_chain",
        "inputs": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "invdesign_kind": inv_kind,
            "invdesign_settings_hash": hash_dict(inv_cfg),
            "layout_settings_hash": hash_dict(layout_cfg),
            "lvs_lite_settings_hash": hash_dict(lvs_cfg),
            "klayout_settings_hash": hash_dict(klayout_cfg),
            "spice_settings_hash": hash_dict(spice_cfg),
        },
        "steps": {
            "invdesign": {
                "run_id": inv_res.get("run_id") if isinstance(inv_res, dict) else None,
                "kind": dict_or_empty(inv_res.get("report") if isinstance(inv_res, dict) else None).get("kind"),
                "artifact_relpaths": inv_res.get("artifact_relpaths") if isinstance(inv_res, dict) else None,
            },
            "layout_build": {
                "run_id": layout_res.get("run_id") if isinstance(layout_res, dict) else None,
                "artifact_relpaths": layout_res.get("artifact_relpaths") if isinstance(layout_res, dict) else None,
            },
            "lvs_lite": {
                "run_id": lvs_res.get("run_id") if isinstance(lvs_res, dict) else None,
                "pass": lvs_pass,
                "artifact_relpaths": lvs_res.get("artifact_relpaths") if isinstance(lvs_res, dict) else None,
            },
            "klayout_pack": klayout_step,
            "spice_export": {
                "run_id": spice_res.get("run_id") if isinstance(spice_res, dict) else None,
                "artifact_relpaths": spice_res.get("artifact_relpaths") if isinstance(spice_res, dict) else None,
            },
        },
        "summary": {"status": overall_status},
        "provenance": provenance,
    }
    if replayed_from_run_id:
        report["inputs"]["replayed_from_run_id"] = str(replayed_from_run_id)
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")

    outputs_summary = {
        "pic_workflow": {
            "kind": "pic.workflow.invdesign_chain",
            "status": overall_status,
            "invdesign_kind": inv_kind,
            "invdesign_run_id": inv_res.get("run_id") if isinstance(inv_res, dict) else None,
            "layout_run_id": layout_res.get("run_id") if isinstance(layout_res, dict) else None,
            "lvs_lite_run_id": lvs_res.get("run_id") if isinstance(lvs_res, dict) else None,
            "klayout_pack_run_id": klayout_step.get("run_id"),
            "klayout_pack_status": klayout_step.get("status"),
            "spice_export_run_id": spice_res.get("run_id") if isinstance(spice_res, dict) else None,
        }
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": workflow_run_id,
        "run_type": "pic_workflow_invdesign_chain",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "invdesign_kind": inv_kind,
            "execution_mode": execution_mode,
            "replayed_from_run_id": replayed_from_run_id,
        },
        "outputs_summary": outputs_summary,
        "artifacts": {"workflow_report_json": report_rel, "workflow_request_json": request_rel},
        "provenance": provenance,
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": workflow_run_id,
        "output_dir": str(run_dir),
        "status": overall_status,
        "optimized_graph": optimized_graph,
        "steps": report.get("steps"),
        "report": report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {"workflow_report_json": report_rel, "workflow_request_json": request_rel},
        "provenance": provenance,
    }


@router.post("/v0/pic/workflow/invdesign_chain/replay")
def pic_workflow_invdesign_chain_replay(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Replay a prior workflow run from its recorded request snapshot."""

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object payload")

    workflow_run_id = str(payload.get("workflow_run_id", "")).strip()
    if not workflow_run_id:
        raise HTTPException(status_code=400, detail="workflow_run_id is required")
    try:
        workflow_run_id = run_store.validate_run_id(workflow_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid workflow_run_id format") from exc

    try:
        src_dir = run_store.run_dir_for_id(workflow_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not resolve workflow run directory") from exc
    if not src_dir.exists():
        raise HTTPException(status_code=404, detail="workflow run not found")

    src_manifest = run_store.read_run_manifest(src_dir)
    if not isinstance(src_manifest, dict):
        src_manifest = runs_get(workflow_run_id, request)
    if not isinstance(src_manifest, dict) or str(src_manifest.get("run_type", "")).strip() != "pic_workflow_invdesign_chain":
        raise HTTPException(status_code=400, detail="run_id is not a pic_workflow_invdesign_chain workflow run")

    try:
        req_path = run_store.resolve_artifact_path(src_dir, "workflow_request.json")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="workflow run does not contain workflow_request.json (cannot replay)")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="failed to resolve workflow_request.json") from exc
    try:
        request_payload = json.loads(req_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="failed to read workflow_request.json") from exc
    if not isinstance(request_payload, dict):
        raise HTTPException(status_code=400, detail="workflow_request.json must be a JSON object")

    if payload.get("project_id") is not None:
        raw_project_id = str(payload.get("project_id", "")).strip()
        if raw_project_id:
            try:
                request_payload["project_id"] = project_id_or_400({"project_id": raw_project_id})
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid project_id format") from exc

    request_payload["replayed_from_run_id"] = workflow_run_id
    return {
        "generated_at": generated_at_utc(),
        "replayed_from_run_id": workflow_run_id,
        "workflow": pic_workflow_invdesign_chain(request_payload),
    }
