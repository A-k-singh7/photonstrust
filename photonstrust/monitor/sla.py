"""SLA compliance checking for QKD links."""

from __future__ import annotations

from photonstrust.monitor.alerts import AlertEngine
from photonstrust.monitor.store import TimeSeriesStore
from photonstrust.monitor.types import SLAComplianceResult, SLADefinition


def check_sla_compliance(
    store: TimeSeriesStore,
    link_id: str,
    sla: SLADefinition,
    *,
    period_start_iso: str,
    period_end_iso: str,
) -> SLAComplianceResult:
    """Check whether a link meets an SLA within a time window."""
    points = store.query(
        link_id,
        sla.metric_name,
        start_iso=period_start_iso,
        end_iso=period_end_iso,
    )

    total = len(points)
    if total == 0:
        return SLAComplianceResult(
            sla_id=sla.sla_id,
            link_id=link_id,
            period_start_iso=period_start_iso,
            period_end_iso=period_end_iso,
            compliant=False,
            actual_value=0.0,
            target_value=sla.target_value,
            uptime_fraction=0.0,
            violations=0,
        )

    violations = 0
    value_sum = 0.0
    for pt in points:
        meets = AlertEngine.check_condition(
            pt.value, sla.condition, sla.target_value
        )
        if not meets:
            violations += 1
        value_sum += pt.value

    points_meeting = total - violations
    uptime_fraction = points_meeting / total
    actual_value = value_sum / total
    compliant = uptime_fraction >= sla.minimum_uptime_fraction

    return SLAComplianceResult(
        sla_id=sla.sla_id,
        link_id=link_id,
        period_start_iso=period_start_iso,
        period_end_iso=period_end_iso,
        compliant=compliant,
        actual_value=round(actual_value, 6),
        target_value=sla.target_value,
        uptime_fraction=round(uptime_fraction, 6),
        violations=violations,
    )
