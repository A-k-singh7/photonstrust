"""QKD execution and import routes."""

from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from photonstrust.api import compile_cache as compile_cache_store
from photonstrust.api import jobs as job_store
from photonstrust.api import runs as run_store
from photonstrust.api.common import dict_or_empty
from photonstrust.api.common import graph_from_payload
from photonstrust.api.common import parse_execution_mode
from photonstrust.api.common import project_id_or_400
from photonstrust.api.common import reject_output_root_override
from photonstrust.api.common import run_artifact_relpath
from photonstrust.api.common import safe_read_json_object
from photonstrust.api.http_layer import request_id
from photonstrust.api.models.v1 import V1QkdRunRequest, V1QkdRunResponse
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.api.services.pdk_manifests import coerce_pdk_manifest_payload
from photonstrust.api.services.pdk_manifests import resolve_run_pdk_manifest
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.config import build_scenarios
from photonstrust.events.kernel import Event, EventKernel
from photonstrust.protocols.steps import write_protocol_steps_artifacts
from photonstrust.qkd_protocols.registry import protocol_gate_policy
from photonstrust.report import build_reliability_card_from_external_result, write_reliability_card
from photonstrust.sweep import run_scenarios
from photonstrust.utils import hash_dict
from photonstrust.workflow.schema import event_trace_schema_path
from photonstrust.workflow.schema import external_sim_result_schema_path
from photonstrust.workflow.schema import protocol_steps_schema_path


router = APIRouter()


def _write_qkd_event_trace_artifact(*, scenario: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    trace_mode = str((scenario or {}).get("event_trace_mode") or "full").strip().lower() or "full"
    if trace_mode not in {"off", "summary", "sampled", "full"}:
        trace_mode = "full"
    sample_rate = float((scenario or {}).get("event_trace_sample_rate", 0.25) or 0.25)
    seed = int((scenario or {}).get("seed", 0) or 0)
    kernel = EventKernel(seed=seed, trace_mode=trace_mode, trace_sample_rate=sample_rate)

    distances = list((scenario or {}).get("distances_km") or [])
    if not distances:
        distances = [0.0]

    for idx, distance in enumerate(distances):
        base = float(idx) * 10.0
        kernel.schedule(
            Event(
                time_ns=base + 0.1,
                priority=0,
                event_type="emission",
                node_id="source",
                payload={"distance_km": float(distance)},
            )
        )
        kernel.schedule(
            Event(
                time_ns=base + 0.2,
                priority=0,
                event_type="propagation_arrival",
                node_id="link",
                payload={"distance_km": float(distance)},
            )
        )
        kernel.schedule(
            Event(
                time_ns=base + 0.3,
                priority=0,
                event_type="detection",
                node_id="detector",
                payload={"distance_km": float(distance)},
            )
        )
    kernel.run()

    trace_payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.event_trace",
        "trace_mode": trace_mode,
        "events": kernel.trace_records(),
        "summary": kernel.trace_summary(),
    }
    validate_instance(trace_payload, event_trace_schema_path(), require_jsonschema=False)
    out_path = output_dir / "event_trace.json"
    out_path.write_text(json.dumps(trace_payload, indent=2), encoding="utf-8")
    return {
        "event_trace_json": str(out_path),
        "event_trace": {
            "trace_mode": trace_mode,
            "event_count": int(trace_payload["summary"].get("event_count", 0) or 0),
            "trace_hash": kernel.trace_hash(),
        },
    }


