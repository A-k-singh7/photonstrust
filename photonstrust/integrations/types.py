"""Data types for the integration hub and webhook system."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class WebhookConfig:
    """Configuration for a registered webhook."""

    webhook_id: str
    url: str
    secret: str
    events: tuple[str, ...]
    active: bool = True
    max_retries: int = 3
    timeout_seconds: int = 10

    def as_dict(self) -> dict:
        return {
            "webhook_id": self.webhook_id,
            "url": self.url,
            "secret": self.secret,
            "events": list(self.events),
            "active": self.active,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass(frozen=True)
class WebhookEvent:
    """An event to be delivered via webhooks."""

    event_id: str
    event_type: str
    timestamp_iso: str
    payload: dict = field(default_factory=dict)
    source: str = ""

    def as_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp_iso": self.timestamp_iso,
            "payload": dict(self.payload),
            "source": self.source,
        }


@dataclass(frozen=True)
class DeliveryAttempt:
    """A single webhook delivery attempt."""

    attempt_number: int
    timestamp_iso: str
    status_code: int | None
    success: bool
    error: str | None

    def as_dict(self) -> dict:
        return {
            "attempt_number": self.attempt_number,
            "timestamp_iso": self.timestamp_iso,
            "status_code": self.status_code,
            "success": self.success,
            "error": self.error,
        }


@dataclass(frozen=True)
class DeliveryResult:
    """Result of attempting to deliver an event to a webhook."""

    webhook_id: str
    event_id: str
    delivered: bool
    attempts: list[DeliveryAttempt] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "webhook_id": self.webhook_id,
            "event_id": self.event_id,
            "delivered": self.delivered,
            "attempts": [a.as_dict() for a in self.attempts],
        }
