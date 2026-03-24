"""API routes for the integration hub and webhook system."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from photonstrust.integrations.types import WebhookConfig, WebhookEvent
from photonstrust.integrations.webhooks import WebhookManager

router = APIRouter(prefix="/v1/integrations", tags=["integrations"])

# Module-level singleton for the webhook manager
_manager = WebhookManager()

_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "integrations" / "data" / "event_catalog.json"


@router.post("/webhooks")
def register_webhook(payload: dict) -> dict:
    """Register a new webhook."""
    try:
        config = WebhookConfig(
            webhook_id=payload["webhook_id"],
            url=payload["url"],
            secret=payload["secret"],
            events=tuple(payload.get("events", ())),
            active=payload.get("active", True),
            max_retries=int(payload.get("max_retries", 3)),
            timeout_seconds=int(payload.get("timeout_seconds", 10)),
        )
        _manager.register(config)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"status": "ok", "webhook": config.as_dict()}


@router.get("/webhooks")
def list_webhooks() -> dict:
    """List all registered webhooks."""
    return {"webhooks": [wh.as_dict() for wh in _manager.list_webhooks()]}


@router.delete("/webhooks/{webhook_id}")
def unregister_webhook(webhook_id: str) -> dict:
    """Unregister a webhook."""
    removed = _manager.unregister(webhook_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"status": "ok", "webhook_id": webhook_id}


@router.get("/events")
def list_event_types() -> dict:
    """List available event types from the catalog."""
    if _CATALOG_PATH.exists():
        data = json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))
        return {"events": data.get("events", {})}
    return {"events": {}}


@router.get("/deliveries")
def list_deliveries() -> dict:
    """List all delivery results."""
    return {
        "deliveries": [d.as_dict() for d in _manager.delivery_log()],
    }


@router.post("/test/{webhook_id}")
def test_webhook(webhook_id: str) -> dict:
    """Send a test event to a specific webhook."""
    from datetime import datetime, timezone

    webhooks = {wh.webhook_id: wh for wh in _manager.list_webhooks()}
    if webhook_id not in webhooks:
        raise HTTPException(status_code=404, detail="Webhook not found")

    event = WebhookEvent(
        event_id="test-event",
        event_type="test.ping",
        timestamp_iso=datetime.now(timezone.utc).isoformat(),
        payload={"message": "test ping"},
        source="api",
    )
    from photonstrust.integrations.delivery import deliver_webhook

    result = deliver_webhook(webhooks[webhook_id], event)
    return {"status": "ok", "result": result.as_dict()}
