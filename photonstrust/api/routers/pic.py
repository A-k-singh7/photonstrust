"""PIC simulation, inverse-design, and export routes."""

from __future__ import annotations

from collections.abc import Callable
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
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.services.invdesign_evidence import enforce_invdesign_evidence_or_400
from photonstrust.graph.compiler import compile_graph
from photonstrust.invdesign import inverse_design_coupler_ratio, inverse_design_mzi_phase
from photonstrust.pic import simulate_pic_netlist, simulate_pic_netlist_sweep
from photonstrust.spice.export import export_pic_graph_to_spice_artifacts
from photonstrust.utils import hash_dict


router = APIRouter()


def _compile_pic_netlist_or_400(graph: dict[str, Any], *, route_name: str) -> dict[str, Any]:
    try:
        compiled = compile_graph(graph, require_schema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="PIC graph compilation failed") from exc
    if compiled.profile != "pic_circuit":
        raise HTTPException(status_code=400, detail=f"{route_name} expects profile=pic_circuit")

    netlist = dict(compiled.compiled)
    for node in netlist.get("nodes", []) or []:
        if str((node or {}).get("kind", "")).strip().lower() == "pic.touchstone_2port":
            raise HTTPException(
                status_code=400,
                detail="pic.touchstone_2port is disabled in the API server (file access). Use CLI workflows.",
            )
    return netlist


def _first_node_id_by_kind(netlist: dict[str, Any], *, node_kind: str) -> str:
    for node in netlist.get("nodes", []) or []:
        if str((node or {}).get("kind", "")).strip().lower() == node_kind:
            return str((node or {}).get("id", "")).strip()
    return ""


def _wavelength_sweep_or_400(payload: dict[str, Any], *, netlist: dict[str, Any]) -> list[float]:
    wavelengths_nm = payload.get("wavelength_sweep_nm")
    if wavelengths_nm is None:
        wl = (netlist.get("circuit", {}) or {}).get("wavelength_nm", 1550.0)
        wavelengths_nm = [wl]
    try:
        return [float(value) for value in (wavelengths_nm or [])]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid wavelength_sweep_nm: {exc}") from exc


def _optimized_graph_with_updated_param(
    graph: dict[str, Any],
    *,
    node_id: str,
    param_name: str,
    param_value: float,
) -> dict[str, Any]:
    optimized_graph = json.loads(json.dumps(graph))
    for node in optimized_graph.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if str(node.get("id", "")).strip() != node_id:
            continue
        params = node.get("params", {}) if isinstance(node.get("params"), dict) else {}
        params[param_name] = float(param_value)
        node["params"] = params
    return optimized_graph


def _invdesign_common_options(
    payload: dict[str, Any],
    *,
    execution_mode: str,
    netlist: dict[str, Any],
    target_fraction_default: float,
    steps_default: int,
) -> dict[str, Any]:
    target_output_node = str(payload.get("target_output_node", "cpl_out")).strip() or "cpl_out"
    target_output_port = str(payload.get("target_output_port", "out1")).strip() or "out1"
    robustness_required = bool(payload.get("robustness_required", execution_mode == "certification"))
    if execution_mode == "certification":
        robustness_required = True
    return {
        "target_output_node": target_output_node,
        "target_output_port": target_output_port,
        "target_power_fraction": float(payload.get("target_power_fraction", target_fraction_default)),
        "steps": int(payload.get("steps", steps_default) or steps_default),
        "robustness_cases": payload.get("robustness_cases") if isinstance(payload.get("robustness_cases"), list) else None,
        "wavelength_objective_agg": str(payload.get("wavelength_objective_agg", "mean") or "mean"),
        "case_objective_agg": str(payload.get("case_objective_agg", "mean") or "mean"),
        "robustness_thresholds": (
            payload.get("robustness_thresholds") if isinstance(payload.get("robustness_thresholds"), dict) else None
        ),
        "robustness_required": robustness_required,
        "solver_backend": str(payload.get("solver_backend", "core") or "core"),
        "solver_plugin": payload.get("solver_plugin") if isinstance(payload.get("solver_plugin"), dict) else None,
        "wavelengths_nm": _wavelength_sweep_or_400(payload, netlist=netlist),
        "execution_mode": execution_mode,
    }


