"""UI telemetry routes."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from photonstrust.api import ui_metrics as ui_metrics_store
from photonstrust.api.auth import enforce_project_scope_or_403, require_roles
from photonstrust.api.common import normalize_utc_timestamp
from photonstrust.api.common import project_id_or_400
from photonstrust.api.runtime import generated_at_utc, runtime_provenance


router = APIRouter()

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
    "newcomer_flow_entered",
    "newcomer_step_completed",
    "newcomer_flow_completed",
    "newcomer_flow_exited",
}
_UI_TELEMETRY_USER_MODES = {"builder", "reviewer", "exec"}
_UI_TELEMETRY_PROFILES = {"qkd_link", "pic_circuit", "orbit"}
_UI_TELEMETRY_OUTCOMES = {"success", "failure", "abandoned"}
_UI_TELEMETRY_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


@router.post("/v0/ui/telemetry/events")
def ui_telemetry_events_ingest(request: Request, payload: dict = Body(...)) -> dict[str, Any]:
    ctx = require_roles(request, "runner", "approver")
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

    timestamp_utc = normalize_utc_timestamp(payload.get("timestamp_utc"), field_name="timestamp_utc")
    project_id = project_id_or_400(payload)
    enforce_project_scope_or_403(ctx, project_id)

    event = {
        "schema_version": "0.1",
        "kind": "photonstrust.ui_metric_event",
        "event_id": uuid.uuid4().hex[:12],
        "event_name": event_name,
        "timestamp_utc": timestamp_utc,
        "ingested_at": generated_at_utc(),
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
        "generated_at": generated_at_utc(),
        "accepted": True,
        "path": str(out_path),
        "event": event,
        "provenance": runtime_provenance(),
    }
