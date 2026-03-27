"""In-process event bus for the integration hub."""

from __future__ import annotations

from typing import Callable

from photonstrust.integrations.types import WebhookEvent


class EventBus:
    """Simple synchronous publish/subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable]] = {}
        self._event_log: list[WebhookEvent] = []

    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Register *callback* for events of *event_type* (use ``"*"`` for all)."""
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event: WebhookEvent) -> None:
        """Publish an event to all matching subscribers."""
        self._event_log.append(event)
        for cb in self._subscribers.get(event.event_type, []):
            cb(event)
        # Wildcard subscribers receive every event
        for cb in self._subscribers.get("*", []):
            cb(event)

    def event_log(self) -> list[WebhookEvent]:
        """Return a copy of the full event log."""
        return list(self._event_log)
