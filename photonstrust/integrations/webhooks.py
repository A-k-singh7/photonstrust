"""Webhook registration, dispatch and persistence."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.integrations.delivery import deliver_webhook
from photonstrust.integrations.types import (
    DeliveryResult,
    WebhookConfig,
    WebhookEvent,
)


class WebhookManager:
    """Central manager for webhook lifecycle and dispatch."""

    def __init__(self, config_path: Path | None = None) -> None:
        self._webhooks: dict[str, WebhookConfig] = {}
        self._delivery_log: list[DeliveryResult] = []
        if config_path and Path(config_path).exists():
            self._load(Path(config_path))

    def register(self, config: WebhookConfig) -> None:
        """Register (or update) a webhook."""
        self._webhooks[config.webhook_id] = config

    def unregister(self, webhook_id: str) -> bool:
        """Remove a webhook. Returns ``True`` if it existed."""
        return self._webhooks.pop(webhook_id, None) is not None

    def list_webhooks(self) -> list[WebhookConfig]:
        """Return all registered webhooks."""
        return list(self._webhooks.values())

    def dispatch(self, event: WebhookEvent) -> list[DeliveryResult]:
        """Deliver *event* to all matching active webhooks."""
        results: list[DeliveryResult] = []
        for wh in self._webhooks.values():
            if not wh.active:
                continue
            if event.event_type in wh.events or "*" in wh.events:
                result = deliver_webhook(wh, event)
                self._delivery_log.append(result)
                results.append(result)
        return results

    def delivery_log(self) -> list[DeliveryResult]:
        """Return a copy of all delivery results."""
        return list(self._delivery_log)

    def save_config(self, path: Path) -> None:
        """Persist webhook registrations to a JSON file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        data = [wh.as_dict() for wh in self._webhooks.values()]
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self, path: Path) -> None:
        """Load webhook registrations from a JSON file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        for wh_data in data:
            wh_data["events"] = tuple(wh_data.get("events", ()))
            self._webhooks[wh_data["webhook_id"]] = WebhookConfig(**wh_data)
