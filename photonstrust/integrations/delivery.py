"""Webhook delivery with HMAC signing and retry logic."""

from __future__ import annotations

import hashlib
import hmac
import json
import urllib.request
from datetime import datetime, timezone

from photonstrust.integrations.types import (
    DeliveryAttempt,
    DeliveryResult,
    WebhookConfig,
    WebhookEvent,
)


def compute_signature(secret: str, payload_bytes: bytes) -> str:
    """Compute HMAC-SHA256 signature for webhook payload."""
    return hmac.new(
        secret.encode("utf-8"), payload_bytes, hashlib.sha256
    ).hexdigest()


def deliver_webhook(
    config: WebhookConfig, event: WebhookEvent
) -> DeliveryResult:
    """Attempt to deliver *event* to the webhook described by *config*."""
    payload_bytes = json.dumps(event.as_dict(), sort_keys=True).encode("utf-8")
    signature = compute_signature(config.secret, payload_bytes)

    attempts: list[DeliveryAttempt] = []
    delivered = False

    for attempt_num in range(1, config.max_retries + 1):
        ts = datetime.now(timezone.utc).isoformat()
        try:
            req = urllib.request.Request(
                config.url,
                data=payload_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-PhotonTrust-Signature": signature,
                    "X-PhotonTrust-Event": event.event_type,
                },
                method="POST",
            )
            resp = urllib.request.urlopen(req, timeout=config.timeout_seconds)
            attempts.append(
                DeliveryAttempt(
                    attempt_number=attempt_num,
                    timestamp_iso=ts,
                    status_code=resp.status,
                    success=True,
                    error=None,
                )
            )
            delivered = True
            break
        except Exception as exc:
            attempts.append(
                DeliveryAttempt(
                    attempt_number=attempt_num,
                    timestamp_iso=ts,
                    status_code=None,
                    success=False,
                    error=str(exc),
                )
            )

    return DeliveryResult(
        webhook_id=config.webhook_id,
        event_id=event.event_id,
        delivered=delivered,
        attempts=attempts,
    )
