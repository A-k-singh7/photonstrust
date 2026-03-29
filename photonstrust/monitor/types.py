"""Data types for the real-time link health monitor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricPoint:
    """A single time-series metric measurement."""

    timestamp_iso: str
    metric_name: str
    value: float
    link_id: str
    tags: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "timestamp_iso": self.timestamp_iso,
            "metric_name": self.metric_name,
            "value": self.value,
            "link_id": self.link_id,
            "tags": dict(self.tags),
        }


@dataclass(frozen=True)
class AlertRule:
    """A rule that triggers an alert when a metric crosses a threshold."""

    rule_id: str
    metric_name: str
    condition: str  # "gt", "lt", "gte", "lte", "eq"
    threshold: float
    window_seconds: int
    severity: str

    def as_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "metric_name": self.metric_name,
            "condition": self.condition,
            "threshold": self.threshold,
            "window_seconds": self.window_seconds,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class AlertEvent:
    """An alert that was triggered by a rule evaluation."""

    alert_id: str
    rule_id: str
    link_id: str
    triggered_at_iso: str
    metric_name: str
    metric_value: float
    threshold: float
    severity: str
    message: str

    def as_dict(self) -> dict:
        return {
            "alert_id": self.alert_id,
            "rule_id": self.rule_id,
            "link_id": self.link_id,
            "triggered_at_iso": self.triggered_at_iso,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(frozen=True)
class SLADefinition:
    """Service-level agreement definition for a QKD metric."""

    sla_id: str
    name: str
    metric_name: str
    target_value: float
    condition: str  # "gt", "lt", "gte", "lte", "eq"
    measurement_window_hours: int
    minimum_uptime_fraction: float

    def as_dict(self) -> dict:
        return {
            "sla_id": self.sla_id,
            "name": self.name,
            "metric_name": self.metric_name,
            "target_value": self.target_value,
            "condition": self.condition,
            "measurement_window_hours": self.measurement_window_hours,
            "minimum_uptime_fraction": self.minimum_uptime_fraction,
        }


@dataclass(frozen=True)
class SLAComplianceResult:
    """Result of checking a link against an SLA definition."""

    sla_id: str
    link_id: str
    period_start_iso: str
    period_end_iso: str
    compliant: bool
    actual_value: float
    target_value: float
    uptime_fraction: float
    violations: int

    def as_dict(self) -> dict:
        return {
            "sla_id": self.sla_id,
            "link_id": self.link_id,
            "period_start_iso": self.period_start_iso,
            "period_end_iso": self.period_end_iso,
            "compliant": self.compliant,
            "actual_value": self.actual_value,
            "target_value": self.target_value,
            "uptime_fraction": self.uptime_fraction,
            "violations": self.violations,
        }


@dataclass(frozen=True)
class HealthScore:
    """Composite health score for a QKD link."""

    link_id: str
    score: float
    timestamp_iso: str
    components: dict = field(default_factory=dict)
    status: str = "unknown"  # "healthy", "degraded", "critical", "unknown"

    def as_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "score": self.score,
            "timestamp_iso": self.timestamp_iso,
            "components": dict(self.components),
            "status": self.status,
        }


@dataclass(frozen=True)
class LinkHealthReport:
    """Full health report for a single QKD link."""

    link_id: str
    health: HealthScore
    active_alerts: list[AlertEvent] = field(default_factory=list)
    sla_compliance: list[SLAComplianceResult] = field(default_factory=list)
    trend: str = "unknown"  # "improving", "stable", "degrading", "unknown"

    def as_dict(self) -> dict:
        return {
            "link_id": self.link_id,
            "health": self.health.as_dict(),
            "active_alerts": [a.as_dict() for a in self.active_alerts],
            "sla_compliance": [s.as_dict() for s in self.sla_compliance],
            "trend": self.trend,
        }


@dataclass(frozen=True)
class NetworkHealthReport:
    """Aggregated health report for the entire QKD network."""

    timestamp_iso: str
    link_reports: list[LinkHealthReport] = field(default_factory=list)
    overall_score: float = 0.0
    overall_status: str = "unknown"
    weakest_link_id: str = ""
    active_alert_count: int = 0

    def as_dict(self) -> dict:
        return {
            "timestamp_iso": self.timestamp_iso,
            "link_reports": [r.as_dict() for r in self.link_reports],
            "overall_score": self.overall_score,
            "overall_status": self.overall_status,
            "weakest_link_id": self.weakest_link_id,
            "active_alert_count": self.active_alert_count,
        }
