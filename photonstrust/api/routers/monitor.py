"""Real-time QKD link health monitoring API routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/monitor", tags=["monitor"])

_DEFAULT_STORE_DIR = Path("data/monitor")


def _get_store() -> "TimeSeriesStore":  # noqa: F821
    from photonstrust.monitor.store import TimeSeriesStore

    return TimeSeriesStore(_DEFAULT_STORE_DIR)


@router.post("/metrics")
def ingest_metric(payload: dict) -> dict:
    """Ingest a single metric point."""
    from photonstrust.monitor.types import MetricPoint

    try:
        point = MetricPoint(
            timestamp_iso=str(payload["timestamp_iso"]),
            metric_name=str(payload["metric_name"]),
            value=float(payload["value"]),
            link_id=str(payload["link_id"]),
            tags=payload.get("tags", {}),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    store = _get_store()
    store.append(point)
    return {"status": "ok", "point": point.as_dict()}


@router.get("/metrics/{link_id}/{metric_name}")
def query_metrics(
    link_id: str,
    metric_name: str,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Query stored metric points for a link."""
    store = _get_store()
    points = store.query(
        link_id, metric_name, start_iso=start, end_iso=end
    )
    return {
        "link_id": link_id,
        "metric_name": metric_name,
        "count": len(points),
        "points": [p.as_dict() for p in points],
    }


@router.get("/health/{link_id}")
def get_link_health(link_id: str) -> dict:
    """Compute and return health score for a single link."""
    from photonstrust.monitor.health import compute_link_health

    store = _get_store()
    health = compute_link_health(store, link_id)
    return health.as_dict()


@router.get("/health")
def get_network_health() -> dict:
    """Compute and return health for all monitored links."""
    from photonstrust.monitor.health import compute_network_health

    store = _get_store()
    link_ids = store.link_ids()
    report = compute_network_health(store, link_ids)
    return report.as_dict()


@router.get("/alerts/{link_id}")
def get_link_alerts(link_id: str) -> dict:
    """Evaluate default alert rules for a link."""
    import json as _json

    from photonstrust.monitor.alerts import AlertEngine
    from photonstrust.monitor.types import AlertRule

    rules_path = (
        Path(__file__).resolve().parent.parent.parent
        / "monitor"
        / "data"
        / "default_alert_rules.json"
    )
    try:
        raw = _json.loads(rules_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Default alert rules not found")

    rules = [AlertRule(**r) for r in raw["rules"]]
    engine = AlertEngine(rules)
    store = _get_store()
    events = engine.evaluate(store, link_id)
    return {
        "link_id": link_id,
        "alert_count": len(events),
        "alerts": [e.as_dict() for e in events],
    }


@router.post("/sla/check")
def check_sla(payload: dict) -> dict:
    """Check SLA compliance for a link."""
    from photonstrust.monitor.sla import check_sla_compliance
    from photonstrust.monitor.types import SLADefinition

    try:
        sla = SLADefinition(
            sla_id=str(payload["sla_id"]),
            name=str(payload["name"]),
            metric_name=str(payload["metric_name"]),
            target_value=float(payload["target_value"]),
            condition=str(payload["condition"]),
            measurement_window_hours=int(payload["measurement_window_hours"]),
            minimum_uptime_fraction=float(payload["minimum_uptime_fraction"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    link_id = str(payload.get("link_id", ""))
    period_start = str(payload.get("period_start_iso", ""))
    period_end = str(payload.get("period_end_iso", ""))

    if not link_id or not period_start or not period_end:
        raise HTTPException(
            status_code=422,
            detail="link_id, period_start_iso, and period_end_iso are required",
        )

    store = _get_store()
    result = check_sla_compliance(
        store, link_id, sla, period_start_iso=period_start, period_end_iso=period_end
    )
    return result.as_dict()


@router.get("/degradation/{link_id}/{metric_name}")
def check_degradation(link_id: str, metric_name: str) -> dict:
    """Detect metric degradation trend for a link."""
    from photonstrust.monitor.degradation import detect_degradation

    store = _get_store()
    return detect_degradation(store, link_id, metric_name)