def _persist_invdesign_run(
    *,
    run_id: str,
    run_dir: Path,
    graph: dict[str, Any],
    project_id: str,
    execution_mode: str,
    invdesign_kind: str,
    design_node_id: str,
    design_param: str,
    best_value: float,
    achieved_fraction: float,
    objective: float,
    report: dict[str, Any],
    optimized_graph: dict[str, Any],
) -> dict[str, Any]:
    generated_at = generated_at_utc()
    provenance = runtime_provenance()
    report_rel = "invdesign_report.json"
    graph_rel = "optimized_graph.json"

    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")
    (Path(run_dir) / graph_rel).write_text(json.dumps(optimized_graph, indent=2), encoding="utf-8")

    artifact_relpaths = {
        "invdesign_report_json": report_rel,
        "optimized_graph_json": graph_rel,
    }
    enforce_invdesign_evidence_or_400(
        report=report,
        run_dir=Path(run_dir),
        artifact_relpaths=artifact_relpaths,
        execution_mode=execution_mode,
    )

    report_inputs_raw = report.get("inputs")
    report_inputs = report_inputs_raw if isinstance(report_inputs_raw, dict) else {}
    robustness_raw = report_inputs.get("robustness")
    robustness = robustness_raw if isinstance(robustness_raw, dict) else {}
    best_raw = report.get("best")
    best = best_raw if isinstance(best_raw, dict) else {}
    best_eval_raw = best.get("robustness_eval")
    best_eval = best_eval_raw if isinstance(best_eval_raw, dict) else {}
    best_metrics_raw = best_eval.get("metrics")
    best_metrics = best_metrics_raw if isinstance(best_metrics_raw, dict) else {}
    threshold_eval_raw = best_eval.get("threshold_eval")
    threshold_eval = threshold_eval_raw if isinstance(threshold_eval_raw, dict) else {}
    execution_raw = report.get("execution")
    execution = execution_raw if isinstance(execution_raw, dict) else {}
    solver_raw = execution.get("solver")
    solver = solver_raw if isinstance(solver_raw, dict) else {}

    outputs_summary = {
        "invdesign": {
            "kind": invdesign_kind,
            "design_node_id": design_node_id,
            "design_param": design_param,
            "best_value": float(best_value),
            "achieved_fraction_nominal_mean": float(achieved_fraction),
            "objective": float(objective),
            "wavelength_objective_agg": str(robustness.get("wavelength_objective_agg") or ""),
            "case_objective_agg": str(robustness.get("case_objective_agg") or ""),
            "objective_case_max": best_metrics.get("objective_case_max"),
            "worst_case_achieved_fraction": best_metrics.get("worst_case_achieved_fraction"),
            "threshold_pass": threshold_eval.get("pass"),
            "solver_backend_requested": solver.get("backend_requested"),
            "solver_backend_used": solver.get("backend_used"),
        }
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "invdesign",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "kind": invdesign_kind,
            "execution_mode": execution_mode,
        },
        "outputs_summary": outputs_summary,
        "artifacts": artifact_relpaths,
        "provenance": provenance,
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "graph_hash": hash_dict(graph),
        "optimized_graph": optimized_graph,
        "report": report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": artifact_relpaths,
        "provenance": provenance,
    }


def _run_pic_invdesign(
    *,
    payload: dict[str, Any],
    route_name: str,
    invdesign_kind: str,
    design_node_field: str,
    design_node_kind: str,
    missing_node_detail: str,
    target_fraction_default: float,
    steps_default: int,
    design_param: str,
    best_attr: str,
    solver: Callable[..., Any],
) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)
    execution_mode = parse_execution_mode(payload)

    netlist = _compile_pic_netlist_or_400(graph, route_name=route_name)
    design_node_id = str(payload.get(design_node_field, "")).strip() or _first_node_id_by_kind(
        netlist,
        node_kind=design_node_kind,
    )
    if not design_node_id:
        raise HTTPException(status_code=400, detail=missing_node_detail)

    invdesign_kwargs = _invdesign_common_options(
        payload,
        execution_mode=execution_mode,
        netlist=netlist,
        target_fraction_default=target_fraction_default,
        steps_default=steps_default,
    )
    invdesign_kwargs[design_node_field] = design_node_id

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        result = solver(netlist, **invdesign_kwargs)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="inverse design run failed") from exc

    best_value = float(getattr(result, best_attr))
    optimized_graph = _optimized_graph_with_updated_param(
        graph,
        node_id=design_node_id,
        param_name=design_param,
        param_value=best_value,
    )
    return _persist_invdesign_run(
        run_id=run_id,
        run_dir=run_dir,
        graph=graph,
        project_id=project_id,
        execution_mode=execution_mode,
        invdesign_kind=invdesign_kind,
        design_node_id=design_node_id,
        design_param=design_param,
        best_value=best_value,
        achieved_fraction=float(result.achieved_fraction),
        objective=float(result.objective),
        report=result.report,
        optimized_graph=optimized_graph,
    )


