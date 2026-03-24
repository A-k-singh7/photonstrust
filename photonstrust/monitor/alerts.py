"""Alert engine for QKD link metric threshold evaluation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from photonstrust.monitor.store import TimeSeriesStore
from photonstrust.monitor.types import AlertEvent, AlertRule


class AlertEngine:
    """Evaluates alert rules against current metric values."""

    def __init__(self, rules: list[AlertRule]) -> None:
        self._rules = list(rules)

    def evaluate(self, store: TimeSeriesStore, link_id: str) -> list[AlertEvent]:
        """Evaluate all rules for a given link, returning triggered alerts."""
        events: list[AlertEvent] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        for rule in self._rules:
            latest = store.latest(link_id, rule.metric_name)
            if latest is None:
                continue

            if self.check_condition(latest.value, rule.condition, rule.threshold):
                event = AlertEvent(
                    alert_id=str(uuid.uuid4()),
                    rule_id=rule.rule_id,
                    link_id=link_id,
                    triggered_at_iso=now_iso,
                    metric_name=rule.metric_name,
                    metric_value=latest.value,
                    threshold=rule.threshold,
                    severity=rule.severity,
                    message=(
                        f"{rule.metric_name} = {latest.value} "
                        f"{rule.condition} {rule.threshold} on link {link_id}"
                    ),
                )
                events.append(event)

        return events

    @staticmethod
    def check_condition(value: float, condition: str, threshold: float) -> bool:
        """Check whether *value* satisfies *condition* against *threshold*."""
        if condition == "gt":
            return value > threshold
        if condition == "lt":
            return value < threshold
        if condition == "gte":
            return value >= threshold
        if condition == "lte":
            return value <= threshold
        if condition == "eq":
            return value == threshold
        raise ValueError(f"Unknown condition: {condition!r}")
