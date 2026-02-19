"""FastAPI server for PhotonTrust MVP web workflows.

This is a local-development surface intended to keep the web UI thin:
- UI sends graph JSON.
- Backend validates/compiles and executes using the Python engine.
"""

from __future__ import annotations

import json
import hashlib
import importlib.metadata as importlib_metadata
import os
import platform
import re
import shutil
import sys
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from photonstrust.api import compile_cache as compile_cache_store
from photonstrust.api import jobs as job_store
from photonstrust.api import projects as project_store
from photonstrust.api import runs as run_store
from photonstrust.api import ui_metrics as ui_metrics_store
from photonstrust.api.diff import diff_json, diff_violations
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.evidence.bundle import verify_bundle_zip
from photonstrust.events.kernel import Event, EventKernel
from photonstrust.graph.compiler import compile_graph
from photonstrust.graph.diagnostics import validate_graph_semantics
from photonstrust.graph.schema import validate_graph
from photonstrust.invdesign.schema import invdesign_report_schema_path
from photonstrust.orbit.diagnostics import validate_orbit_pass_semantics
from photonstrust.orbit.pass_envelope import run_orbit_pass_from_config
from photonstrust.orbit.schema import validate_orbit_pass_config
from photonstrust.pic import simulate_pic_netlist, simulate_pic_netlist_sweep
from photonstrust.sweep import run_scenarios
from photonstrust.config import build_scenarios
from photonstrust.invdesign import inverse_design_coupler_ratio, inverse_design_mzi_phase
from photonstrust.layout.pic.build_layout import build_pic_layout_artifacts
from photonstrust.layout.pic.foundry_drc_sealed import run_foundry_drc_sealed
from photonstrust.layout.pic.klayout_artifact_pack import build_klayout_run_artifact_pack
from photonstrust.pdk import resolve_pdk_contract
from photonstrust.registry.kinds import build_kinds_registry
from photonstrust.qkd_protocols.registry import protocol_gate_policy
from photonstrust.protocols.steps import write_protocol_steps_artifacts
from photonstrust.report import build_reliability_card_from_external_result, write_reliability_card
from photonstrust.spice.export import export_pic_graph_to_spice_artifacts
from photonstrust.verification.performance_drc import run_parallel_waveguide_crosstalk_check
from photonstrust.verification.lvs_lite import run_pic_lvs_lite
from photonstrust.utils import hash_dict
from photonstrust.workflow.schema import (
    event_trace_schema_path,
    evidence_bundle_publish_manifest_schema_path,
    external_sim_result_schema_path,
    protocol_steps_schema_path,
)


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("photonstrust")
    except PackageNotFoundError:
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except (OSError, UnicodeError):
            return None
    return None


def _cors_allow_origins() -> list[str]:
    """Return allowed CORS origins.

    Configure with `PHOTONTRUST_API_CORS_ALLOW_ORIGINS` as a comma-separated list.
    Defaults are local-development origins only.
    """

    raw = str(os.environ.get("PHOTONTRUST_API_CORS_ALLOW_ORIGINS", "")).strip()
    if raw:
        origins = [item.strip() for item in raw.split(",") if item.strip()]
        if origins:
            return origins

    return [
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ]


