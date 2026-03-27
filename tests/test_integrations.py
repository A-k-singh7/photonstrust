"""Tests for integration hub & webhooks (Feature 15)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.integrations.delivery import compute_signature, deliver_webhook
from photonstrust.integrations.events import EventBus
from photonstrust.integrations.types import (
    DeliveryResult,
    WebhookConfig,
    WebhookEvent,
)
from photonstrust.integrations.webhooks import WebhookManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(event_type: str = "run.completed") -> WebhookEvent:
    return WebhookEvent(
        event_id="evt-001",
        event_type=event_type,
        timestamp_iso="2025-01-01T00:00:00Z",
        payload={"key": "value"},
        source="test",
    )


def _make_config(
    webhook_id: str = "wh-1",
    url: str = "http://127.0.0.1:1/noop",
    events: tuple[str, ...] = ("run.completed",),
) -> WebhookConfig:
    return WebhookConfig(
        webhook_id=webhook_id,
        url=url,
        secret="test-secret",
        events=events,
        active=True,
        max_retries=1,
        timeout_seconds=1,
    )


# ---------------------------------------------------------------------------
# EventBus tests
# ---------------------------------------------------------------------------


def test_event_bus_publish_subscribe() -> None:
    """Subscriber should receive the published event."""
    bus = EventBus()
    received: list[WebhookEvent] = []
    bus.subscribe("run.completed", received.append)

    event = _make_event("run.completed")
    bus.publish(event)

    assert len(received) == 1
    assert received[0].event_id == "evt-001"


def test_event_bus_wildcard_subscriber() -> None:
    """A '*' subscriber should receive events of any type."""
    bus = EventBus()
    received: list[WebhookEvent] = []
    bus.subscribe("*", received.append)

    bus.publish(_make_event("run.completed"))
    bus.publish(_make_event("alert.fired"))

    assert len(received) == 2


# ---------------------------------------------------------------------------
# Webhook config tests
# ---------------------------------------------------------------------------


def test_webhook_config_serialization() -> None:
    """WebhookConfig.as_dict() should round-trip through JSON."""
    config = _make_config()
    d = config.as_dict()
    assert isinstance(d, dict)
    # Round-trip: dict -> JSON -> dict -> WebhookConfig
    raw = json.loads(json.dumps(d))
    raw["events"] = tuple(raw["events"])
    restored = WebhookConfig(**raw)
    assert restored.webhook_id == config.webhook_id
    assert restored.url == config.url


# ---------------------------------------------------------------------------
# HMAC signature tests
# ---------------------------------------------------------------------------


def test_hmac_signature_computation() -> None:
    """compute_signature should return a 64-char hex string (SHA-256)."""
    sig = compute_signature("secret", b'{"test": true}')
    assert isinstance(sig, str)
    assert len(sig) == 64
    # Must be valid hex
    int(sig, 16)


# ---------------------------------------------------------------------------
# WebhookManager tests
# ---------------------------------------------------------------------------


def test_webhook_manager_register_unregister() -> None:
    """Register then unregister should succeed and reflect in list."""
    mgr = WebhookManager()
    config = _make_config()
    mgr.register(config)
    assert len(mgr.list_webhooks()) == 1

    assert mgr.unregister("wh-1") is True
    assert len(mgr.list_webhooks()) == 0

    # Unregistering again should return False
    assert mgr.unregister("wh-1") is False


def test_webhook_dispatch_matches_event_type() -> None:
    """Only webhooks subscribed to the event type should be dispatched."""
    mgr = WebhookManager()
    # wh-match listens for run.completed, wh-miss listens for alert.fired
    mgr.register(_make_config("wh-match", events=("run.completed",)))
    mgr.register(_make_config("wh-miss", events=("alert.fired",)))

    event = _make_event("run.completed")
    results = mgr.dispatch(event)

    # Only wh-match should fire (delivery may fail due to bad URL, but it
    # should still attempt delivery)
    assert len(results) == 1
    assert results[0].webhook_id == "wh-match"


def test_delivery_result_on_failure() -> None:
    """Delivering to an invalid URL should yield delivered=False."""
    config = _make_config(url="http://127.0.0.1:1/noop")
    event = _make_event()
    result = deliver_webhook(config, event)
    assert isinstance(result, DeliveryResult)
    assert result.delivered is False
    assert len(result.attempts) >= 1
    assert result.attempts[0].success is False


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


def test_webhook_config_persistence(tmp_path: Path) -> None:
    """Webhooks should survive a save/load cycle."""
    cfg_path = tmp_path / "webhooks.json"

    mgr1 = WebhookManager()
    mgr1.register(_make_config("wh-a", events=("run.completed", "alert.fired")))
    mgr1.register(_make_config("wh-b", events=("*",)))
    mgr1.save_config(cfg_path)

    mgr2 = WebhookManager(config_path=cfg_path)
    loaded = {wh.webhook_id: wh for wh in mgr2.list_webhooks()}
    assert "wh-a" in loaded
    assert "wh-b" in loaded
    assert "run.completed" in loaded["wh-a"].events


# ---------------------------------------------------------------------------
# Event log tests
# ---------------------------------------------------------------------------


def test_event_log_records_events() -> None:
    """EventBus.event_log() should record all published events."""
    bus = EventBus()
    bus.publish(_make_event("run.completed"))
    bus.publish(_make_event("alert.fired"))
    bus.publish(_make_event("sla.breached"))

    log = bus.event_log()
    assert len(log) == 3
    types = [e.event_type for e in log]
    assert "run.completed" in types
    assert "alert.fired" in types
    assert "sla.breached" in types