@router.post("/v0/qkd/run")
def qkd_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    graph = graph_from_payload(payload)
    include_cache_stats = bool(payload.get("include_cache_stats", False))
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

    try:
        compiled_payload, compile_cache = compile_cache_store.compile_graph_cached(graph, require_schema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if str(compiled_payload.get("profile", "")) != "qkd_link":
        raise HTTPException(status_code=400, detail="qkd/run expects a graph with profile=qkd_link")

    compiled_config_raw = compiled_payload.get("compiled")
    cfg = dict_or_empty(compiled_config_raw)
    scenario = dict_or_empty(cfg.get("scenario"))
    scenario["execution_mode"] = execution_mode
    cfg["scenario"] = scenario

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    try:
        scenarios = build_scenarios(cfg)
        result = run_scenarios(scenarios, run_dir, run_id=run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scenario_primary: dict[str, Any] = (
        scenarios[0] if isinstance(scenarios, list) and scenarios and isinstance(scenarios[0], dict) else {}
    )

    protocol_selected_hint = None
    cards_hint = result.get("cards") if isinstance(result, dict) else []
    if isinstance(cards_hint, list) and cards_hint and isinstance(cards_hint[0], dict):
        model_prov = cards_hint[0].get("model_provenance") if isinstance(cards_hint[0].get("model_provenance"), dict) else {}
        protocol_selected_hint = model_prov.get("protocol_normalized")

    protocol_step_meta = write_protocol_steps_artifacts(
        scenario=scenario_primary,
        output_dir=run_dir,
        protocol_selected=str(protocol_selected_hint or ""),
        include_qasm=bool(payload.get("include_qasm", True)),
    )
    steps_payload = safe_read_json_object(Path(protocol_step_meta.get("protocol_steps_json", ""))) or {}
    if steps_payload:
        validate_instance(steps_payload, protocol_steps_schema_path(), require_jsonschema=False)

    event_trace_meta = _write_qkd_event_trace_artifact(
        scenario=scenario_primary,
        output_dir=run_dir,
    )

    generated_at = generated_at_utc()
    cards = result.get("cards", []) if isinstance(result, dict) else []
    artifacts: dict[str, Any] = {"run_registry_json": "run_registry.json"}
    multifidelity_report_path = str((result or {}).get("multifidelity_report_path", "")).strip()
    if multifidelity_report_path:
        try:
            mf_rel = str(Path(multifidelity_report_path).resolve().relative_to(run_dir.resolve())).replace("\\", "/")
        except Exception:
            mf_rel = None
        if mf_rel:
            artifacts["multifidelity_report_json"] = mf_rel

    steps_rel = run_artifact_relpath(run_dir, protocol_step_meta.get("protocol_steps_json", ""))
    if steps_rel:
        artifacts["protocol_steps_json"] = steps_rel

    protocol_steps_raw = protocol_step_meta.get("protocol_steps")
    protocol_steps = protocol_steps_raw if isinstance(protocol_steps_raw, dict) else {}
    qasm_artifacts = protocol_steps.get("qasm_artifacts") if isinstance(protocol_steps.get("qasm_artifacts"), dict) else {}
    if isinstance(qasm_artifacts, dict):
        for key, abs_path in qasm_artifacts.items():
            rel = run_artifact_relpath(run_dir, abs_path)
            if rel:
                artifacts[str(key)] = rel

    event_trace_rel = run_artifact_relpath(run_dir, event_trace_meta.get("event_trace_json", ""))
    if event_trace_rel:
        artifacts["event_trace_json"] = event_trace_rel

    if isinstance(cards, list) and cards:
        cards_manifest = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            scenario_id = str(card.get("scenario_id", "")).strip()
            band = str(card.get("band", "")).strip()
            card_artifacts_raw = card.get("artifacts", {}) or {}
            if not isinstance(card_artifacts_raw, dict):
                card_artifacts_raw = {}

            card_artifacts: dict[str, Any] = {}
            if scenario_id and band:
                card_artifacts["results_json"] = f"{scenario_id}/{band}/results.json"
                if artifacts.get("multifidelity_report_json"):
                    card_artifacts["multifidelity_report_json"] = str(artifacts["multifidelity_report_json"])

            for key in ("report_html_path", "report_pdf_path", "card_path"):
                path = card_artifacts_raw.get(key)
                if not path:
                    continue
                try:
                    rel = str(Path(str(path)).resolve().relative_to(run_dir.resolve())).replace("\\", "/")
                except Exception:
                    rel = None
                if rel:
                    card_artifacts[key.replace("_path", "")] = rel

            plots = card_artifacts_raw.get("plots", {}) or {}
            if isinstance(plots, dict) and plots.get("key_rate_vs_distance_path"):
                try:
                    rel = str(Path(str(plots["key_rate_vs_distance_path"])).resolve().relative_to(run_dir.resolve())).replace(
                        "\\", "/"
                    )
                except Exception:
                    rel = None
                if rel:
                    card_artifacts["key_rate_vs_distance_png"] = rel

            cards_manifest.append(
                {
                    "scenario_id": scenario_id,
                    "band": band,
                    "artifacts": card_artifacts,
                }
            )
        if cards_manifest:
            artifacts["cards"] = cards_manifest

    outputs_summary: dict[str, Any] = {
        "qkd": {
            "cards": [],
            "multifidelity": {
                "present": bool("multifidelity_report_json" in artifacts),
                "artifact": artifacts.get("multifidelity_report_json"),
            },
            "protocol_selected": None,
            "protocol_steps": dict(protocol_steps),
            "event_trace": dict(event_trace_meta.get("event_trace", {})),
        }
    }
    if isinstance(cards, list) and cards:
        summary_cards = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            outs = card.get("outputs", {}) or {}
            derived = card.get("derived", {}) or {}
            safe = card.get("safe_use_label", {}) or {}
            ci = card.get("confidence_intervals", {}) or {}
            fk_ledger = card.get("finite_key_epsilon_ledger", {}) or {}
            model_prov = card.get("model_provenance", {}) or {}
            sec_assumptions = card.get("security_assumptions_metadata", {}) or {}
            if not isinstance(outs, dict):
                outs = {}
            if not isinstance(derived, dict):
                derived = {}
            if not isinstance(safe, dict):
                safe = {}
            if not isinstance(ci, dict):
                ci = {}
            if not isinstance(fk_ledger, dict):
                fk_ledger = {}
            if not isinstance(model_prov, dict):
                model_prov = {}
            if not isinstance(sec_assumptions, dict):
                sec_assumptions = {}
            gate_policy = protocol_gate_policy(model_prov.get("protocol_normalized"))
            summary_cards.append(
                {
                    "scenario_id": str(card.get("scenario_id", "")).strip(),
                    "band": str(card.get("band", "")).strip(),
                    "key_rate_bps": outs.get("key_rate_bps"),
                    "qber": derived.get("qber_total"),
                    "safe_use": safe.get("label"),
                    "confidence_intervals": {
                        "key_rate_bps": (ci.get("key_rate_bps") if isinstance(ci.get("key_rate_bps"), dict) else None),
                    },
                    "finite_key_epsilon_ledger": {
                        "enabled": fk_ledger.get("enabled"),
                        "epsilon_total": fk_ledger.get("epsilon_total"),
                    },
                    "security_assumptions_metadata": {
                        "security_model": sec_assumptions.get("security_model"),
                        "trusted_device_model": sec_assumptions.get("trusted_device_model"),
                        "assume_iid": sec_assumptions.get("assume_iid"),
                    },
                    "model_provenance": {
                        "protocol_family": model_prov.get("protocol_family"),
                        "protocol_normalized": model_prov.get("protocol_normalized"),
                        "channel_model": model_prov.get("channel_model"),
                        "finite_key_model": model_prov.get("finite_key_model"),
                    },
                    "bound_gate_policy": {
                        "plob_repeaterless_bound": gate_policy.get("plob_repeaterless_bound"),
                        "rationale": gate_policy.get("rationale"),
                    },
                }
            )
        outputs_summary["qkd"]["cards"] = summary_cards
        if summary_cards:
            first_protocol = ((summary_cards[0].get("model_provenance") or {}).get("protocol_normalized"))
            outputs_summary["qkd"]["protocol_selected"] = first_protocol

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "qkd_run",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_id": graph.get("graph_id"),
            "graph_hash": hash_dict(graph),
            "compiled_config_hash": hash_dict(cfg),
            "execution_mode": execution_mode,
            "protocol_selected": ((outputs_summary.get("qkd") or {}).get("protocol_selected")),
            "source_job_id": str((payload or {}).get("source_job_id", "")).strip() or None,
            "compile_cache_key": compile_cache.get("key"),
        },
        "outputs_summary": outputs_summary,
        "artifacts": artifacts,
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    compile_cache_payload: dict[str, Any] = {"key": compile_cache.get("key")}
    if include_cache_stats:
        compile_cache_payload["hit"] = bool(compile_cache.get("hit", False))

    return {
        "run_id": run_id,
        "output_dir": str(run_dir),
        "graph_hash": hash_dict(graph),
        "compiled_config": cfg,
        "compile_cache": compile_cache_payload,
        "results": result,
        "artifact_relpaths": artifacts,
        "manifest_path": str(manifest_path),
    }


@router.post("/v1/qkd/run", response_model=V1QkdRunResponse)
def v1_qkd_run(request: Request, payload: V1QkdRunRequest) -> V1QkdRunResponse:
    run_payload = qkd_run(payload.model_dump(exclude_none=True))
    return V1QkdRunResponse.model_validate(
        {
            **run_payload,
            "request_id": request_id(request),
        }
    )


def _qkd_async_worker(job_id: str, payload: dict[str, Any]) -> None:
    try:
        job_store.set_status(job_id, "running")

        request_payload = dict(payload) if isinstance(payload, dict) else {}
        graph = request_payload.get("graph") if isinstance(request_payload.get("graph"), dict) else None
        if not isinstance(graph, dict):
            graph = request_payload
            request_payload = {"graph": graph}

        request_payload["source_job_id"] = str(job_id)
        run_payload = qkd_run(request_payload)
        if not isinstance(run_payload, dict):
            raise RuntimeError("qkd_run returned invalid payload")

        result_payload: dict[str, Any] = {
            "run_id": run_payload.get("run_id"),
            "output_dir": run_payload.get("output_dir"),
            "manifest_path": run_payload.get("manifest_path"),
            "artifact_relpaths": run_payload.get("artifact_relpaths")
            if isinstance(run_payload.get("artifact_relpaths"), dict)
            else {},
            "graph_hash": run_payload.get("graph_hash"),
            "compile_cache": run_payload.get("compile_cache") if isinstance(run_payload.get("compile_cache"), dict) else {},
        }
        job_store.set_result(job_id, result_payload)
    except HTTPException as exc:
        error_payload: dict[str, Any] = {
            "status_code": int(exc.status_code),
            "detail": str(exc.detail),
            "type": "HTTPException",
        }
        job_store.set_error(job_id, error_payload)
    except Exception as exc:
        error_payload = {
            "status_code": 500,
            "detail": str(exc),
            "type": str(type(exc).__name__),
        }
        job_store.set_error(job_id, error_payload)


@router.post("/v0/qkd/run/async")
def qkd_run_async(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for qkd async payload")

    graph = graph_from_payload(payload)
    project_id = project_id_or_400(payload)
    queued = job_store.create_job(
        job_type="qkd_run",
        payload=payload,
        project_id=project_id,
        input_hash=hash_dict(graph),
    )
    job_id = str(queued.get("job_id"))

    worker = threading.Thread(target=_qkd_async_worker, args=(job_id, dict(payload)), daemon=True)
    worker.start()

    return {
        "job_id": job_id,
        "status": "queued",
        "job_manifest_path": str(job_store.job_dir_for_id(job_id) / "job_manifest.json"),
        "status_endpoint": f"/v0/jobs/{job_id}/status",
        "job_endpoint": f"/v0/jobs/{job_id}",
    }


@router.post("/v0/qkd/import_external")
def qkd_import_external(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    ext = payload.get("external_result") if isinstance(payload.get("external_result"), dict) else payload
    if not isinstance(ext, dict):
        raise HTTPException(status_code=400, detail="external_result object is required")

    try:
        validate_instance(ext, external_sim_result_schema_path(), require_jsonschema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    project_id = project_id_or_400(payload)

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    ext_path = run_dir / "external_sim_result.json"
    ext_path.write_text(json.dumps(ext, indent=2), encoding="utf-8")

    card = build_reliability_card_from_external_result(ext)
    card_path = run_dir / "reliability_card.json"
    write_reliability_card(card, card_path)

    model_raw = card.get("model_provenance")
    model = model_raw if isinstance(model_raw, dict) else {}
    protocol_selected = model.get("protocol_normalized")
    outputs_raw = card.get("outputs")
    outputs = outputs_raw if isinstance(outputs_raw, dict) else {}
    derived_raw = card.get("derived")
    derived = derived_raw if isinstance(derived_raw, dict) else {}
    outputs_summary = {
        "qkd_external_import": {
            "source": "external_import",
            "simulator_name": ext.get("simulator_name"),
            "simulator_version": ext.get("simulator_version"),
            "protocol_selected": protocol_selected,
            "key_rate_bps": outputs.get("key_rate_bps"),
            "qber_total": derived.get("qber_total"),
            "fidelity_est": outputs.get("fidelity_est"),
        }
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "qkd_external_import",
        "generated_at": generated_at_utc(),
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "source": "external_import",
            "simulator_name": ext.get("simulator_name"),
            "simulator_version": ext.get("simulator_version"),
            "external_result_hash": hash_dict(ext),
            "protocol_selected": protocol_selected,
        },
        "outputs_summary": outputs_summary,
        "artifacts": {
            "external_sim_result_json": "external_sim_result.json",
            "reliability_card_json": "reliability_card.json",
        },
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "run_id": run_id,
        "output_dir": str(run_dir),
        "manifest_path": str(manifest_path),
        "external_result_hash": hash_dict(ext),
        "card_path": str(card_path),
    }
