"""Trend / degradation detection for QKD link metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from photonstrust.monitor.store import TimeSeriesStore


def detect_degradation(
    store: TimeSeriesStore,
    link_id: str,
    metric_name: str,
    *,
    window_hours: int = 24,
    significance_threshold: float = 0.01,
) -> dict:
    """Detect whether a metric is degrading, stable, or improving.

    Returns a dict with keys: trend, slope, r_squared.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=window_hours)
    start_iso = start.isoformat()
    end_iso = now.isoformat()

    points = store.query(
        link_id, metric_name, start_iso=start_iso, end_iso=end_iso
    )

    if len(points) < 3:
        return {"trend": "unknown", "slope": 0.0, "r_squared": 0.0}

    # Convert timestamps to hours-since-first
    first_dt = datetime.fromisoformat(points[0].timestamp_iso)
    x: list[float] = []
    y: list[float] = []
    for pt in points:
        dt = datetime.fromisoformat(pt.timestamp_iso)
        hours_since = (dt - first_dt).total_seconds() / 3600.0
        x.append(hours_since)
        y.append(pt.value)

    # Linear regression via least squares (no numpy dependency)
    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xy = sum(xi * yi for xi, yi in zip(x, y))
    sum_x2 = sum(xi * xi for xi in x)

    denom = n * sum_x2 - sum_x * sum_x
    if abs(denom) < 1e-15:
        return {"trend": "stable", "slope": 0.0, "r_squared": 0.0}

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # Compute R²
    mean_y = sum_y / n
    ss_tot = sum((yi - mean_y) ** 2 for yi in y)
    ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

    slope = round(slope, 8)
    r_squared = round(r_squared, 8)

    if abs(slope) > significance_threshold and r_squared > 0.3:
        # For "good" metrics (key_rate), negative slope = degrading
        # For "bad" metrics (qber), positive slope = degrading
        # Simple heuristic: negative slope → degrading
        trend = "degrading" if slope < 0 else "improving"
    else:
        trend = "stable"

    return {"trend": trend, "slope": slope, "r_squared": r_squared}
