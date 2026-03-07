"""Metrics summary routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, Request

from photonstrust.api import foundry_metrics as foundry_metrics_store
from photonstrust.api.auth import require_roles
from photonstrust.api.runtime import generated_at_utc, runtime_provenance


router = APIRouter()


@router.get("/v0/metrics/foundry/summary")
def foundry_metrics_summary(request: Request, limit: int = Query(200, ge=1, le=5000)) -> dict[str, Any]:
    require_roles(request, "viewer", "runner", "approver")
    events = foundry_metrics_store.read_foundry_metric_events(limit=int(limit))
    summary = foundry_metrics_store.aggregate_foundry_metrics(events)
    return {
        "generated_at": generated_at_utc(),
        "limit": int(limit),
        "event_count": len(events),
        "summary": summary,
        "provenance": runtime_provenance(),
    }