@router.post("/v0/pic/simulate")
def pic_simulate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    wavelengths_nm = payload.get("wavelength_sweep_nm") if isinstance(payload, dict) else None
    wavelength_nm = payload.get("wavelength_nm") if isinstance(payload, dict) else None

    netlist = _compile_pic_netlist_or_400(graph, route_name="pic/simulate")

    try:
        if wavelengths_nm:
            wavelengths = [float(x) for x in wavelengths_nm]
            results = simulate_pic_netlist_sweep(netlist, wavelengths_nm=wavelengths)
        else:
            wn = float(wavelength_nm) if wavelength_nm is not None else None
            results = simulate_pic_netlist(netlist, wavelength_nm=wn)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="PIC simulation failed") from exc

    return {
        "generated_at": generated_at_utc(),
        "graph_hash": hash_dict(graph),
        "netlist": netlist,
        "results": results,
    }


@router.post("/v0/pic/spice/export")
def pic_spice_export(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)

    require_schema = bool(payload.get("require_schema", False))
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else None

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        report = export_pic_graph_to_spice_artifacts(
            {"graph": graph, "settings": settings},
            run_dir,
            require_schema=require_schema,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="PIC SPICE export failed") from exc

    generated_at = generated_at_utc()
    report_rel = "spice_export_report.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")

    artifacts = dict(report.get("artifacts", {}) or {})
    netlist_rel = str(artifacts.get("netlist_path") or "netlist.sp")
    map_rel = str(artifacts.get("spice_map_path") or "spice_map.json")
    prov_rel = str(artifacts.get("spice_provenance_path") or "spice_provenance.json")

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "pic_spice_export",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "settings_hash": hash_dict(settings or {}),
        },
        "outputs_summary": {"pic_spice_export": dict(report.get("summary", {}) or {})},
        "artifacts": {
            "spice_export_report_json": report_rel,
            "netlist_sp": netlist_rel,
            "spice_map_json": map_rel,
            "spice_provenance_json": prov_rel,
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
            "spice_export_report_json": report_rel,
            "netlist_sp": netlist_rel,
            "spice_map_json": map_rel,
            "spice_provenance_json": prov_rel,
        },
        "provenance": runtime_provenance(),
    }


@router.post("/v0/pic/invdesign/mzi_phase")
def pic_invdesign_mzi_phase(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Inverse-design an MZI-like PIC graph by tuning one phase shifter."""

    return _run_pic_invdesign(
        payload=payload,
        route_name="pic/invdesign/mzi_phase",
        invdesign_kind="pic.invdesign.mzi_phase",
        design_node_field="phase_node_id",
        design_node_kind="pic.phase_shifter",
        missing_node_detail="No pic.phase_shifter nodes found to optimize",
        target_fraction_default=0.9,
        steps_default=181,
        design_param="phase_rad",
        best_attr="best_phase_rad",
        solver=inverse_design_mzi_phase,
    )


@router.post("/v0/pic/invdesign/coupler_ratio")
def pic_invdesign_coupler_ratio(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """Inverse-design a PIC graph by tuning one coupler coupling ratio."""

    return _run_pic_invdesign(
        payload=payload,
        route_name="pic/invdesign/coupler_ratio",
        invdesign_kind="pic.invdesign.coupler_ratio",
        design_node_field="coupler_node_id",
        design_node_kind="pic.coupler",
        missing_node_detail="No pic.coupler nodes found to optimize",
        target_fraction_default=0.5,
        steps_default=101,
        design_param="coupling_ratio",
        best_attr="best_coupling_ratio",
        solver=inverse_design_coupler_ratio,
    )