app = FastAPI(title="PhotonTrust API", version=_photonstrust_version() or "0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _violation_rows_or_none(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out = [item for item in value if isinstance(item, dict)]
    if out:
        return out
    return [] if not value else None


def _extract_violation_rows(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, dict):
        return None

    for key in ("violations_annotated", "violations"):
        rows = _violation_rows_or_none(value.get(key))
        if rows is not None:
            return rows

    for child in value.values():
        if isinstance(child, dict):
            rows = _extract_violation_rows(child)
            if rows is not None:
                return rows
    return None


_EXECUTION_MODES = {"preview", "certification"}
_AUTH_MODES = {"off", "header"}
_ROLE_SET = {"viewer", "runner", "approver", "admin"}
_UI_TELEMETRY_EVENT_NAMES = {
    "ui_session_started",
    "ui_guided_flow_started",
    "ui_guided_flow_completed",
    "ui_run_started",
    "ui_run_succeeded",
    "ui_run_failed",
    "ui_error_recovered",
    "ui_compare_completed",
    "ui_packet_exported",
    "ui_demo_mode_completed",
}
_UI_TELEMETRY_USER_MODES = {"builder", "reviewer", "exec"}
_UI_TELEMETRY_PROFILES = {"qkd_link", "pic_circuit", "orbit"}
_UI_TELEMETRY_OUTCOMES = {"success", "failure", "abandoned"}
_UI_TELEMETRY_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


def _parse_execution_mode(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return "preview"
    mode = str(payload.get("execution_mode", "preview") or "preview").strip().lower() or "preview"
    if mode not in _EXECUTION_MODES:
        raise HTTPException(
            status_code=400,
            detail="execution_mode must be 'preview' or 'certification' when provided",
        )
    return mode


def _auth_mode() -> str:
    mode = str(os.environ.get("PHOTONTRUST_API_AUTH_MODE", "off") or "off").strip().lower() or "off"
    if mode not in _AUTH_MODES:
        return "off"
    return mode


def _auth_context(request: Request) -> dict[str, Any]:
    mode = _auth_mode()
    if mode == "off":
        return {
            "mode": "off",
            "actor": "anonymous",
            "roles": set(_ROLE_SET),
            "projects": {"*"},
        }

    expected_token = str(os.environ.get("PHOTONTRUST_API_DEV_TOKEN", "") or "").strip()
    if expected_token:
        got_token = str(request.headers.get("x-photonstrust-dev-token", "") or "").strip()
        if got_token != expected_token:
            raise HTTPException(status_code=401, detail="invalid or missing dev token")

    actor = str(request.headers.get("x-photonstrust-actor", "") or "").strip()
    if not actor:
        raise HTTPException(status_code=401, detail="missing x-photonstrust-actor header")

    raw_roles = str(request.headers.get("x-photonstrust-roles", "") or "").strip()
    roles = {item.strip().lower() for item in raw_roles.split(",") if item.strip()}
    if not roles:
        raise HTTPException(status_code=401, detail="missing x-photonstrust-roles header")
    if not roles.intersection(_ROLE_SET):
        raise HTTPException(status_code=401, detail="no supported roles in x-photonstrust-roles")

    raw_projects = str(request.headers.get("x-photonstrust-projects", "") or "").strip()
    projects = {item.strip().lower() for item in raw_projects.split(",") if item.strip()}
    if not projects:
        projects = {"*"}

    return {
        "mode": mode,
        "actor": actor,
        "roles": roles,
        "projects": projects,
    }


def _require_roles(request: Request, *required_roles: str) -> dict[str, Any]:
    ctx = _auth_context(request)
    if "admin" in ctx["roles"]:
        return ctx

    required = {str(role).strip().lower() for role in required_roles if str(role).strip()}
    if not required:
        return ctx
    if not ctx["roles"].intersection(required):
        raise HTTPException(status_code=403, detail="insufficient role for endpoint")
    return ctx


def _enforce_project_scope_or_403(ctx: dict[str, Any], project_id: str | None) -> None:
    pid = str(project_id or "default").strip().lower() or "default"
    projects = ctx.get("projects") if isinstance(ctx.get("projects"), set) else {"*"}
    if "*" in projects:
        return
    if pid not in projects:
        raise HTTPException(status_code=403, detail="project scope denied")


def _run_project_id_from_manifest(manifest: dict[str, Any] | None) -> str:
    m = manifest if isinstance(manifest, dict) else {}
    return str(((m.get("input") if isinstance(m.get("input"), dict) else {}) or {}).get("project_id") or "default").strip().lower() or "default"


def _normalize_utc_timestamp(value: Any, *, field_name: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return datetime.now(timezone.utc).isoformat()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{field_name} must be ISO-8601 timestamp") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.isoformat()


def _safe_read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _to_run_relpath(run_dir: Path, artifact_path: str | Path) -> str | None:
    try:
        return str(Path(str(artifact_path)).resolve().relative_to(run_dir.resolve())).replace("\\", "/")
    except Exception:
        return None


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


def _extract_interop_view(manifest: dict[str, Any]) -> dict[str, Any]:
    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    qkd = outputs.get("qkd") if isinstance(outputs.get("qkd"), dict) else None
    if isinstance(qkd, dict):
        cards = qkd.get("cards") if isinstance(qkd.get("cards"), list) else []
        first = cards[0] if cards and isinstance(cards[0], dict) else {}
        return {
            "source": "native",
            "protocol_selected": qkd.get("protocol_selected"),
            "key_rate_bps": first.get("key_rate_bps"),
            "qber": first.get("qber"),
        }

    ext = outputs.get("qkd_external_import") if isinstance(outputs.get("qkd_external_import"), dict) else None
    if isinstance(ext, dict):
        return {
            "source": "external_import",
            "protocol_selected": ext.get("protocol_selected"),
            "key_rate_bps": ext.get("key_rate_bps"),
            "qber": ext.get("qber_total"),
        }
    return {}


def _interop_diff(lhs_manifest: dict[str, Any], rhs_manifest: dict[str, Any]) -> dict[str, Any] | None:
    lhs = _extract_interop_view(lhs_manifest)
    rhs = _extract_interop_view(rhs_manifest)
    if not lhs or not rhs:
        return None

    key_rate_delta = None
    qber_delta = None
    try:
        key_rate_delta = float(rhs.get("key_rate_bps")) - float(lhs.get("key_rate_bps"))
    except Exception:
        key_rate_delta = None
    try:
        qber_delta = float(rhs.get("qber")) - float(lhs.get("qber"))
    except Exception:
        qber_delta = None

    return {
        "lhs_source": lhs.get("source"),
        "rhs_source": rhs.get("source"),
        "lhs_protocol_selected": lhs.get("protocol_selected"),
        "rhs_protocol_selected": rhs.get("protocol_selected"),
        "key_rate_bps_delta": key_rate_delta,
        "qber_delta": qber_delta,
    }


def _extract_pdk_request_from_manifest(manifest: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(manifest, dict):
        return None
    input_obj = manifest.get("input") if isinstance(manifest.get("input"), dict) else {}
    raw_pdk = input_obj.get("pdk")

    if isinstance(raw_pdk, str) and raw_pdk.strip():
        return {"name": raw_pdk.strip()}

    if isinstance(raw_pdk, dict):
        out: dict[str, Any] = {}
        name = raw_pdk.get("name")
        if isinstance(name, str) and name.strip():
            out["name"] = name.strip()
        manifest_path = raw_pdk.get("manifest_path")
        if isinstance(manifest_path, str) and manifest_path.strip():
            out["manifest_path"] = manifest_path.strip()
        if out:
            return out

    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    pic_layout = outputs.get("pic_layout") if isinstance(outputs.get("pic_layout"), dict) else {}
    pdk_name = pic_layout.get("pdk")
    if isinstance(pdk_name, str) and pdk_name.strip():
        return {"name": pdk_name.strip()}

    return None


def _build_pdk_manifest_payload(
    pdk_request: dict[str, Any] | None,
    *,
    execution_mode: str,
    source_run_id: str | None = None,
) -> dict[str, Any]:
    contract = resolve_pdk_contract(pdk_request if isinstance(pdk_request, dict) else {})

    source_id = None
    if isinstance(source_run_id, str) and source_run_id.strip():
        try:
            source_id = run_store.validate_run_id(source_run_id)
        except Exception:
            source_id = None

    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pdk_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": execution_mode,
        "source_run_id": source_id,
        "adapter": str(contract.get("adapter", "registry.v0") or "registry.v0"),
        "request": {
            "name": (contract.get("request") or {}).get("name"),
            "manifest_path": (contract.get("request") or {}).get("manifest_path"),
        },
        "pdk": {
            "name": (contract.get("pdk") or {}).get("name"),
            "version": (contract.get("pdk") or {}).get("version"),
            "design_rules": dict(((contract.get("pdk") or {}).get("design_rules") or {})),
            "notes": list(((contract.get("pdk") or {}).get("notes") or [])),
        },
        "capabilities": {
            "supports_layout": bool(((contract.get("capabilities") or {}).get("supports_layout", True))),
            "supports_performance_drc": bool(
                ((contract.get("capabilities") or {}).get("supports_performance_drc", True))
            ),
            "supports_lvs_lite_signoff": bool(
                ((contract.get("capabilities") or {}).get("supports_lvs_lite_signoff", True))
            ),
            "supports_spice_export": bool(((contract.get("capabilities") or {}).get("supports_spice_export", True))),
        },
    }


def _coerce_pdk_manifest_payload(
    payload: dict[str, Any] | None,
    *,
    execution_mode: str,
    source_run_id: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    out = dict(payload)

    request = out.get("request") if isinstance(out.get("request"), dict) else {}
    req_name = request.get("name")
    req_manifest = request.get("manifest_path")
    out["request"] = {
        "name": str(req_name).strip() if isinstance(req_name, str) and req_name.strip() else None,
        "manifest_path": str(req_manifest).strip() if isinstance(req_manifest, str) and req_manifest.strip() else None,
    }

    pdk = out.get("pdk") if isinstance(out.get("pdk"), dict) else None
    if not isinstance(pdk, dict) or not str(pdk.get("name", "")).strip():
        try:
            return _build_pdk_manifest_payload(out.get("request"), execution_mode=execution_mode, source_run_id=source_run_id)
        except Exception:
            return None

    out["pdk"] = {
        "name": str(pdk.get("name", "")).strip(),
        "version": str(pdk.get("version", "0")).strip() or "0",
        "design_rules": dict(pdk.get("design_rules") if isinstance(pdk.get("design_rules"), dict) else {}),
        "notes": [str(n) for n in (pdk.get("notes") if isinstance(pdk.get("notes"), list) else [])],
    }

    caps = out.get("capabilities") if isinstance(out.get("capabilities"), dict) else {}
    out["capabilities"] = {
        "supports_layout": bool(caps.get("supports_layout", True)),
        "supports_performance_drc": bool(caps.get("supports_performance_drc", True)),
        "supports_lvs_lite_signoff": bool(caps.get("supports_lvs_lite_signoff", True)),
        "supports_spice_export": bool(caps.get("supports_spice_export", True)),
    }

    src = None
    if isinstance(source_run_id, str) and source_run_id.strip():
        try:
            src = run_store.validate_run_id(source_run_id)
        except Exception:
            src = None
    elif isinstance(out.get("source_run_id"), str) and str(out.get("source_run_id") or "").strip():
        try:
            src = run_store.validate_run_id(str(out.get("source_run_id")))
        except Exception:
            src = None

    out["schema_version"] = "0.1"
    out["kind"] = "photonstrust.pdk_manifest"
    out["generated_at"] = (
        str(out.get("generated_at")).strip() if isinstance(out.get("generated_at"), str) and str(out.get("generated_at")).strip() else datetime.now(timezone.utc).isoformat()
    )
    out["execution_mode"] = execution_mode
    out["source_run_id"] = src
    out["adapter"] = str(out.get("adapter", "registry.v0") or "registry.v0").strip() or "registry.v0"
    return out


def _load_pdk_manifest_from_run(run_dir: Path) -> dict[str, Any] | None:
    m = run_store.read_run_manifest(run_dir)
    if not isinstance(m, dict):
        return None

    arts = m.get("artifacts") if isinstance(m.get("artifacts"), dict) else {}
    rel = arts.get("pdk_manifest_json")
    if isinstance(rel, str) and rel.strip():
        try:
            p = run_store.resolve_artifact_path(run_dir, str(rel).strip())
        except Exception:
            p = None
        if isinstance(p, Path):
            data = _safe_read_json_object(p)
            if isinstance(data, dict):
                return data

    req = _extract_pdk_request_from_manifest(m)
    if isinstance(req, dict):
        return _build_pdk_manifest_payload(
            req,
            execution_mode="preview",
            source_run_id=str(m.get("run_id", "")).strip() or None,
        )
    return None


def _resolve_run_pdk_manifest(
    *,
    pdk_request: dict[str, Any] | None,
    execution_mode: str,
    source_run_dir: Path | None = None,
    source_run_id: str | None = None,
    require_context_in_cert: bool,
) -> dict[str, Any] | None:
    payload = None
    if isinstance(source_run_dir, Path):
        payload = _load_pdk_manifest_from_run(source_run_dir)

    if payload is None and isinstance(pdk_request, dict):
        payload = _build_pdk_manifest_payload(
            pdk_request,
            execution_mode=execution_mode,
            source_run_id=source_run_id,
        )

    if payload is None:
        if execution_mode == "certification" and require_context_in_cert:
            return None
        payload = _build_pdk_manifest_payload({}, execution_mode=execution_mode, source_run_id=source_run_id)

    return _coerce_pdk_manifest_payload(payload, execution_mode=execution_mode, source_run_id=source_run_id)


def _write_pdk_manifest_artifact(run_dir: Path, payload: dict[str, Any]) -> str:
    rel = "pdk_manifest.json"
    (Path(run_dir) / rel).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return rel


_INVDESIGN_REQUIRED_ARTIFACT_KEYS = ("invdesign_report_json", "optimized_graph_json")


def _validate_invdesign_report_schema_or_400(report: dict[str, Any], *, require_jsonschema: bool) -> None:
    try:
        validate_instance(report, invdesign_report_schema_path(), require_jsonschema=require_jsonschema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invdesign evidence schema validation failed: {exc}") from exc


def _invdesign_certification_evidence_issues(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    inputs = report.get("inputs") if isinstance(report.get("inputs"), dict) else {}
    robustness = inputs.get("robustness") if isinstance(inputs.get("robustness"), dict) else {}
    cases = robustness.get("cases") if isinstance(robustness.get("cases"), list) else []
    if not bool(robustness.get("required", False)):
        issues.append("inputs.robustness.required must be true in certification mode")
    if len(cases) < 2:
        issues.append("inputs.robustness.cases must include at least two cases in certification mode")

    best = report.get("best") if isinstance(report.get("best"), dict) else {}
    robustness_eval = best.get("robustness_eval") if isinstance(best.get("robustness_eval"), dict) else {}
    if not isinstance(robustness_eval.get("worst_case"), dict):
        issues.append("best.robustness_eval.worst_case is required in certification mode")
    threshold_eval = robustness_eval.get("threshold_eval") if isinstance(robustness_eval.get("threshold_eval"), dict) else None
    if not isinstance(threshold_eval, dict):
        issues.append("best.robustness_eval.threshold_eval is required in certification mode")
    elif not isinstance(threshold_eval.get("pass"), bool):
        issues.append("best.robustness_eval.threshold_eval.pass must be boolean")

    execution = report.get("execution") if isinstance(report.get("execution"), dict) else {}
    if str(execution.get("mode", "")).strip().lower() != "certification":
        issues.append("execution.mode must be 'certification' in certification runs")
    solver = execution.get("solver") if isinstance(execution.get("solver"), dict) else {}
    if not str(solver.get("backend_requested", "")).strip():
        issues.append("execution.solver.backend_requested is required")
    if not str(solver.get("backend_used", "")).strip():
        issues.append("execution.solver.backend_used is required")

    return issues


def _enforce_invdesign_evidence_or_400(
    *,
    report: dict[str, Any],
    run_dir: Path,
    artifact_relpaths: dict[str, Any],
    execution_mode: str,
) -> None:
    _validate_invdesign_report_schema_or_400(report, require_jsonschema=(execution_mode == "certification"))

    missing_artifacts: list[str] = []
    for key in _INVDESIGN_REQUIRED_ARTIFACT_KEYS:
        rel = artifact_relpaths.get(key)
        if not isinstance(rel, str) or not rel.strip():
            missing_artifacts.append(key)
            continue
        p = Path(run_dir) / rel
        if not p.exists() or not p.is_file():
            missing_artifacts.append(key)
    if missing_artifacts:
        raise HTTPException(
            status_code=400,
            detail=f"invdesign evidence artifacts missing: {', '.join(sorted(missing_artifacts))}",
        )

    if execution_mode == "certification":
        issues = _invdesign_certification_evidence_issues(report)
        if issues:
            raise HTTPException(
                status_code=400,
                detail=f"certification mode requires complete inverse-design evidence: {'; '.join(issues)}",
            )


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "version": app.version}


@app.get("/v0/registry/kinds")
def registry_kinds() -> dict[str, Any]:
    registry = build_kinds_registry()
    return {
        "schema_version": str(registry.get("schema_version", "0.0")),
        "registry_hash": hash_dict(registry),
        "registry": registry,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.get("/v0/runs")
def runs_list(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    project_id: str | None = Query(None, description="Optional project_id filter"),
) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
    pid = None
    if project_id is not None:
        raw = str(project_id or "").strip()
        if raw:
            try:
                pid = project_store.validate_project_id(raw)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            _enforce_project_scope_or_403(ctx, pid)

    runs = run_store.list_runs(limit=int(limit), project_id=pid)
    if "*" not in ctx.get("projects", {"*"}):
        allowed = ctx.get("projects") if isinstance(ctx.get("projects"), set) else set()
        runs = [
            row
            for row in runs
            if isinstance(row, dict) and str(row.get("project_id") or "default").strip().lower() in allowed
        ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_root": str(run_store.runs_root()),
        "project_id": pid,
        "runs": runs,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.get("/v0/jobs")
def jobs_list(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    status: str | None = Query(None, description="Optional status filter: queued|running|succeeded|failed"),
) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
    try:
        jobs = job_store.list_jobs(limit=int(limit), status=status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if "*" not in ctx.get("projects", {"*"}):
        allowed = ctx.get("projects") if isinstance(ctx.get("projects"), set) else set()
        jobs = [
            row
            for row in jobs
            if isinstance(row, dict)
            and str(((row.get("input") if isinstance(row.get("input"), dict) else {}) or {}).get("project_id") or "default").strip().lower() in allowed
        ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "jobs_root": str(job_store.jobs_root()),
        "status": str(status).strip().lower() if isinstance(status, str) and str(status).strip() else None,
        "jobs": jobs,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.get("/v0/jobs/{job_id}")
def jobs_get(job_id: str, request: Request) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
    try:
        manifest = job_store.read_job(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not isinstance(manifest, dict):
        raise HTTPException(status_code=404, detail="job not found")
    project_id = str(((manifest.get("input") if isinstance(manifest.get("input"), dict) else {}) or {}).get("project_id") or "default").strip().lower() or "default"
    _enforce_project_scope_or_403(ctx, project_id)
    return manifest


@app.get("/v0/jobs/{job_id}/status")
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


@app.get("/v0/runs/{run_id}")
def runs_get(run_id: str, request: Request) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
    try:
        run_dir = run_store.run_dir_for_id(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    manifest = run_store.read_run_manifest(run_dir)
    if manifest:
        _enforce_project_scope_or_403(ctx, _run_project_id_from_manifest(manifest))
        return manifest

    # Backwards-compatible fallback for older runs without a manifest.
    _enforce_project_scope_or_403(ctx, "default")
    ts = float(run_dir.stat().st_mtime)
    generated_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
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


@app.get("/v0/runs/{run_id}/artifact")
def runs_artifact(
    run_id: str,
    request: Request,
    path: str = Query(..., description="Relative path within the run directory"),
):
    _ = _require_roles(request, "viewer", "runner", "approver")
    try:
        run_dir = run_store.run_dir_for_id(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not run_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    _ = runs_get(run_id, request)

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


_BUNDLE_FIXED_DT = (1980, 1, 1, 0, 0, 0)
_BUNDLE_CHUNK_BYTES = 1024 * 1024


def _iter_manifest_artifact_relpaths(manifest: dict[str, Any]) -> list[str]:
    out: list[str] = []
    arts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    for _, v in arts.items():
        if isinstance(v, str) and v.strip():
            out.append(str(v).strip())

    # Nested artifact lists (v0.1): QKD cards list.
    cards = arts.get("cards")
    if isinstance(cards, list):
        for c in cards:
            if not isinstance(c, dict):
                continue
            c_arts = c.get("artifacts") if isinstance(c.get("artifacts"), dict) else {}
            for _, v in c_arts.items():
                if isinstance(v, str) and v.strip():
                    out.append(str(v).strip())

    # Unique (case-insensitive) while preserving first-seen order.
    seen: set[str] = set()
    uniq: list[str] = []
    for p in out:
        key = str(p).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        uniq.append(str(p).strip())
    return uniq


def _is_workflow_manifest(manifest: dict[str, Any]) -> bool:
    if str(manifest.get("run_type", "")).strip() == "pic_workflow_invdesign_chain":
        return True
    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    return isinstance(outputs.get("pic_workflow"), dict)


def _workflow_child_run_ids(manifest: dict[str, Any]) -> list[str]:
    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    wf = outputs.get("pic_workflow") if isinstance(outputs.get("pic_workflow"), dict) else {}
    raw = [
        wf.get("invdesign_run_id"),
        wf.get("layout_run_id"),
        wf.get("lvs_lite_run_id"),
        wf.get("klayout_pack_run_id"),
        wf.get("spice_export_run_id"),
    ]
    out: list[str] = []
    seen: set[str] = set()
    for rid in raw:
        if not isinstance(rid, str) or not rid.strip():
            continue
        try:
            canon = run_store.validate_run_id(rid)
        except Exception:
            continue
        if canon in seen:
            continue
        seen.add(canon)
        out.append(canon)
    return out


def _zip_write_bytes(zf: zipfile.ZipFile, arcname: str, data: bytes) -> tuple[str, int]:
    arc = str(arcname).replace("\\", "/")
    info = zipfile.ZipInfo(arc)
    info.date_time = _BUNDLE_FIXED_DT
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)
    return hashlib.sha256(data).hexdigest(), int(len(data))


def _zip_write_file(zf: zipfile.ZipFile, arcname: str, src_path: Path) -> tuple[str, int]:
    arc = str(arcname).replace("\\", "/")
    info = zipfile.ZipInfo(arc)
    info.date_time = _BUNDLE_FIXED_DT
    info.compress_type = zipfile.ZIP_DEFLATED

    sha = hashlib.sha256()
    size = 0
    with Path(src_path).open("rb") as src, zf.open(info, "w") as dest:
        while True:
            chunk = src.read(_BUNDLE_CHUNK_BYTES)
            if not chunk:
                break
            dest.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), int(size)


_BUNDLE_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")


def _published_bundles_root() -> Path:
    root = run_store.runs_root() / "_published_bundles" / "sha256"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _sha256_file(path: Path) -> tuple[str, int]:
    sha = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(_BUNDLE_CHUNK_BYTES)
            if not chunk:
                break
            sha.update(chunk)
            size += len(chunk)
    return sha.hexdigest(), int(size)


def _build_cyclonedx_sbom(*, timestamp: str | None = None) -> dict[str, Any]:
    components: list[dict[str, Any]] = []
    for dist in sorted(importlib_metadata.distributions(), key=lambda d: str((d.metadata or {}).get("Name", "")).lower()):
        name = str((dist.metadata or {}).get("Name") or "").strip()
        if not name:
            continue
        components.append(
            {
                "type": "library",
                "name": name,
                "version": str(dist.version or ""),
            }
        )

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": str(timestamp or datetime.now(timezone.utc).isoformat()),
            "tools": [
                {
                    "vendor": "PhotonTrust",
                    "name": "photonstrust.api.bundle",
                    "version": str(app.version),
                }
            ],
            "component": {
                "type": "application",
                "name": "photonstrust",
                "version": str(app.version),
            },
        },
        "components": components,
    }


@app.get("/v0/runs/{run_id}/bundle")
def runs_bundle(
    run_id: str,
    request: Request,
    include_children: bool | None = Query(None, description="Include workflow child runs (default: true for workflow runs)."),
    rebuild: bool = Query(False, description="Rebuild bundle even if cached zip exists."),
):
    """Export a portable evidence bundle as a zip file.

    Safety posture:
    - includes only run_manifest.json + manifest-declared artifacts
    - uses safe artifact resolution under each run directory
    """

    ctx = _require_roles(request, "viewer", "runner", "approver")

    try:
        root_dir = run_store.run_dir_for_id(run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not root_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    root_manifest = run_store.read_run_manifest(root_dir) or runs_get(run_id, request)
    if not isinstance(root_manifest, dict):
        root_manifest = runs_get(run_id, request)
    _enforce_project_scope_or_403(ctx, _run_project_id_from_manifest(root_manifest))

    default_children = _is_workflow_manifest(root_manifest)
    include_children = bool(default_children) if include_children is None else bool(include_children)

    child_ids: list[str] = _workflow_child_run_ids(root_manifest) if include_children else []
    included_run_ids = [run_store.validate_run_id(run_id)] + child_ids

    bundle_rel = "evidence_bundle_with_children.zip" if include_children else "evidence_bundle_root_only.zip"
    bundle_path = root_dir / bundle_rel
    tmp_path = root_dir / (bundle_rel + ".tmp")
    if bundle_path.exists() and bundle_path.is_file() and not rebuild:
        headers = {
            "cache-control": "no-store",
            "content-disposition": f'attachment; filename="{bundle_path.name}"',
        }
        return FileResponse(path=str(bundle_path), media_type="application/zip", headers=headers)

    files: list[tuple[str, Path]] = []
    generated_files: list[tuple[str, bytes]] = []
    missing: list[dict[str, Any]] = []

    for rid in included_run_ids:
        try:
            rdir = run_store.run_dir_for_id(rid)
        except Exception:
            continue
        if not rdir.exists():
            missing.append({"run_id": rid, "path": None, "error": "run directory missing"})
            continue

        # 1) run manifest
        mf = rdir / run_store.RUN_MANIFEST_BASENAME
        if mf.exists() and mf.is_file():
            files.append((f"runs/run_{rid}/{run_store.RUN_MANIFEST_BASENAME}", mf))
            m = run_store.read_run_manifest(rdir) or {}
        else:
            m = runs_get(rid, request)
            try:
                generated_files.append(
                    (
                        f"runs/run_{rid}/{run_store.RUN_MANIFEST_BASENAME}",
                        json.dumps(m, indent=2).encode("utf-8"),
                    )
                )
            except Exception:
                missing.append({"run_id": rid, "path": run_store.RUN_MANIFEST_BASENAME, "error": "failed to serialize synthesized manifest"})

        # 2) manifest artifacts
        if isinstance(m, dict):
            for rel in _iter_manifest_artifact_relpaths(m):
                try:
                    p = run_store.resolve_artifact_path(rdir, rel)
                except FileNotFoundError as exc:
                    missing.append({"run_id": rid, "path": rel, "error": str(exc)})
                    continue
                except Exception as exc:
                    missing.append({"run_id": rid, "path": rel, "error": str(exc)})
                    continue
                arc = f"runs/run_{rid}/{str(rel).replace('\\\\', '/')}"
                files.append((arc, p))
        else:
            missing.append({"run_id": rid, "path": None, "error": "manifest not readable"})

    # Unique by archive name.
    seen_arc: set[str] = set()
    uniq_files: list[tuple[str, Path]] = []
    for arc, p in files:
        key = str(arc).lower()
        if key in seen_arc:
            continue
        seen_arc.add(key)
        uniq_files.append((arc, p))

    uniq_files.sort(key=lambda t: str(t[0]).lower())

    root_input = root_manifest.get("input") if isinstance(root_manifest.get("input"), dict) else {}
    root_execution_mode = str(root_input.get("execution_mode", "preview") or "preview").strip().lower() or "preview"
    if root_execution_mode == "certification":
        missing_invdesign = []
        for row in missing:
            if not isinstance(row, dict):
                continue
            rel = str(row.get("path", "") or "").strip().lower()
            if rel.endswith("invdesign_report.json") or rel.endswith("optimized_graph.json"):
                missing_invdesign.append(row)
        if missing_invdesign:
            raise HTTPException(
                status_code=400,
                detail="certification evidence bundle missing required inverse-design artifacts",
            )

    bundle_root = f"photonstrust_evidence_bundle_{run_store.validate_run_id(run_id)}"
    generated_at = str(root_manifest.get("generated_at") or datetime.now(timezone.utc).isoformat())

    readme = "\n".join(
        [
            "# PhotonTrust Evidence Bundle",
            "",
            f"- generated_at: {generated_at}",
            f"- root_run_id: {run_store.validate_run_id(run_id)}",
            f"- include_children: {str(include_children).lower()}",
            "",
            "This bundle contains run manifests + declared artifacts for offline review.",
            "Integrity metadata is recorded in bundle_manifest.json (sha256 per file).",
            "",
        ]
    ).encode("utf-8")

    sbom_rel = "sbom/cyclonedx.json"
    sbom_bytes = json.dumps(_build_cyclonedx_sbom(timestamp=generated_at), indent=2).encode("utf-8")
    generated_files.append((sbom_rel, sbom_bytes))

    bundle_manifest: dict[str, Any] = {
        "schema_version": "0.1",
        "generated_at": generated_at,
        "kind": "photonstrust.evidence_bundle",
        "root_run_id": run_store.validate_run_id(run_id),
        "include_children": bool(include_children),
        "included_run_ids": list(included_run_ids),
        "files": [],
        "missing": missing,
        "sbom": {
            "path": sbom_rel,
            "format": "cyclonedx+json",
            "sha256": None,
            "bytes": None,
        },
    }

    try:
        with zipfile.ZipFile(tmp_path, mode="w") as zf:
            # README first for human review.
            sha, size = _zip_write_bytes(zf, f"{bundle_root}/README.md", readme)
            bundle_manifest["files"].append({"path": "README.md", "sha256": sha, "bytes": size})

            generated_files.sort(key=lambda t: str(t[0]).lower())
            for arc, data in generated_files:
                sha, size = _zip_write_bytes(zf, f"{bundle_root}/{arc}", data)
                bundle_manifest["files"].append({"path": str(arc).replace("\\", "/"), "sha256": sha, "bytes": size})
                if str(arc).replace("\\", "/") == sbom_rel:
                    sbom_obj = bundle_manifest.get("sbom") if isinstance(bundle_manifest.get("sbom"), dict) else None
                    if isinstance(sbom_obj, dict):
                        sbom_obj["sha256"] = sha
                        sbom_obj["bytes"] = int(size)

            for arc, p in uniq_files:
                sha, size = _zip_write_file(zf, f"{bundle_root}/{arc}", p)
                bundle_manifest["files"].append(
                    {
                        "path": str(arc).replace("\\", "/"),
                        "sha256": sha,
                        "bytes": size,
                    }
                )

            bm = json.dumps(bundle_manifest, indent=2).encode("utf-8")
            sha, size = _zip_write_bytes(zf, f"{bundle_root}/bundle_manifest.json", bm)
            bundle_manifest["bundle_manifest_sha256"] = sha
            bundle_manifest["bundle_manifest_bytes"] = size
    except Exception as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            pass
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        tmp_path.replace(bundle_path)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {
        "cache-control": "no-store",
        "content-disposition": f'attachment; filename="{bundle_path.name}"',
    }
    return FileResponse(path=str(bundle_path), media_type="application/zip", headers=headers)


@app.post("/v0/runs/{run_id}/bundle/publish")
def runs_bundle_publish(
    run_id: str,
    request: Request,
    include_children: bool | None = Query(None, description="Include workflow child runs (default: true for workflow runs)."),
    rebuild: bool = Query(False, description="Rebuild bundle before publish."),
) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")

    try:
        root_dir = run_store.run_dir_for_id(run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not root_dir.exists():
        raise HTTPException(status_code=404, detail="run not found")

    root_manifest = run_store.read_run_manifest(root_dir) or runs_get(run_id, request)
    if not isinstance(root_manifest, dict):
        root_manifest = runs_get(run_id, request)
    _enforce_project_scope_or_403(ctx, _run_project_id_from_manifest(root_manifest))

    default_children = _is_workflow_manifest(root_manifest)
    include_children_resolved = bool(default_children) if include_children is None else bool(include_children)
    bundle_rel = "evidence_bundle_with_children.zip" if include_children_resolved else "evidence_bundle_root_only.zip"
    bundle_path = root_dir / bundle_rel

    if rebuild or not bundle_path.exists():
        _ = runs_bundle(
            run_id,
            request,
            include_children=include_children_resolved,
            rebuild=True,
        )

    if not bundle_path.exists() or not bundle_path.is_file():
        raise HTTPException(status_code=400, detail="bundle file was not created")

    bundle_sha, bundle_bytes = _sha256_file(bundle_path)
    publish_root = _published_bundles_root()
    zip_dest = publish_root / f"{bundle_sha}.zip"
    if not zip_dest.exists():
        shutil.copy2(bundle_path, zip_dest)

    verify = verify_bundle_zip(zip_dest, require_signature=False)
    publish_manifest = {
        "schema_version": "0.1",
        "kind": "photonstrust.evidence_bundle_publish_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_sha256": bundle_sha,
        "bundle_bytes": int(bundle_bytes),
        "bundle_path": str(zip_dest),
        "source_run_id": run_store.validate_run_id(run_id),
        "include_children": bool(include_children_resolved),
        "verify": {
            "ok": bool(verify.ok),
            "bundle_root": str(verify.bundle_root),
            "manifest_sha256": str(verify.manifest_sha256),
            "verified_files": int(verify.verified_files),
            "missing_files": int(verify.missing_files),
            "mismatched_files": int(verify.mismatched_files),
            "signature_verified": bool(verify.signature_verified),
            "errors": list(verify.errors),
        },
    }
    validate_instance(publish_manifest, evidence_bundle_publish_manifest_schema_path(), require_jsonschema=False)
    publish_manifest_path = publish_root / f"{bundle_sha}.manifest.json"
    publish_manifest_path.write_text(json.dumps(publish_manifest, indent=2), encoding="utf-8")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_sha256": bundle_sha,
        "bundle_bytes": int(bundle_bytes),
        "bundle_path": str(zip_dest),
        "publish_manifest_path": str(publish_manifest_path),
        "verify": publish_manifest["verify"],
    }


@app.get("/v0/evidence/bundle/by-digest/{digest}")
def evidence_bundle_by_digest(digest: str, request: Request):
    _ = _require_roles(request, "viewer", "runner", "approver")
    value = str(digest or "").strip().lower()
    if not _BUNDLE_DIGEST_RE.match(value):
        raise HTTPException(status_code=400, detail="digest must be a 64-char lowercase hex sha256")

    zip_path = _published_bundles_root() / f"{value}.zip"
    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=404, detail="published bundle not found")

    headers = {
        "cache-control": "no-store",
        "content-disposition": f'attachment; filename="{zip_path.name}"',
    }
    return FileResponse(path=str(zip_path), media_type="application/zip", headers=headers)


@app.get("/v0/evidence/bundle/by-digest/{digest}/verify")
def evidence_bundle_verify_by_digest(digest: str, request: Request) -> dict[str, Any]:
    _ = _require_roles(request, "viewer", "runner", "approver")
    value = str(digest or "").strip().lower()
    if not _BUNDLE_DIGEST_RE.match(value):
        raise HTTPException(status_code=400, detail="digest must be a 64-char lowercase hex sha256")

    zip_path = _published_bundles_root() / f"{value}.zip"
    if not zip_path.exists() or not zip_path.is_file():
        raise HTTPException(status_code=404, detail="published bundle not found")

    verify = verify_bundle_zip(zip_path, require_signature=False)
    publish_manifest_path = _published_bundles_root() / f"{value}.manifest.json"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "bundle_sha256": value,
        "bundle_path": str(zip_path),
        "publish_manifest_path": str(publish_manifest_path) if publish_manifest_path.exists() else None,
        "verify": {
            "ok": bool(verify.ok),
            "bundle_root": str(verify.bundle_root),
            "manifest_sha256": str(verify.manifest_sha256),
            "verified_files": int(verify.verified_files),
            "missing_files": int(verify.missing_files),
            "mismatched_files": int(verify.mismatched_files),
            "signature_verified": bool(verify.signature_verified),
            "errors": list(verify.errors),
        },
    }


@app.post("/v0/runs/diff")
def runs_diff(request: Request, payload: dict = Body(...)) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
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
        _enforce_project_scope_or_403(ctx, _run_project_id_from_manifest(lhs_manifest))
    if isinstance(rhs_manifest, dict):
        _enforce_project_scope_or_403(ctx, _run_project_id_from_manifest(rhs_manifest))

    if scope == "input":
        lhs_obj = lhs_manifest.get("input", {})
        rhs_obj = rhs_manifest.get("input", {})
    elif scope == "outputs_summary":
        lhs_obj = lhs_manifest.get("outputs_summary", {})
        rhs_obj = rhs_manifest.get("outputs_summary", {})
    else:
        lhs_obj = lhs_manifest
        rhs_obj = rhs_manifest
    if not isinstance(lhs_obj, dict):
        lhs_obj = {}
    if not isinstance(rhs_obj, dict):
        rhs_obj = {}

    diff = diff_json(lhs_obj, rhs_obj, limit=limit)
    violation_diff = None
    if scope in ("outputs_summary", "all"):
        lhs_outputs = lhs_manifest.get("outputs_summary", {}) if isinstance(lhs_manifest, dict) else {}
        rhs_outputs = rhs_manifest.get("outputs_summary", {}) if isinstance(rhs_manifest, dict) else {}
        lhs_rows = _extract_violation_rows(lhs_outputs)
        rhs_rows = _extract_violation_rows(rhs_outputs)
        if lhs_rows is not None and rhs_rows is not None:
            violation_diff = diff_violations(lhs_rows, rhs_rows)

    lhs_summary = run_store.summarize_manifest(lhs_manifest) if isinstance(lhs_manifest, dict) else {}
    rhs_summary = run_store.summarize_manifest(rhs_manifest) if isinstance(rhs_manifest, dict) else {}

    diff_payload: dict[str, Any] = {
        "changes": diff.get("changes", []),
        "summary": {
            "change_count": len(diff.get("changes", []) or []),
            "truncated": bool(diff.get("truncated", False)),
        },
    }
    if violation_diff is not None:
        diff_payload["violation_diff"] = violation_diff
    interop = _interop_diff(lhs_manifest if isinstance(lhs_manifest, dict) else {}, rhs_manifest if isinstance(rhs_manifest, dict) else {})
    if interop is not None:
        diff_payload["interop_diff"] = interop

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "lhs": lhs_summary,
        "rhs": rhs_summary,
        "diff": diff_payload,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.get("/v0/projects")
def projects_list(request: Request, limit: int = Query(200, ge=1, le=500)) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
    projects = project_store.list_projects(limit=int(limit))
    if "*" not in ctx.get("projects", {"*"}):
        allowed = ctx.get("projects") if isinstance(ctx.get("projects"), set) else set()
        projects = [
            row
            for row in projects
            if isinstance(row, dict) and str(row.get("project_id") or "default").strip().lower() in allowed
        ]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_root": str(run_store.runs_root()),
        "projects": projects,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.get("/v0/projects/{project_id}/approvals")
def projects_approvals_list(request: Request, project_id: str, limit: int = Query(50, ge=1, le=500)) -> dict[str, Any]:
    ctx = _require_roles(request, "viewer", "runner", "approver")
    try:
        pid = project_store.validate_project_id(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _enforce_project_scope_or_403(ctx, pid)

    approvals = project_store.list_approval_events(pid, limit=int(limit))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "project_id": pid,
        "approvals": approvals,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/projects/{project_id}/approvals")
def projects_approvals_create(request: Request, project_id: str, payload: dict = Body(...)) -> dict[str, Any]:
    ctx = _require_roles(request, "approver")
    try:
        pid = project_store.validate_project_id(project_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _enforce_project_scope_or_403(ctx, pid)

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
    run_pid = str(((manifest or {}).get("input", {}) or {}).get("project_id") or "default").strip().lower() or "default"
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
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/ui/telemetry/events")
def ui_telemetry_events_ingest(request: Request, payload: dict = Body(...)) -> dict[str, Any]:
    ctx = _require_roles(request, "runner", "approver")
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for telemetry event")

    event_name = str(payload.get("event_name") or payload.get("event") or "").strip().lower()
    if not event_name:
        raise HTTPException(status_code=400, detail="event_name is required")
    if not _UI_TELEMETRY_EVENT_RE.match(event_name) or event_name not in _UI_TELEMETRY_EVENT_NAMES:
        raise HTTPException(status_code=400, detail="unsupported event_name")

    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")
    if len(session_id) > 128:
        raise HTTPException(status_code=400, detail="session_id must be <= 128 chars")

    user_mode = str(payload.get("user_mode") or "").strip().lower()
    if user_mode not in _UI_TELEMETRY_USER_MODES:
        raise HTTPException(status_code=400, detail="user_mode must be one of: builder, reviewer, exec")

    profile = str(payload.get("profile") or "").strip().lower()
    if profile not in _UI_TELEMETRY_PROFILES:
        raise HTTPException(status_code=400, detail="profile must be one of: qkd_link, pic_circuit, orbit")

    outcome = str(payload.get("outcome") or "success").strip().lower() or "success"
    if outcome not in _UI_TELEMETRY_OUTCOMES:
        raise HTTPException(status_code=400, detail="outcome must be one of: success, failure, abandoned")

    run_id = str(payload.get("run_id") or "").strip()
    if len(run_id) > 128:
        raise HTTPException(status_code=400, detail="run_id must be <= 128 chars")

    duration_ms: int | None = None
    duration_raw = payload.get("duration_ms")
    if duration_raw is not None and str(duration_raw).strip() != "":
        try:
            duration_ms = int(round(float(duration_raw)))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="duration_ms must be numeric when provided") from exc
        if duration_ms < 0:
            raise HTTPException(status_code=400, detail="duration_ms must be >= 0")

    payload_obj = payload.get("payload")
    if payload_obj is None:
        payload_obj = {}
    if not isinstance(payload_obj, dict):
        raise HTTPException(status_code=400, detail="payload must be a JSON object when provided")
    if len(json.dumps(payload_obj, ensure_ascii=True)) > 64000:
        raise HTTPException(status_code=400, detail="payload too large")

    timestamp_utc = _normalize_utc_timestamp(payload.get("timestamp_utc"), field_name="timestamp_utc")
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _enforce_project_scope_or_403(ctx, project_id)

    event = {
        "schema_version": "0.1",
        "kind": "photonstrust.ui_metric_event",
        "event_id": uuid.uuid4().hex[:12],
        "event_name": event_name,
        "timestamp_utc": timestamp_utc,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "user_mode": user_mode,
        "profile": profile,
        "project_id": project_id,
        "run_id": run_id or None,
        "duration_ms": duration_ms,
        "outcome": outcome,
        "payload": payload_obj,
    }
    try:
        out_path = ui_metrics_store.append_ui_metric_event(event)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "accepted": True,
        "path": str(out_path),
        "event": event,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/graph/validate")
def graph_validate(payload: dict = Body(...)) -> dict[str, Any]:
    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload  # allow posting graph directly
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    try:
        validate_graph(graph, require_jsonschema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    diagnostics = validate_graph_semantics(graph)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_id": graph.get("graph_id"),
        "profile": str(graph.get("profile", "")).strip().lower(),
        "graph_hash": hash_dict(graph),
        "diagnostics": diagnostics,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/graph/compile")
def graph_compile(payload: dict = Body(...)) -> dict[str, Any]:
    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload  # allow posting graph directly
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    include_cache_stats = bool(payload.get("include_cache_stats", False)) if isinstance(payload, dict) else False
    try:
        compiled_payload, compile_cache = compile_cache_store.compile_graph_cached(graph, require_schema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    compile_cache_payload: dict[str, Any] = {"key": compile_cache.get("key")}
    if include_cache_stats:
        compile_cache_payload["hit"] = bool(compile_cache.get("hit", False))

    return {
        "generated_at": compiled_payload.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "graph_id": compiled_payload.get("graph_id"),
        "profile": compiled_payload.get("profile"),
        "graph_hash": compiled_payload.get("graph_hash"),
        "diagnostics": compiled_payload.get("diagnostics"),
        "compiled": compiled_payload.get("compiled"),
        "warnings": compiled_payload.get("warnings"),
        "assumptions_md": compiled_payload.get("assumptions_md"),
        "compile_cache": compile_cache_payload,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/qkd/run")
def qkd_run(payload: dict = Body(...)) -> dict[str, Any]:
    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    execution_mode = str(payload.get("execution_mode", "preview")).strip().lower()
    include_cache_stats = bool(payload.get("include_cache_stats", False))
    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    execution_mode = _parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    pdk_manifest = None
    if isinstance(payload.get("pdk_manifest"), dict):
        pdk_manifest = _coerce_pdk_manifest_payload(
            payload.get("pdk_manifest"),
            execution_mode=execution_mode,
        )
    if not isinstance(pdk_manifest, dict):
        pdk_manifest = _resolve_run_pdk_manifest(
            pdk_request=pdk_req,
            execution_mode=execution_mode,
            require_context_in_cert=True,
        )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(
            status_code=400,
            detail="certification mode requires explicit pdk manifest context (provide payload.pdk or payload.pdk_manifest)",
        )
    execution_mode = _parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    try:
        compiled_payload, compile_cache = compile_cache_store.compile_graph_cached(graph, require_schema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if str(compiled_payload.get("profile", "")) != "qkd_link":
        raise HTTPException(status_code=400, detail="qkd/run expects a graph with profile=qkd_link")

    cfg = dict(compiled_payload.get("compiled") if isinstance(compiled_payload.get("compiled"), dict) else {})
    scenario = cfg.get("scenario", {}) or {}
    if not isinstance(scenario, dict):
        scenario = {}
    scenario["execution_mode"] = execution_mode
    cfg["scenario"] = scenario

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    try:
        scenarios = build_scenarios(cfg)
        result = run_scenarios(scenarios, run_dir, run_id=run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scenario_primary = scenarios[0] if isinstance(scenarios, list) and scenarios and isinstance(scenarios[0], dict) else {}

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
    steps_payload = _safe_read_json_object(Path(protocol_step_meta.get("protocol_steps_json", ""))) or {}
    if steps_payload:
        validate_instance(steps_payload, protocol_steps_schema_path(), require_jsonschema=False)

    event_trace_meta = _write_qkd_event_trace_artifact(
        scenario=scenario_primary,
        output_dir=run_dir,
    )

    generated_at = datetime.now(timezone.utc).isoformat()
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

    steps_rel = _to_run_relpath(run_dir, protocol_step_meta.get("protocol_steps_json", ""))
    if steps_rel:
        artifacts["protocol_steps_json"] = steps_rel

    qasm_artifacts = protocol_step_meta.get("protocol_steps", {}).get("qasm_artifacts", {})
    if isinstance(qasm_artifacts, dict):
        for key, abs_path in qasm_artifacts.items():
            rel = _to_run_relpath(run_dir, abs_path)
            if rel:
                artifacts[str(key)] = rel

    event_trace_rel = _to_run_relpath(run_dir, event_trace_meta.get("event_trace_json", ""))
    if event_trace_rel:
        artifacts["event_trace_json"] = event_trace_rel

    if isinstance(cards, list) and cards:
        cards_manifest = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            scenario_id = str(card.get("scenario_id", "")).strip()
            band = str(card.get("band", "")).strip()
            a = card.get("artifacts", {}) or {}
            if not isinstance(a, dict):
                a = {}

            card_artifacts: dict[str, Any] = {}
            if scenario_id and band:
                card_artifacts["results_json"] = f"{scenario_id}/{band}/results.json"
                if artifacts.get("multifidelity_report_json"):
                    card_artifacts["multifidelity_report_json"] = str(artifacts["multifidelity_report_json"])

            for key in ("report_html_path", "report_pdf_path", "card_path"):
                p = a.get(key)
                if not p:
                    continue
                try:
                    rel = str(Path(str(p)).resolve().relative_to(run_dir.resolve())).replace("\\", "/")
                except Exception:
                    rel = None
                if rel:
                    card_artifacts[key.replace("_path", "")] = rel

            plots = a.get("plots", {}) or {}
            if isinstance(plots, dict) and plots.get("key_rate_vs_distance_path"):
                try:
                    rel = (
                        str(Path(str(plots["key_rate_vs_distance_path"])).resolve().relative_to(run_dir.resolve())).replace("\\", "/")
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
            "protocol_steps": dict(protocol_step_meta.get("protocol_steps", {})),
            "event_trace": dict(event_trace_meta.get("event_trace", {})),
        }
    }
    if isinstance(cards, list) and cards:
        summary_cards = []
        for card in cards:
            if not isinstance(card, dict):
                continue
            sid = str(card.get("scenario_id", "")).strip()
            band = str(card.get("band", "")).strip()
            outs = card.get("outputs", {}) or {}
            derived = card.get("derived", {}) or {}
            safe = card.get("safe_use_label", {}) or {}
            if not isinstance(outs, dict):
                outs = {}
            if not isinstance(derived, dict):
                derived = {}
            if not isinstance(safe, dict):
                safe = {}
            ci = card.get("confidence_intervals", {}) or {}
            if not isinstance(ci, dict):
                ci = {}
            fk_ledger = card.get("finite_key_epsilon_ledger", {}) or {}
            if not isinstance(fk_ledger, dict):
                fk_ledger = {}
            model_prov = card.get("model_provenance", {}) or {}
            if not isinstance(model_prov, dict):
                model_prov = {}
            sec_assumptions = card.get("security_assumptions_metadata", {}) or {}
            if not isinstance(sec_assumptions, dict):
                sec_assumptions = {}
            gate_policy = protocol_gate_policy(model_prov.get("protocol_normalized"))
            summary_cards.append(
                {
                    "scenario_id": sid,
                    "band": band,
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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
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

        result_payload = {
            "run_id": run_payload.get("run_id"),
            "output_dir": run_payload.get("output_dir"),
            "manifest_path": run_payload.get("manifest_path"),
            "artifact_relpaths": run_payload.get("artifact_relpaths") if isinstance(run_payload.get("artifact_relpaths"), dict) else {},
            "graph_hash": run_payload.get("graph_hash"),
            "compile_cache": run_payload.get("compile_cache") if isinstance(run_payload.get("compile_cache"), dict) else {},
        }
        job_store.set_result(job_id, result_payload)
    except HTTPException as exc:
        job_store.set_error(
            job_id,
            {
                "status_code": int(exc.status_code),
                "detail": str(exc.detail),
                "type": "HTTPException",
            },
        )
    except Exception as exc:
        job_store.set_error(
            job_id,
            {
                "status_code": 500,
                "detail": str(exc),
                "type": str(type(exc).__name__),
            },
        )


@app.post("/v0/qkd/run/async")
def qkd_run_async(payload: dict = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for qkd async payload")

    graph = payload.get("graph") if isinstance(payload.get("graph"), dict) else payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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


@app.post("/v0/qkd/import_external")
def qkd_import_external(payload: dict = Body(...)) -> dict[str, Any]:
    ext = payload.get("external_result") if isinstance(payload.get("external_result"), dict) else payload
    if not isinstance(ext, dict):
        raise HTTPException(status_code=400, detail="external_result object is required")

    try:
        validate_instance(ext, external_sim_result_schema_path(), require_jsonschema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    ext_path = run_dir / "external_sim_result.json"
    ext_path.write_text(json.dumps(ext, indent=2), encoding="utf-8")

    card = build_reliability_card_from_external_result(ext)
    card_path = run_dir / "reliability_card.json"
    write_reliability_card(card, card_path)

    model = card.get("model_provenance") if isinstance(card.get("model_provenance"), dict) else {}
    protocol_selected = model.get("protocol_normalized")
    outputs_summary = {
        "qkd_external_import": {
            "source": "external_import",
            "simulator_name": ext.get("simulator_name"),
            "simulator_version": ext.get("simulator_version"),
            "protocol_selected": protocol_selected,
            "key_rate_bps": (card.get("outputs") or {}).get("key_rate_bps"),
            "qber_total": (card.get("derived") or {}).get("qber_total"),
            "fidelity_est": (card.get("outputs") or {}).get("fidelity_est"),
        }
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "qkd_external_import",
        "generated_at": datetime.now(timezone.utc).isoformat(),
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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "run_id": run_id,
        "output_dir": str(run_dir),
        "manifest_path": str(manifest_path),
        "external_result_hash": hash_dict(ext),
        "card_path": str(card_path),
    }


@app.post("/v0/orbit/pass/validate")
def orbit_pass_validate(payload: dict = Body(...)) -> dict[str, Any]:
    config = payload.get("config") if isinstance(payload, dict) else None
    if not isinstance(config, dict):
        config = payload  # allow posting config directly
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for orbit pass config payload")

    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    try:
        validate_orbit_pass_config(config, require_jsonschema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    diagnostics = validate_orbit_pass_semantics(config)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config_hash": hash_dict(config),
        "diagnostics": diagnostics,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/orbit/pass/run")
def orbit_pass_run(payload: dict = Body(...)) -> dict[str, Any]:
    config = payload.get("config") if isinstance(payload, dict) else None
    if not isinstance(config, dict):
        config = payload  # allow posting config directly
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for orbit pass config payload")

    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    try:
        validate_orbit_pass_config(config, require_jsonschema=require_schema)
        diagnostics = validate_orbit_pass_semantics(config)
        artifacts = run_orbit_pass_from_config(config, run_dir)
        results_path = Path(str(artifacts.get("results_path", "")))
        results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc).isoformat()
    orbit_pass_id = str((config.get("orbit_pass") or {}).get("id", "")).strip()
    band = str((config.get("orbit_pass") or {}).get("band", "")).strip()
    report_rel = f"{orbit_pass_id}/{band}/orbit_pass_report.html" if orbit_pass_id and band else None
    results_rel = f"{orbit_pass_id}/{band}/orbit_pass_results.json" if orbit_pass_id and band else None

    outputs_summary: dict[str, Any] = {"orbit_pass": {"pass_id": orbit_pass_id, "band": band, "cases": []}}
    if isinstance(results, dict):
        cases = results.get("cases", []) or []
        if isinstance(cases, list):
            out_cases = []
            for c in cases:
                if not isinstance(c, dict):
                    continue
                s = c.get("summary", {}) or {}
                if not isinstance(s, dict):
                    s = {}
                out_cases.append(
                    {
                        "case_id": c.get("case_id"),
                        "label": c.get("label"),
                        "total_keys_bits": s.get("total_keys_bits"),
                        "expected_total_keys_bits": s.get("expected_total_keys_bits"),
                        "avg_key_rate_bps": s.get("avg_key_rate_bps"),
                        "min_key_rate_bps": s.get("min_key_rate_bps"),
                        "max_key_rate_bps": s.get("max_key_rate_bps"),
                        "avg_channel_outage_probability": s.get("avg_channel_outage_probability"),
                        "max_channel_outage_probability": s.get("max_channel_outage_probability"),
                        "background_model": s.get("background_model"),
                        "background_day_night": s.get("background_day_night"),
                        "avg_background_counts_cps": s.get("avg_background_counts_cps"),
                        "max_background_counts_cps": s.get("max_background_counts_cps"),
                        "finite_key": s.get("finite_key"),
                    }
                )
            outputs_summary["orbit_pass"]["cases"] = out_cases
        trust = results.get("trust_label", {}) or {}
        if isinstance(trust, dict):
            outputs_summary["orbit_pass"]["trust_label"] = {
                "mode": trust.get("mode"),
                "label": trust.get("label"),
                "regime": trust.get("regime"),
            }
        finite_key = results.get("finite_key", {}) or {}
        if isinstance(finite_key, dict):
            outputs_summary["orbit_pass"]["finite_key"] = {
                "enabled": finite_key.get("enabled"),
                "effective_signals_per_block": finite_key.get("effective_signals_per_block"),
                "signals_per_pass_budget": finite_key.get("signals_per_pass_budget"),
                "security_epsilon": finite_key.get("security_epsilon"),
                "pass_duration_s": finite_key.get("pass_duration_s"),
            }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "orbit_pass",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "config_hash": hash_dict(config),
            "orbit_pass_id": orbit_pass_id,
            "band": band,
        },
        "outputs_summary": outputs_summary,
        "artifacts": {
            "orbit_pass_report_html": report_rel,
            "orbit_pass_results_json": results_rel,
        },
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "config_hash": hash_dict(config),
        "output_dir": str(artifacts.get("output_dir", "")),
        "results_path": str(artifacts.get("results_path", "")),
        "report_html_path": str(artifacts.get("report_html_path", "")),
        "diagnostics": diagnostics,
        "results": results,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {
            "orbit_pass_report_html": report_rel,
            "orbit_pass_results_json": results_rel,
        },
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/simulate")
def pic_simulate(payload: dict = Body(...)) -> dict[str, Any]:
    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    wavelengths_nm = payload.get("wavelength_sweep_nm") if isinstance(payload, dict) else None
    wavelength_nm = payload.get("wavelength_nm") if isinstance(payload, dict) else None

    try:
        compiled = compile_graph(graph, require_schema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if compiled.profile != "pic_circuit":
        raise HTTPException(status_code=400, detail="pic/simulate expects a graph with profile=pic_circuit")

    netlist = dict(compiled.compiled)
    # Security posture for MVP: disable Touchstone file reads via API by default.
    for node in netlist.get("nodes", []) or []:
        if str((node or {}).get("kind", "")).strip().lower() == "pic.touchstone_2port":
            raise HTTPException(
                status_code=400,
                detail="pic.touchstone_2port is disabled in the API server (file access). Use CLI workflows.",
            )

    try:
        if wavelengths_nm:
            wavelengths = [float(x) for x in wavelengths_nm]
            results = simulate_pic_netlist_sweep(netlist, wavelengths_nm=wavelengths)
        else:
            wn = float(wavelength_nm) if wavelength_nm is not None else None
            results = simulate_pic_netlist(netlist, wavelength_nm=wn)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "graph_hash": hash_dict(graph),
        "netlist": netlist,
        "results": results,
    }


@app.post("/v0/pic/invdesign/mzi_phase")
def pic_invdesign_mzi_phase(payload: dict = Body(...)) -> dict[str, Any]:
    """Inverse-design an MZI-like PIC graph by tuning one phase shifter."""

    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    execution_mode = _parse_execution_mode(payload)

    try:
        compiled = compile_graph(graph, require_schema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if compiled.profile != "pic_circuit":
        raise HTTPException(status_code=400, detail="pic/invdesign/mzi_phase expects profile=pic_circuit")

    netlist = dict(compiled.compiled)
    for node in netlist.get("nodes", []) or []:
        if str((node or {}).get("kind", "")).strip().lower() == "pic.touchstone_2port":
            raise HTTPException(
                status_code=400,
                detail="pic.touchstone_2port is disabled in the API server (file access). Use CLI workflows.",
            )

    phase_node_id = str(payload.get("phase_node_id", "")).strip()
    if not phase_node_id:
        # Deterministic default: first phase_shifter node (sorted by id in compiler).
        for node in netlist.get("nodes", []) or []:
            if str((node or {}).get("kind", "")).strip().lower() == "pic.phase_shifter":
                phase_node_id = str((node or {}).get("id", "")).strip()
                break
    if not phase_node_id:
        raise HTTPException(status_code=400, detail="No pic.phase_shifter nodes found to optimize")

    target_output_node = str(payload.get("target_output_node", "cpl_out")).strip() or "cpl_out"
    target_output_port = str(payload.get("target_output_port", "out1")).strip() or "out1"
    target_fraction = float(payload.get("target_power_fraction", 0.9))
    steps = int(payload.get("steps", 181) or 181)
    robustness_cases = payload.get("robustness_cases") if isinstance(payload.get("robustness_cases"), list) else None
    wavelength_objective_agg = str(payload.get("wavelength_objective_agg", "mean") or "mean")
    case_objective_agg = str(payload.get("case_objective_agg", "mean") or "mean")
    robustness_thresholds = payload.get("robustness_thresholds") if isinstance(payload.get("robustness_thresholds"), dict) else None
    robustness_required = bool(payload.get("robustness_required", execution_mode == "certification"))
    if execution_mode == "certification":
        robustness_required = True
    solver_backend = str(payload.get("solver_backend", "core") or "core")
    solver_plugin = payload.get("solver_plugin") if isinstance(payload.get("solver_plugin"), dict) else None

    wavelengths_nm = payload.get("wavelength_sweep_nm")
    if wavelengths_nm is None:
        wl = (netlist.get("circuit", {}) or {}).get("wavelength_nm", 1550.0)
        wavelengths_nm = [wl]
    try:
        wavelengths_nm = [float(x) for x in (wavelengths_nm or [])]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid wavelength_sweep_nm: {exc}") from exc

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        result = inverse_design_mzi_phase(
            netlist,
            phase_node_id=phase_node_id,
            target_output_node=target_output_node,
            target_output_port=target_output_port,
            target_power_fraction=target_fraction,
            wavelengths_nm=wavelengths_nm,
            steps=steps,
            robustness_cases=robustness_cases,
            wavelength_objective_agg=wavelength_objective_agg,
            case_objective_agg=case_objective_agg,
            robustness_required=robustness_required,
            robustness_thresholds=robustness_thresholds,
            execution_mode=execution_mode,
            solver_backend=solver_backend,
            solver_plugin=solver_plugin,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Update the incoming graph (keep UI metadata) with the optimized phase.
    optimized_graph = json.loads(json.dumps(graph))
    for node in optimized_graph.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if str(node.get("id", "")).strip() != phase_node_id:
            continue
        params = node.get("params", {}) or {}
        if not isinstance(params, dict):
            params = {}
        params["phase_rad"] = float(result.best_phase_rad)
        node["params"] = params

    generated_at = datetime.now(timezone.utc).isoformat()
    report_rel = "invdesign_report.json"
    graph_rel = "optimized_graph.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    (Path(run_dir) / graph_rel).write_text(json.dumps(optimized_graph, indent=2), encoding="utf-8")

    artifact_relpaths = {
        "invdesign_report_json": report_rel,
        "optimized_graph_json": graph_rel,
    }
    _enforce_invdesign_evidence_or_400(
        report=result.report,
        run_dir=Path(run_dir),
        artifact_relpaths=artifact_relpaths,
        execution_mode=execution_mode,
    )

    best_eval = ((result.report.get("best") or {}).get("robustness_eval") or {}) if isinstance(result.report, dict) else {}
    if not isinstance(best_eval, dict):
        best_eval = {}
    best_metrics = best_eval.get("metrics") if isinstance(best_eval.get("metrics"), dict) else {}
    threshold_eval = best_eval.get("threshold_eval") if isinstance(best_eval.get("threshold_eval"), dict) else {}
    execution = result.report.get("execution") if isinstance(result.report.get("execution"), dict) else {}
    solver = execution.get("solver") if isinstance(execution.get("solver"), dict) else {}

    outputs_summary = {
        "invdesign": {
            "kind": "pic.invdesign.mzi_phase",
            "design_node_id": phase_node_id,
            "design_param": "phase_rad",
            "best_value": float(result.best_phase_rad),
            "achieved_fraction_nominal_mean": float(result.achieved_fraction),
            "objective": float(result.objective),
            "wavelength_objective_agg": str((result.report.get("inputs", {}) or {}).get("robustness", {}).get("wavelength_objective_agg") or ""),
            "case_objective_agg": str((result.report.get("inputs", {}) or {}).get("robustness", {}).get("case_objective_agg") or ""),
            "objective_case_max": (best_metrics.get("objective_case_max") if isinstance(best_metrics, dict) else None),
            "worst_case_achieved_fraction": (
                best_metrics.get("worst_case_achieved_fraction") if isinstance(best_metrics, dict) else None
            ),
            "threshold_pass": (threshold_eval.get("pass") if isinstance(threshold_eval, dict) else None),
            "solver_backend_requested": (solver.get("backend_requested") if isinstance(solver, dict) else None),
            "solver_backend_used": (solver.get("backend_used") if isinstance(solver, dict) else None),
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
            "kind": "pic.invdesign.mzi_phase",
            "execution_mode": execution_mode,
        },
        "outputs_summary": outputs_summary,
        "artifacts": artifact_relpaths,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "graph_hash": hash_dict(graph),
        "optimized_graph": optimized_graph,
        "report": result.report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": artifact_relpaths,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/invdesign/coupler_ratio")
def pic_invdesign_coupler_ratio(payload: dict = Body(...)) -> dict[str, Any]:
    """Inverse-design a PIC graph by tuning one coupler coupling ratio."""

    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    execution_mode = _parse_execution_mode(payload)

    try:
        compiled = compile_graph(graph, require_schema=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if compiled.profile != "pic_circuit":
        raise HTTPException(status_code=400, detail="pic/invdesign/coupler_ratio expects profile=pic_circuit")

    netlist = dict(compiled.compiled)
    for node in netlist.get("nodes", []) or []:
        if str((node or {}).get("kind", "")).strip().lower() == "pic.touchstone_2port":
            raise HTTPException(
                status_code=400,
                detail="pic.touchstone_2port is disabled in the API server (file access). Use CLI workflows.",
            )

    coupler_node_id = str(payload.get("coupler_node_id", "")).strip()
    if not coupler_node_id:
        # Deterministic default: first coupler node (sorted by id in compiler).
        for node in netlist.get("nodes", []) or []:
            if str((node or {}).get("kind", "")).strip().lower() == "pic.coupler":
                coupler_node_id = str((node or {}).get("id", "")).strip()
                break
    if not coupler_node_id:
        raise HTTPException(status_code=400, detail="No pic.coupler nodes found to optimize")

    target_output_node = str(payload.get("target_output_node", "cpl_out")).strip() or "cpl_out"
    target_output_port = str(payload.get("target_output_port", "out1")).strip() or "out1"
    target_fraction = float(payload.get("target_power_fraction", 0.5))
    steps = int(payload.get("steps", 101) or 101)
    robustness_cases = payload.get("robustness_cases") if isinstance(payload.get("robustness_cases"), list) else None
    wavelength_objective_agg = str(payload.get("wavelength_objective_agg", "mean") or "mean")
    case_objective_agg = str(payload.get("case_objective_agg", "mean") or "mean")
    robustness_thresholds = payload.get("robustness_thresholds") if isinstance(payload.get("robustness_thresholds"), dict) else None
    robustness_required = bool(payload.get("robustness_required", execution_mode == "certification"))
    if execution_mode == "certification":
        robustness_required = True
    solver_backend = str(payload.get("solver_backend", "core") or "core")
    solver_plugin = payload.get("solver_plugin") if isinstance(payload.get("solver_plugin"), dict) else None

    wavelengths_nm = payload.get("wavelength_sweep_nm")
    if wavelengths_nm is None:
        wl = (netlist.get("circuit", {}) or {}).get("wavelength_nm", 1550.0)
        wavelengths_nm = [wl]
    try:
        wavelengths_nm = [float(x) for x in (wavelengths_nm or [])]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid wavelength_sweep_nm: {exc}") from exc

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        result = inverse_design_coupler_ratio(
            netlist,
            coupler_node_id=coupler_node_id,
            target_output_node=target_output_node,
            target_output_port=target_output_port,
            target_power_fraction=target_fraction,
            wavelengths_nm=wavelengths_nm,
            steps=steps,
            robustness_cases=robustness_cases,
            wavelength_objective_agg=wavelength_objective_agg,
            case_objective_agg=case_objective_agg,
            robustness_required=robustness_required,
            robustness_thresholds=robustness_thresholds,
            execution_mode=execution_mode,
            solver_backend=solver_backend,
            solver_plugin=solver_plugin,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    optimized_graph = json.loads(json.dumps(graph))
    for node in optimized_graph.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        if str(node.get("id", "")).strip() != coupler_node_id:
            continue
        params = node.get("params", {}) or {}
        if not isinstance(params, dict):
            params = {}
        params["coupling_ratio"] = float(result.best_coupling_ratio)
        node["params"] = params

    generated_at = datetime.now(timezone.utc).isoformat()
    report_rel = "invdesign_report.json"
    graph_rel = "optimized_graph.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(result.report, indent=2), encoding="utf-8")
    (Path(run_dir) / graph_rel).write_text(json.dumps(optimized_graph, indent=2), encoding="utf-8")

    artifact_relpaths = {
        "invdesign_report_json": report_rel,
        "optimized_graph_json": graph_rel,
    }
    _enforce_invdesign_evidence_or_400(
        report=result.report,
        run_dir=Path(run_dir),
        artifact_relpaths=artifact_relpaths,
        execution_mode=execution_mode,
    )

    best_eval = ((result.report.get("best") or {}).get("robustness_eval") or {}) if isinstance(result.report, dict) else {}
    if not isinstance(best_eval, dict):
        best_eval = {}
    best_metrics = best_eval.get("metrics") if isinstance(best_eval.get("metrics"), dict) else {}
    threshold_eval = best_eval.get("threshold_eval") if isinstance(best_eval.get("threshold_eval"), dict) else {}
    execution = result.report.get("execution") if isinstance(result.report.get("execution"), dict) else {}
    solver = execution.get("solver") if isinstance(execution.get("solver"), dict) else {}

    outputs_summary = {
        "invdesign": {
            "kind": "pic.invdesign.coupler_ratio",
            "design_node_id": coupler_node_id,
            "design_param": "coupling_ratio",
            "best_value": float(result.best_coupling_ratio),
            "achieved_fraction_nominal_mean": float(result.achieved_fraction),
            "objective": float(result.objective),
            "wavelength_objective_agg": str((result.report.get("inputs", {}) or {}).get("robustness", {}).get("wavelength_objective_agg") or ""),
            "case_objective_agg": str((result.report.get("inputs", {}) or {}).get("robustness", {}).get("case_objective_agg") or ""),
            "objective_case_max": (best_metrics.get("objective_case_max") if isinstance(best_metrics, dict) else None),
            "worst_case_achieved_fraction": (
                best_metrics.get("worst_case_achieved_fraction") if isinstance(best_metrics, dict) else None
            ),
            "threshold_pass": (threshold_eval.get("pass") if isinstance(threshold_eval, dict) else None),
            "solver_backend_requested": (solver.get("backend_requested") if isinstance(solver, dict) else None),
            "solver_backend_used": (solver.get("backend_used") if isinstance(solver, dict) else None),
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
            "kind": "pic.invdesign.coupler_ratio",
            "execution_mode": execution_mode,
        },
        "outputs_summary": outputs_summary,
        "artifacts": artifact_relpaths,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "graph_hash": hash_dict(graph),
        "optimized_graph": optimized_graph,
        "report": result.report,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": artifact_relpaths,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/workflow/invdesign_chain")
def pic_workflow_invdesign_chain(payload: dict = Body(...)) -> dict[str, Any]:
    """Run a chained PIC workflow (v0.1).

    Chain:
      1) invdesign (mzi_phase or coupler_ratio)
      2) layout build
      3) LVS-lite
      4) optional KLayout artifact pack (if GDS is available)
      5) SPICE export

    Produces a top-level workflow run manifest + report that references child run IDs.
    """

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object payload")

    graph = payload.get("graph")
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    require_schema = bool(payload.get("require_schema", False))
    execution_mode = _parse_execution_mode(payload)

    inv_cfg = payload.get("invdesign") if isinstance(payload.get("invdesign"), dict) else {}
    inv_kind_raw = inv_cfg.get("kind", None)
    if inv_kind_raw is None:
        inv_kind_raw = payload.get("invdesign_kind", None)
    inv_kind = str(inv_kind_raw or "mzi_phase").strip().lower()
    if inv_kind in ("pic.invdesign.mzi_phase", "mzi_phase"):
        inv_kind = "mzi_phase"
    elif inv_kind in ("pic.invdesign.coupler_ratio", "coupler_ratio"):
        inv_kind = "coupler_ratio"
    else:
        raise HTTPException(status_code=400, detail="Unsupported invdesign.kind (expected 'mzi_phase' or 'coupler_ratio')")

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
    optimized_graph = inv_res.get("optimized_graph")
    if not isinstance(optimized_graph, dict):
        raise HTTPException(status_code=400, detail="invdesign did not return optimized_graph")

    layout_cfg = payload.get("layout") if isinstance(payload.get("layout"), dict) else {}
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

    layout_run_id = str(layout_res.get("run_id", "")).strip()
    if not layout_run_id:
        raise HTTPException(status_code=400, detail="layout build did not return run_id")

    lvs_cfg = payload.get("lvs_lite") if isinstance(payload.get("lvs_lite"), dict) else {}
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

    klayout_cfg = payload.get("klayout") if isinstance(payload.get("klayout"), dict) else {}
    klayout_enabled = bool(klayout_cfg.get("enabled", True))
    klayout_settings = klayout_cfg.get("settings") if isinstance(klayout_cfg.get("settings"), dict) else {}
    klayout_step: dict[str, Any] = {"status": "skipped", "run_id": None, "note": "optional"}
    if klayout_enabled:
        # Determine whether a GDS exists in the layout build run.
        try:
            layout_dir = run_store.run_dir_for_id(layout_run_id)
            layout_manifest = run_store.read_run_manifest(layout_dir) or {}
            layout_artifacts = layout_manifest.get("artifacts") if isinstance(layout_manifest.get("artifacts"), dict) else {}
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
                    "run_id": k_res.get("run_id"),
                    "artifact_relpaths": k_res.get("artifact_relpaths"),
                }
            except HTTPException as exc:
                # Optional seam: do not fail workflow on KLayout errors.
                klayout_step = {"status": "error", "run_id": None, "error": str(getattr(exc, "detail", None) or exc)}
            except Exception as exc:
                klayout_step = {"status": "error", "run_id": None, "error": str(exc)}
        else:
            klayout_step = {"status": "skipped", "run_id": None, "reason": "layout did not emit a .gds artifact"}

    spice_cfg = payload.get("spice") if isinstance(payload.get("spice"), dict) else {}
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
    generated_at = datetime.now(timezone.utc).isoformat()
    replayed_from_run_id = str(payload.get("replayed_from_run_id", "")).strip() or None

    # Record the request payload snapshot to enable replay and offline review.
    request_rel = "workflow_request.json"
    try:
        request_snapshot = json.loads(json.dumps(payload))
    except Exception:
        request_snapshot = {}
    if not isinstance(request_snapshot, dict):
        request_snapshot = {}
    request_snapshot.pop("output_root", None)
    request_snapshot["project_id"] = project_id
    if isinstance(request_snapshot.get("invdesign"), dict):
        request_snapshot["invdesign"]["kind"] = inv_kind
    (Path(run_dir) / request_rel).write_text(json.dumps(request_snapshot, indent=2), encoding="utf-8")

    lvs_pass = bool(((lvs_res.get("report") or {}).get("summary") or {}).get("pass")) if isinstance(lvs_res, dict) else False
    overall_status = "pass" if lvs_pass else "fail"

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
                "run_id": inv_res.get("run_id"),
                "kind": (inv_res.get("report") or {}).get("kind") if isinstance(inv_res, dict) else None,
                "artifact_relpaths": inv_res.get("artifact_relpaths") if isinstance(inv_res, dict) else None,
            },
            "layout_build": {
                "run_id": layout_res.get("run_id"),
                "artifact_relpaths": layout_res.get("artifact_relpaths") if isinstance(layout_res, dict) else None,
            },
            "lvs_lite": {
                "run_id": lvs_res.get("run_id") if isinstance(lvs_res, dict) else None,
                "pass": bool(lvs_pass),
                "artifact_relpaths": lvs_res.get("artifact_relpaths") if isinstance(lvs_res, dict) else None,
            },
            "klayout_pack": klayout_step,
            "spice_export": {
                "run_id": spice_res.get("run_id") if isinstance(spice_res, dict) else None,
                "artifact_relpaths": spice_res.get("artifact_relpaths") if isinstance(spice_res, dict) else None,
            },
        },
        "summary": {
            "status": overall_status,
        },
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    if replayed_from_run_id:
        report["inputs"]["replayed_from_run_id"] = str(replayed_from_run_id)
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")

    outputs_summary = {
        "pic_workflow": {
            "kind": "pic.workflow.invdesign_chain",
            "status": overall_status,
            "invdesign_kind": inv_kind,
            "invdesign_run_id": inv_res.get("run_id"),
            "layout_run_id": layout_res.get("run_id"),
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
            "replayed_from_run_id": str(replayed_from_run_id) if replayed_from_run_id else None,
        },
        "outputs_summary": outputs_summary,
        "artifacts": {"workflow_report_json": report_rel, "workflow_request_json": request_rel},
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
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
        "provenance": report.get("provenance"),
    }


@app.post("/v0/pic/workflow/invdesign_chain/replay")
def pic_workflow_invdesign_chain_replay(request: Request, payload: dict = Body(...)) -> dict[str, Any]:
    """Replay a prior workflow run from its recorded request snapshot."""

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object payload")

    workflow_run_id = str(payload.get("workflow_run_id", "")).strip()
    if not workflow_run_id:
        raise HTTPException(status_code=400, detail="workflow_run_id is required")
    try:
        workflow_run_id = run_store.validate_run_id(workflow_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        src_dir = run_store.run_dir_for_id(workflow_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not src_dir.exists():
        raise HTTPException(status_code=404, detail="workflow run not found")

    src_manifest = run_store.read_run_manifest(src_dir) or runs_get(workflow_run_id, request)
    if not isinstance(src_manifest, dict) or str(src_manifest.get("run_type", "")).strip() != "pic_workflow_invdesign_chain":
        raise HTTPException(status_code=400, detail="run_id is not a pic_workflow_invdesign_chain workflow run")

    req_path = src_dir / "workflow_request.json"
    if not req_path.exists() or not req_path.is_file():
        raise HTTPException(status_code=400, detail="workflow run does not contain workflow_request.json (cannot replay)")
    try:
        request = json.loads(req_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read workflow_request.json: {exc}") from exc
    if not isinstance(request, dict):
        raise HTTPException(status_code=400, detail="workflow_request.json must be a JSON object")

    # Optional project override.
    if payload.get("project_id") is not None:
        raw = str(payload.get("project_id", "")).strip()
        if raw:
            try:
                request["project_id"] = project_store.validate_project_id(raw)
            except Exception as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

    request["replayed_from_run_id"] = workflow_run_id
    res = pic_workflow_invdesign_chain(request)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "replayed_from_run_id": workflow_run_id,
        "workflow": res,
    }


@app.post("/v0/pic/layout/build")
def pic_layout_build(payload: dict = Body(...)) -> dict[str, Any]:
    """Build deterministic PIC layout artifacts (ports/routes/provenance, optional GDS)."""

    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    execution_mode = _parse_execution_mode(payload)
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc).isoformat()
    report_rel = "layout_build_report.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")

    pdk_manifest = _resolve_run_pdk_manifest(
        pdk_request=pdk_req,
        execution_mode=execution_mode,
        require_context_in_cert=False,
    )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(status_code=400, detail="failed to resolve pdk_manifest for layout build run")
    pdk_manifest_rel = _write_pdk_manifest_artifact(run_dir, pdk_manifest)

    artifacts = dict(report.get("artifacts", {}) or {})
    ports_rel = str(artifacts.get("ports_json_path") or "ports.json")
    routes_rel = str(artifacts.get("routes_json_path") or "routes.json")
    prov_rel = str(artifacts.get("layout_provenance_json_path") or "layout_provenance.json")
    gds_rel = artifacts.get("layout_gds_path")

    outputs_summary = {
        "pic_layout": {
            "nodes": (report.get("summary", {}) or {}).get("nodes"),
            "edges": (report.get("summary", {}) or {}).get("edges"),
            "ports": (report.get("summary", {}) or {}).get("ports"),
            "routes": (report.get("summary", {}) or {}).get("routes"),
            "gds_emitted": (report.get("summary", {}) or {}).get("gds_emitted"),
            "pdk": (report.get("pdk", {}) or {}).get("name"),
        }
    }

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
        "outputs_summary": outputs_summary,
        "artifacts": {
            "layout_build_report_json": report_rel,
            "ports_json": ports_rel,
            "routes_json": routes_rel,
            "layout_provenance_json": prov_rel,
            "layout_gds": gds_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/layout/lvs_lite")
def pic_layout_lvs_lite(payload: dict = Body(...)) -> dict[str, Any]:
    """Run PIC LVS-lite against a graph and layout sidecars (ports/routes)."""

    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    require_schema = bool(payload.get("require_schema", False))
    execution_mode = _parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    ports = payload.get("ports")
    routes = payload.get("routes")
    layout_run_id = str(payload.get("layout_run_id", "")).strip()
    layout_dir: Path | None = None
    if layout_run_id:
        try:
            layout_dir = run_store.run_dir_for_id(layout_run_id)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
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
            raise HTTPException(status_code=400, detail=f"Failed to read layout sidecars from run {layout_run_id}: {exc}") from exc

    if not isinstance(ports, dict) or not isinstance(routes, dict):
        raise HTTPException(status_code=400, detail="Provide ports/routes objects or layout_run_id")

    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    signoff_bundle = payload.get("signoff_bundle") if isinstance(payload.get("signoff_bundle"), dict) else None

    pdk_manifest = _resolve_run_pdk_manifest(
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

    try:
        request_payload: dict[str, Any] = {
            "graph": graph,
            "ports": ports,
            "routes": routes,
            "settings": settings,
        }
        if isinstance(signoff_bundle, dict):
            request_payload["signoff_bundle"] = signoff_bundle
        report = run_pic_lvs_lite(
            request_payload,
            require_schema=require_schema,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc).isoformat()
    report_rel = "lvs_lite_report.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")
    pdk_manifest_rel = _write_pdk_manifest_artifact(run_dir, pdk_manifest)

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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/layout/klayout/run")
def pic_layout_klayout_run(payload: dict = Body(...)) -> dict[str, Any]:
    """Run the trusted KLayout macro template and capture a KLayout run artifact pack."""

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    execution_mode = _parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    layout_run_id = str(payload.get("layout_run_id", "")).strip()
    source_run_id = str(payload.get("source_run_id", "") or payload.get("run_id", "")).strip()
    if source_run_id and layout_run_id and source_run_id != layout_run_id:
        raise HTTPException(status_code=400, detail="source_run_id and layout_run_id must match when both are provided")

    ref_run_id = source_run_id or layout_run_id
    if not ref_run_id:
        raise HTTPException(status_code=400, detail="Provide source_run_id (preferred) or layout_run_id")
    try:
        ref_dir = run_store.run_dir_for_id(ref_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ref_dir.exists():
        raise HTTPException(status_code=404, detail="source_run_id not found" if source_run_id else "layout_run_id not found")

    ref_manifest = run_store.read_run_manifest(ref_dir) or {}
    declared = ref_manifest.get("artifacts") if isinstance(ref_manifest.get("artifacts"), dict) else {}

    pdk_manifest = _resolve_run_pdk_manifest(
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

    # Resolve the input GDS from the prior layout run, using safe artifact resolution.
    gds_rel = str(payload.get("gds_artifact_path", "") or "").strip() or None
    if not gds_rel:
        # 1) Canonical layout artifact key (layout build runs).
        raw = declared.get("layout_gds")
        if isinstance(raw, str) and raw.strip():
            gds_rel = str(raw).strip()
        else:
            # 2) If there is exactly one top-level GDS artifact, use it.
            candidates = []
            for _, v in declared.items():
                if isinstance(v, str) and v.strip().lower().endswith(".gds"):
                    candidates.append(str(v).strip())
            candidates = sorted(set(candidates), key=lambda s: s.lower())
            if len(candidates) == 1:
                gds_rel = candidates[0]

        # 3) Best-effort fallback for older/manual runs: layout.gds present in dir.
        if not gds_rel:
            if (ref_dir / "layout.gds").exists():
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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    # Default KLayout settings from the source layout build run when available.
    # This keeps DRC-lite thresholds and layer conventions consistent with the PDK
    # and layout settings that produced the GDS.
    try:
        merged_settings: dict[str, Any] = dict(settings or {})
        if "layout_build_report_json" in declared and isinstance(declared.get("layout_build_report_json"), str):
            rep_rel = str(declared.get("layout_build_report_json") or "").strip()
            if rep_rel:
                rep_path = run_store.resolve_artifact_path(ref_dir, rep_rel)
                rep = json.loads(rep_path.read_text(encoding="utf-8"))
                if isinstance(rep, dict):
                    rep_settings = rep.get("settings") if isinstance(rep.get("settings"), dict) else {}
                    rep_pdk = rep.get("pdk") if isinstance(rep.get("pdk"), dict) else {}
                    rep_rules = rep_pdk.get("design_rules") if isinstance(rep_pdk.get("design_rules"), dict) else {}

                    if "min_waveguide_width_um" not in merged_settings and rep_rules.get("min_waveguide_width_um") is not None:
                        merged_settings["min_waveguide_width_um"] = float(rep_rules.get("min_waveguide_width_um"))

                    if "waveguide_layer" not in merged_settings and isinstance(rep_settings.get("waveguide_layer"), dict):
                        merged_settings["waveguide_layer"] = rep_settings.get("waveguide_layer")
                    if "label_layer" not in merged_settings and isinstance(rep_settings.get("label_layer"), dict):
                        merged_settings["label_layer"] = rep_settings.get("label_layer")
                    if "label_prefix" not in merged_settings and rep_settings.get("label_prefix") is not None:
                        merged_settings["label_prefix"] = str(rep_settings.get("label_prefix") or "").strip() or None

                    # `cell_name` is the layout builder setting; macro expects `top_cell`.
                    if "top_cell" not in merged_settings:
                        cell_name = str(rep_settings.get("cell_name") or "").strip()
                        if cell_name:
                            merged_settings["top_cell"] = cell_name
        settings = merged_settings
    except Exception:
        # Best-effort only: fall back to provided settings.
        settings = dict(settings or {})

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
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc).isoformat()
    pdk_manifest_rel = _write_pdk_manifest_artifact(run_dir, pdk_manifest)

    # Artifact filenames produced by the wrapper (deterministic).
    pack_rel = "klayout_run_artifact_pack.json"
    stdout_rel = "klayout_stdout.txt"
    stderr_rel = "klayout_stderr.txt"
    outputs = pack.get("outputs") if isinstance(pack, dict) else None
    if not isinstance(outputs, dict):
        outputs = {}

    outputs_summary = {
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
    }

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
        "outputs_summary": outputs_summary,
        "artifacts": artifacts,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "pack": pack,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": artifacts,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/layout/foundry_drc/run")
def pic_layout_foundry_drc_run(payload: dict = Body(...)) -> dict[str, Any]:
    """Run metadata-only sealed foundry DRC seam (mockable, no deck leakage)."""

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    execution_mode = _parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    layout_run_id = str(payload.get("layout_run_id", "")).strip()
    source_run_id = str(payload.get("source_run_id", "") or payload.get("run_id", "")).strip()
    if source_run_id and layout_run_id and source_run_id != layout_run_id:
        raise HTTPException(status_code=400, detail="source_run_id and layout_run_id must match when both are provided")

    ref_run_id = source_run_id or layout_run_id
    if not ref_run_id:
        raise HTTPException(status_code=400, detail="Provide source_run_id (preferred) or layout_run_id")

    try:
        ref_dir = run_store.run_dir_for_id(ref_run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ref_dir.exists():
        raise HTTPException(status_code=404, detail="source_run_id not found" if source_run_id else "layout_run_id not found")

    pdk_manifest = _resolve_run_pdk_manifest(
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

    sealed_request: dict[str, Any] = {}
    if isinstance(payload.get("backend"), str) and str(payload.get("backend") or "").strip():
        sealed_request["backend"] = str(payload.get("backend")).strip()
    if isinstance(payload.get("run_id"), str) and str(payload.get("run_id") or "").strip():
        sealed_request["run_id"] = str(payload.get("run_id")).strip()
    if payload.get("deck_fingerprint") is not None:
        sealed_request["deck_fingerprint"] = str(payload.get("deck_fingerprint"))
    if isinstance(payload.get("mock_result"), dict):
        sealed_request["mock_result"] = payload.get("mock_result")

    try:
        summary = run_foundry_drc_sealed(sealed_request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    generated_at = datetime.now(timezone.utc).isoformat()
    summary_rel = "foundry_drc_sealed_summary.json"
    (Path(run_dir) / summary_rel).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    pdk_manifest_rel = _write_pdk_manifest_artifact(run_dir, pdk_manifest)

    counts = summary.get("check_counts") if isinstance(summary.get("check_counts"), dict) else {}
    outputs_summary = {
        "pic_foundry_drc_sealed": {
            "status": summary.get("status"),
            "execution_backend": summary.get("execution_backend"),
            "failed_checks": counts.get("failed"),
            "errored_checks": counts.get("errored"),
            "source_run_id": ref_run_id,
            "layout_run_id": layout_run_id or None,
        }
    }

    artifacts = {
        "foundry_drc_sealed_summary_json": summary_rel,
        "pdk_manifest_json": pdk_manifest_rel,
    }

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "pic_foundry_drc_sealed",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "source_run_id": ref_run_id,
            "layout_run_id": layout_run_id or None,
            "execution_mode": execution_mode,
            "pdk": ((pdk_manifest.get("pdk") or {}).get("name") if isinstance(pdk_manifest, dict) else None),
            "deck_fingerprint": summary.get("deck_fingerprint"),
        },
        "outputs_summary": outputs_summary,
        "artifacts": artifacts,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "output_dir": str(run_dir),
        "summary": summary,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": artifacts,
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/pic/spice/export")
def pic_spice_export(payload: dict = Body(...)) -> dict[str, Any]:
    """Export a PIC graph to a deterministic SPICE-like netlist + mapping artifacts."""

    graph = payload.get("graph") if isinstance(payload, dict) else None
    if not isinstance(graph, dict):
        graph = payload
    if not isinstance(graph, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for graph payload")

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    require_schema = bool(payload.get("require_schema", False))

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    Path(run_dir).mkdir(parents=True, exist_ok=True)

    try:
        report = export_pic_graph_to_spice_artifacts(
            {
                "graph": graph,
                "settings": payload.get("settings") if isinstance(payload.get("settings"), dict) else None,
            },
            run_dir,
            require_schema=require_schema,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc).isoformat()
    report_rel = "spice_export_report.json"
    (Path(run_dir) / report_rel).write_text(json.dumps(report, indent=2), encoding="utf-8")

    artifacts = dict(report.get("artifacts", {}) or {})
    netlist_rel = str(artifacts.get("netlist_path") or "netlist.sp")
    map_rel = str(artifacts.get("spice_map_path") or "spice_map.json")
    prov_rel = str(artifacts.get("spice_provenance_path") or "spice_provenance.json")

    outputs_summary = {"pic_spice_export": dict(report.get("summary", {}) or {})}

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "pic_spice_export",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "graph_hash": hash_dict(graph),
            "settings_hash": hash_dict(payload.get("settings") if isinstance(payload.get("settings"), dict) else {}),
        },
        "outputs_summary": outputs_summary,
        "artifacts": {
            "spice_export_report_json": report_rel,
            "netlist_sp": netlist_rel,
            "spice_map_json": map_rel,
            "spice_provenance_json": prov_rel,
        },
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }


@app.post("/v0/performance_drc/crosstalk")
def performance_drc_crosstalk(payload: dict = Body(...)) -> dict[str, Any]:
    """Run a performance DRC crosstalk check (dev API)."""

    if str(payload.get("output_root", "")).strip():
        raise HTTPException(
            status_code=400,
            detail="output_root override is disabled for API runs; set PHOTONTRUST_API_RUNS_ROOT instead",
        )
    try:
        project_id = project_store.validate_project_id(payload.get("project_id", "default"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    execution_mode = _parse_execution_mode(payload)
    pdk_req = payload.get("pdk") if isinstance(payload.get("pdk"), dict) else None

    pdk_manifest = None
    if isinstance(payload.get("pdk_manifest"), dict):
        pdk_manifest = _coerce_pdk_manifest_payload(
            payload.get("pdk_manifest"),
            execution_mode=execution_mode,
        )
    if not isinstance(pdk_manifest, dict):
        pdk_manifest = _resolve_run_pdk_manifest(
            pdk_request=pdk_req,
            execution_mode=execution_mode,
            require_context_in_cert=True,
        )
    if not isinstance(pdk_manifest, dict):
        raise HTTPException(
            status_code=400,
            detail="certification mode requires explicit pdk manifest context (provide payload.pdk or payload.pdk_manifest)",
        )

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)

    try:
        report = run_parallel_waveguide_crosstalk_check(payload, output_dir=run_dir, run_id=run_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = datetime.now(timezone.utc).isoformat()
    report_json_rel = "performance_drc_report.json"
    report_html_rel = "performance_drc_report.html"
    pdk_manifest_rel = _write_pdk_manifest_artifact(run_dir, pdk_manifest)

    drc_results = report.get("results") if isinstance(report.get("results"), dict) else {}
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
            "pdk": ((pdk_manifest.get("pdk") or {}).get("name") if isinstance(pdk_manifest, dict) else None),
            "check_kind": (report.get("check", {}) or {}).get("kind"),
            "input_hash": (report.get("provenance", {}) or {}).get("input_hash"),
            "model_hash": (report.get("provenance", {}) or {}).get("model_hash"),
        },
        "outputs_summary": outputs_summary,
        "artifacts": {
            "performance_drc_report_json": report_json_rel,
            "performance_drc_report_html": report_html_rel,
            "pdk_manifest_json": pdk_manifest_rel,
        },
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
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
        "provenance": {
            "photonstrust_version": app.version,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
