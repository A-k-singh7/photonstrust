"""Tests for the real-time QKD link health monitoring module."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from photonstrust.monitor.alerts import AlertEngine
from photonstrust.monitor.degradation import detect_degradation
from photonstrust.monitor.health import compute_link_health, compute_network_health
from photonstrust.monitor.sla import check_sla_compliance
from photonstrust.monitor.store import TimeSeriesStore
from photonstrust.monitor.types import (
    AlertRule,
    MetricPoint,
    SLADefinition,
)


# ---- helpers ----

def _make_point(
    link_id: str,
    metric_name: str,
    value: float,
    ts: datetime | None = None,
) -> MetricPoint:
    if ts is None:
        ts = datetime.now(timezone.utc)
    return MetricPoint(
        timestamp_iso=ts.isoformat(),
        metric_name=metric_name,
        value=value,
        link_id=link_id,
    )


# ---- 1. append & query ----

def test_time_series_store_append_and_query(tmp_path):
    store = TimeSeriesStore(tmp_path)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)

    for i in range(5):
        pt = _make_point("link_a", "key_rate_bps", 1000.0 + i, base + timedelta(seconds=i))
        store.append(pt)

    results = store.query("link_a", "key_rate_bps")
    assert len(results) == 5
    assert results[0].value == 1000.0
    assert results[4].value == 1004.0


# ---- 2. time-range filter ----

def test_time_series_store_time_range_filter(tmp_path):
    store = TimeSeriesStore(tmp_path)
    base = datetime(2025, 6, 1, tzinfo=timezone.utc)

    for i in range(10):
        pt = _make_point("link_b", "qber", 0.01 * i, base + timedelta(hours=i))
        store.append(pt)

    start = (base + timedelta(hours=3)).isoformat()
    end = (base + timedelta(hours=6)).isoformat()

    results = store.query("link_b", "qber", start_iso=start, end_iso=end)
    assert len(results) == 4  # hours 3, 4, 5, 6
    assert results[0].value == 0.03


# ---- 3. latest ----

def test_time_series_store_latest(tmp_path):
    store = TimeSeriesStore(tmp_path)
    base = datetime(2025, 3, 1, tzinfo=timezone.utc)

    for i in range(5):
        store.append(_make_point("link_c", "link_loss_db", 5.0 + i, base + timedelta(minutes=i)))

    latest = store.latest("link_c", "link_loss_db")
    assert latest is not None
    assert latest.value == 9.0


# ---- 4. alert fires on threshold ----

def test_alert_engine_fires_on_threshold(tmp_path):
    store = TimeSeriesStore(tmp_path)
    store.append(_make_point("link_d", "key_rate_bps", 50.0))

    rule = AlertRule(
        rule_id="kr_low",
        metric_name="key_rate_bps",
        condition="lt",
        threshold=100.0,
        window_seconds=300,
        severity="critical",
    )
    engine = AlertEngine([rule])
    alerts = engine.evaluate(store, "link_d")

    assert len(alerts) == 1
    assert alerts[0].severity == "critical"
    assert alerts[0].metric_value == 50.0


# ---- 5. no alert when healthy ----

def test_alert_engine_no_fire_when_healthy(tmp_path):
    store = TimeSeriesStore(tmp_path)
    store.append(_make_point("link_e", "key_rate_bps", 5000.0))

    rule = AlertRule(
        rule_id="kr_low",
        metric_name="key_rate_bps",
        condition="lt",
        threshold=100.0,
        window_seconds=300,
        severity="critical",
    )
    engine = AlertEngine([rule])
    alerts = engine.evaluate(store, "link_e")

    assert len(alerts) == 0


# ---- 6. SLA compliance pass ----

def test_sla_compliance_pass(tmp_path):
    store = TimeSeriesStore(tmp_path)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)

    for i in range(20):
        store.append(
            _make_point("link_f", "key_rate_bps", 12000.0, base + timedelta(hours=i))
        )

    sla = SLADefinition(
        sla_id="sla_test",
        name="Test SLA",
        metric_name="key_rate_bps",
        target_value=10000.0,
        condition="gte",
        measurement_window_hours=720,
        minimum_uptime_fraction=0.99,
    )
    result = check_sla_compliance(
        store,
        "link_f",
        sla,
        period_start_iso=base.isoformat(),
        period_end_iso=(base + timedelta(hours=20)).isoformat(),
    )

    assert result.compliant is True
    assert result.violations == 0
    assert result.uptime_fraction == 1.0


# ---- 7. SLA compliance fail ----

def test_sla_compliance_fail(tmp_path):
    store = TimeSeriesStore(tmp_path)
    base = datetime(2025, 1, 1, tzinfo=timezone.utc)

    for i in range(20):
        # Half the points violate the SLA
        val = 12000.0 if i % 2 == 0 else 5000.0
        store.append(
            _make_point("link_g", "key_rate_bps", val, base + timedelta(hours=i))
        )

    sla = SLADefinition(
        sla_id="sla_test",
        name="Test SLA",
        metric_name="key_rate_bps",
        target_value=10000.0,
        condition="gte",
        measurement_window_hours=720,
        minimum_uptime_fraction=0.99,
    )
    result = check_sla_compliance(
        store,
        "link_g",
        sla,
        period_start_iso=base.isoformat(),
        period_end_iso=(base + timedelta(hours=20)).isoformat(),
    )

    assert result.compliant is False
    assert result.violations == 10
    assert result.uptime_fraction == 0.5


# ---- 8. health score computation ----

def test_health_score_computation(tmp_path):
    store = TimeSeriesStore(tmp_path)

    store.append(_make_point("link_h", "key_rate_bps", 8000.0))
    store.append(_make_point("link_h", "qber", 0.03))
    store.append(_make_point("link_h", "link_loss_db", 10.0))
    store.append(_make_point("link_h", "detector_pde", 0.85))

    health = compute_link_health(store, "link_h")

    assert 0.0 < health.score < 1.0
    assert health.status in ("healthy", "degraded", "critical")
    assert "key_rate_score" in health.components


# ---- 9. degradation detection — linear decline ----

def test_degradation_detection_linear_decline(tmp_path):
    store = TimeSeriesStore(tmp_path)
    now = datetime.now(timezone.utc)

    for i in range(24):
        ts = now - timedelta(hours=23) + timedelta(hours=i)
        store.append(_make_point("link_i", "key_rate_bps", 10000.0 - 300 * i, ts))

    result = detect_degradation(store, "link_i", "key_rate_bps", window_hours=24)

    assert result["trend"] == "degrading"
    assert result["slope"] < 0


# ---- 10. degradation detection — stable ----

def test_degradation_detection_stable(tmp_path):
    store = TimeSeriesStore(tmp_path)
    now = datetime.now(timezone.utc)

    for i in range(24):
        ts = now - timedelta(hours=23) + timedelta(hours=i)
        store.append(_make_point("link_j", "key_rate_bps", 10000.0, ts))

    result = detect_degradation(store, "link_j", "key_rate_bps", window_hours=24)

    assert result["trend"] == "stable"


# ---- 11. network health aggregation ----

def test_network_health_aggregation(tmp_path):
    store = TimeSeriesStore(tmp_path)

    # Link 1: healthy
    store.append(_make_point("link_k", "key_rate_bps", 9000.0))
    store.append(_make_point("link_k", "qber", 0.02))
    store.append(_make_point("link_k", "link_loss_db", 5.0))

    # Link 2: weaker
    store.append(_make_point("link_l", "key_rate_bps", 2000.0))
    store.append(_make_point("link_l", "qber", 0.08))
    store.append(_make_point("link_l", "link_loss_db", 20.0))

    report = compute_network_health(store, ["link_k", "link_l"])

    assert len(report.link_reports) == 2
    assert report.weakest_link_id == "link_l"
    assert report.overall_score > 0
