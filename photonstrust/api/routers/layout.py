"""PIC layout build, LVS-lite, and KLayout routes."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from photonstrust.api import runs as run_store
from photonstrust.api.common import graph_from_payload
from photonstrust.api.common import parse_execution_mode
from photonstrust.api.common import project_id_or_400
from photonstrust.api.common import reject_output_root_override
from photonstrust.api.common import resolve_reference_run
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.services.pdk_manifests import resolve_run_pdk_manifest
from photonstrust.api.services.pdk_manifests import write_pdk_manifest_artifact
from photonstrust.layout.pic.build_layout import build_pic_layout_artifacts
from photonstrust.layout.pic.klayout_artifact_pack import build_klayout_run_artifact_pack
from photonstrust.utils import hash_dict
from photonstrust.verification.lvs_lite import run_pic_lvs_lite


router = APIRouter()


@router.post("/v0/pic/layout/build")
def pic_layout_build(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None
    require_schema = bool(payload.get("require_schema", False))

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        report = build_pic_layout_artifacts(
            {
                "graph": graph,
                "pdk": pdk_req,
                "settings": payload.get("settings") if isinstance(payload.get("settings"), dict) else None,
            },
            run_dir,
            require_schema=require_schema,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="layout build failed") from exc

    generated_at = generated_at_utc()
    report_rel = "layout_build_report.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")

    pdk_manifest = resolve_run_pdk_manifest(
        pdk_request=pdk_req,
        execution_mode=execution_mode,
        require_context_in_cert=False,
    )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(status_code=400, detail="failed to resolve pdk_manifest for layout build run")
    pdk_manifest_rel = write_pdk_manifest_artifact(run_dir, pdk_manifest)

    artifacts = dict(report.get("artifacts", {}) or {})
    ports_rel = str(artifacts.get("ports_json_path") or "ports.json")
    routes_rel = str(artifacts.get("routes_json_path") or "routes.json")
    prov_rel = str(artifacts.get("layout_provenance_json_path") or "layout_provenance.json")
    gds_rel = artifacts.get("layout_gds_path")

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "pic_layout_build",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "execution_mode": execution_mode,
            "pdk": (report.get("pdk", {}) or {}).get("name"),
            "settings_hash": hash_dict(report.get("settings", {}) or {}),
        },
        "outputs_summary": {
            "pic_layout": {
                "nodes": (report.get("summary", {}) or {}).get("nodes"),
                "edges": (report.get("summary", {}) or {}).get("edges"),
                "ports": (report.get("summary", {}) or {}).get("ports"),
                "routes": (report.get("summary", {}) or {}).get("routes"),
                "gds_emitted": (report.get("summary", {}) or {}).get("gds_emitted"),
                "pdk": (report.get("pdk", {}) or {}).get("name"),
            }
        },
        "artifacts": {
            "layout_build_report_json": report_rel,
            "ports_json": ports_rel,
            "routes_json": routes_rel,
            "layout_provenance_json": prov_rel,
            "layout_gds": gds_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "graph_hash": hash_dict(graph),
        "report": report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {
            "layout_build_report_json": report_rel,
            "ports_json": ports_rel,
            "routes_json": routes_rel,
            "layout_provenance_json": prov_rel,
            "layout_gds": gds_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }


@router.post("/v0/pic/layout/lvs_lite")
def pic_layout_lvs_lite(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    require_schema = bool(payload.get("require_schema", False))
    execution_mode = parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    ports = payload.get("ports")
    routes = payload.get("routes")
    layout_run_id = str(payload.get("layout_run_id", "")).strip()
    layout_dir: Path | None = None
    if layout_run_id:
        try:
            layout_dir = run_store.run_dir_for_id(layout_run_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid layout_run_id") from exc
        if not layout_dir.exists():
            raise HTTPException(status_code=404, detail="layout_run_id not found")

        ports_path = layout_dir / "ports.json"
        routes_path = layout_dir / "routes.json"
        if not ports_path.exists() or not routes_path.exists():
            raise HTTPException(status_code=400, detail="layout run does not contain ports.json/routes.json artifacts")
        try:
            ports = json.loads(ports_path.read_text(encoding="utf-8"))
            routes = json.loads(routes_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="failed to read layout sidecars") from exc

    if not isinstance(ports, dict) or not isinstance(routes, dict):
        raise HTTPException(status_code=400, detail="Provide ports/routes objects or layout_run_id")

    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    signoff_bundle = payload.get("signoff_bundle") if isinstance(payload.get("signoff_bundle"), dict) else None
    pdk_manifest = resolve_run_pdk_manifest(
        pdk_request=pdk_req,
        execution_mode=execution_mode,
        source_run_dir=layout_dir,
        source_run_id=layout_run_id or None,
        require_context_in_cert=True,
    )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(
            status_code=400,
            detail=(
                "certification mode requires pdk_manifest context; provide layout_run_id with pdk_manifest_json "
                "or provide payload.pdk"
            ),
        )

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    request_payload: dict[str, Any] = {
        "graph": graph,
        "ports": ports,
        "routes": routes,
        "settings": settings,
    }
    if isinstance(signoff_bundle, dict):
        request_payload["signoff_bundle"] = signoff_bundle
    try:
        report = run_pic_lvs_lite(request_payload, require_schema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="lvs_lite run failed") from exc

    generated_at = generated_at_utc()
    report_rel = "lvs_lite_report.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")
    pdk_manifest_rel = write_pdk_manifest_artifact(run_dir, pdk_manifest)

    outputs_summary = {"pic_lvs_lite": dict(report.get("summary", {}) or {})}
    lvs_violations = report.get("violations_annotated") if isinstance(report.get("violations_annotated"), list) else []
    outputs_summary["pic_lvs_lite"]["violations_annotated"] = lvs_violations
    if layout_run_id:
        outputs_summary["pic_lvs_lite"]["layout_run_id"] = layout_run_id

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "pic_lvs_lite",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "execution_mode": execution_mode,
            "layout_run_id": layout_run_id or None,
            "pdk": ((pdk_manifest.get("pdk") or {}).get("name") if isinstance(pdk_manifest, dict) else None),
            "ports_hash": hash_dict(ports),
            "routes_hash": hash_dict(routes),
        },
        "outputs_summary": outputs_summary,
        "artifacts": {
            "lvs_lite_report_json": report_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "graph_hash": hash_dict(graph),
        "report": report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {
            "lvs_lite_report_json": report_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": runtime_provenance(),
    }


@router.post("/v0/pic/layout/klayout/run")
def pic_layout_klayout_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    ref_run_id, layout_run_id, ref_dir = resolve_reference_run(payload)

    ref_manifest = run_store.read_run_manifest(ref_dir) or {}
    declared_raw = ref_manifest.get("artifacts") if isinstance(ref_manifest, dict) else None
    declared: dict[str, Any] = declared_raw if isinstance(declared_raw, dict) else {}
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

    gds_rel = str(payload.get("gds_artifact_path", "") or "").strip() or None
    if not gds_rel:
        raw = declared.get("layout_gds")
        if isinstance(raw, str) and raw.strip():
            gds_rel = str(raw).strip()
        else:
            candidates = []
            for value in declared.values():
                if isinstance(value, str) and value.strip().lower().endswith(".gds"):
                    candidates.append(str(value).strip())
            candidates = sorted(set(candidates), key=lambda item: item.lower())
            if len(candidates) == 1:
                gds_rel = candidates[0]
        if not gds_rel and (ref_dir / "layout.gds").exists():
            gds_rel = "layout.gds"
    if not gds_rel:
        raise HTTPException(
            status_code=400,
            detail="gds_artifact_path is required for this run (no default .gds artifact was found)",
        )

    try:
        gds_path = run_store.resolve_artifact_path(ref_dir, str(gds_rel))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=f"GDS artifact not found in source run: {gds_rel}") from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail="failed to resolve source GDS artifact") from exc

    settings_raw_obj = payload.get("settings")
    settings_raw: dict[str, Any] = settings_raw_obj if isinstance(settings_raw_obj, dict) else {}
    settings: dict[str, Any] = dict(settings_raw)
    try:
        merged_settings: dict[str, Any] = dict(settings)
        if "layout_build_report_json" in declared and isinstance(declared.get("layout_build_report_json"), str):
            rep_rel = str(declared.get("layout_build_report_json") or "").strip()
            if rep_rel:
                rep_path = run_store.resolve_artifact_path(ref_dir, rep_rel)
                rep = json.loads(rep_path.read_text(encoding="utf-8"))
                if isinstance(rep, dict):
                    rep_settings_raw = rep.get("settings")
                    rep_settings: dict[str, Any] = rep_settings_raw if isinstance(rep_settings_raw, dict) else {}
                    rep_pdk_raw = rep.get("pdk")
                    rep_pdk: dict[str, Any] = rep_pdk_raw if isinstance(rep_pdk_raw, dict) else {}
                    rep_rules_raw = rep_pdk.get("design_rules")
                    rep_rules: dict[str, Any] = rep_rules_raw if isinstance(rep_rules_raw, dict) else {}

                    min_width_um = rep_rules.get("min_waveguide_width_um")
                    if "min_waveguide_width_um" not in merged_settings and min_width_um is not None:
                        merged_settings["min_waveguide_width_um"] = float(min_width_um)
                    if "waveguide_layer" not in merged_settings and isinstance(rep_settings.get("waveguide_layer"), dict):
                        merged_settings["waveguide_layer"] = rep_settings.get("waveguide_layer")
                    if "label_layer" not in merged_settings and isinstance(rep_settings.get("label_layer"), dict):
                        merged_settings["label_layer"] = rep_settings.get("label_layer")
                    if "label_prefix" not in merged_settings and rep_settings.get("label_prefix") is not None:
                        merged_settings["label_prefix"] = str(rep_settings.get("label_prefix") or "").strip() or None
                    if "top_cell" not in merged_settings:
                        cell_name = str(rep_settings.get("cell_name") or "").strip()
                        if cell_name:
                            merged_settings["top_cell"] = cell_name
        settings = merged_settings
    except Exception:
        settings = dict(settings)

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        pack = build_klayout_run_artifact_pack(
            input_gds_path=gds_path,
            output_dir=run_dir,
            settings=settings,
            allow_missing_tool=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="klayout artifact pack failed") from exc

    generated_at = generated_at_utc()
    pdk_manifest_rel = write_pdk_manifest_artifact(run_dir, pdk_manifest)
    pack_rel = "klayout_run_artifact_pack.json"
    stdout_rel = "klayout_stdout.txt"
    stderr_rel = "klayout_stderr.txt"
    outputs = pack.get("outputs") if isinstance(pack, dict) else None
    if not isinstance(outputs, dict):
        outputs = {}

    artifacts = {
        "klayout_run_artifact_pack_json": pack_rel,
        "klayout_stdout_txt": stdout_rel,
        "klayout_stderr_txt": stderr_rel,
        "ports_extracted_json": outputs.get("ports_extracted_json"),
        "routes_extracted_json": outputs.get("routes_extracted_json"),
        "drc_lite_json": outputs.get("drc_lite_json"),
        "macro_provenance_json": outputs.get("macro_provenance_json"),
        "pdk_manifest_json": pdk_manifest_rel,
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "pic_klayout_artifact_pack",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "source_run_id": ref_run_id,
            "source_gds_artifact_path": str(gds_rel),
            "layout_run_id": layout_run_id or None,
            "execution_mode": execution_mode,
            "pdk": ((pdk_manifest.get("pdk") or {}).get("name") if isinstance(pdk_manifest, dict) else None),
            "settings_hash": hash_dict(settings),
        },
        "outputs_summary": {
            "pic_klayout": {
                "status": pack.get("status") if isinstance(pack, dict) else None,
                "drc_status": (pack.get("summary") or {}).get("drc_status") if isinstance(pack, dict) else None,
                "ports_extracted": (pack.get("summary") or {}).get("ports_extracted") if isinstance(pack, dict) else None,
                "routes_extracted": (pack.get("summary") or {}).get("routes_extracted") if isinstance(pack, dict) else None,
                "issue_count": (pack.get("summary") or {}).get("issue_count") if isinstance(pack, dict) else None,
                "error_count": (pack.get("summary") or {}).get("error_count") if isinstance(pack, dict) else None,
                "source_run_id": ref_run_id,
                "layout_run_id": layout_run_id or None,
            }
        },
        "artifacts": artifacts,
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "pack": pack,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": artifacts,
        "provenance": runtime_provenance(),
    }
