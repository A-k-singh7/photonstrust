"""Health score computation for QKD links and networks."""

from __future__ import annotations

from datetime import datetime, timezone

from photonstrust.monitor.store import TimeSeriesStore
from photonstrust.monitor.types import (
    HealthScore,
    LinkHealthReport,
    NetworkHealthReport,
)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def compute_link_health(
    store: TimeSeriesStore,
    link_id: str,
    *,
    nominal_key_rate_bps: float = 10000.0,
) -> HealthScore:
    """Compute a composite health score for a single QKD link."""
    now_iso = datetime.now(timezone.utc).isoformat()

    latest_key_rate = store.latest(link_id, "key_rate_bps")
    latest_qber = store.latest(link_id, "qber")
    latest_loss = store.latest(link_id, "link_loss_db")
    latest_pde = store.latest(link_id, "detector_pde")

    # If no metrics at all, return unknown
    if all(
        m is None
        for m in [latest_key_rate, latest_qber, latest_loss, latest_pde]
    ):
        return HealthScore(
            link_id=link_id,
            score=0.0,
            timestamp_iso=now_iso,
            components={},
            status="unknown",
        )

    # Compute individual scores
    key_rate_score = (
        _clamp(latest_key_rate.value / nominal_key_rate_bps)
        if latest_key_rate is not None
        else 0.0
    )
    qber_score = (
        _clamp(1.0 - latest_qber.value / 0.11)
        if latest_qber is not None
        else 0.0
    )
    loss_score = (
        _clamp(1.0 - latest_loss.value / 30.0)
        if latest_loss is not None
        else 0.0
    )
    detector_score = (
        latest_pde.value if latest_pde is not None else 1.0
    )

    composite = (
        0.4 * key_rate_score
        + 0.3 * qber_score
        + 0.2 * loss_score
        + 0.1 * detector_score
    )

    if composite >= 0.8:
        status = "healthy"
    elif composite >= 0.5:
        status = "degraded"
    else:
        status = "critical"

    return HealthScore(
        link_id=link_id,
        score=round(composite, 6),
        timestamp_iso=now_iso,
        components={
            "key_rate_score": round(key_rate_score, 6),
            "qber_score": round(qber_score, 6),
            "loss_score": round(loss_score, 6),
            "detector_score": round(detector_score, 6),
        },
        status=status,
    )


def compute_network_health(
    store: TimeSeriesStore,
    link_ids: list[str],
    *,
    nominal_key_rate_bps: float = 10000.0,
) -> NetworkHealthReport:
    """Aggregate link health into a network-wide report."""
    now_iso = datetime.now(timezone.utc).isoformat()

    if not link_ids:
        return NetworkHealthReport(
            timestamp_iso=now_iso,
            link_reports=[],
            overall_score=0.0,
            overall_status="unknown",
            weakest_link_id="",
            active_alert_count=0,
        )

    link_reports: list[LinkHealthReport] = []
    for lid in link_ids:
        health = compute_link_health(
            store, lid, nominal_key_rate_bps=nominal_key_rate_bps
        )
        report = LinkHealthReport(
            link_id=lid,
            health=health,
            active_alerts=[],
            sla_compliance=[],
            trend="unknown",
        )
        link_reports.append(report)

    scores = [r.health.score for r in link_reports]
    overall_score = sum(scores) / len(scores) if scores else 0.0

    if overall_score >= 0.8:
        overall_status = "healthy"
    elif overall_score >= 0.5:
        overall_status = "degraded"
    else:
        overall_status = "critical"

    weakest = min(link_reports, key=lambda r: r.health.score)

    return NetworkHealthReport(
        timestamp_iso=now_iso,
        link_reports=link_reports,
        overall_score=round(overall_score, 6),
        overall_status=overall_status,
        weakest_link_id=weakest.link_id,
        active_alert_count=0,
    )
