"""File-backed time-series store for QKD link metrics."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.monitor.types import MetricPoint


class TimeSeriesStore:
    """Append-only JSONL store partitioned by link_id and metric_name."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = Path(data_dir)

    def append(self, point: MetricPoint) -> None:
        """Append a metric point to the store."""
        link_dir = self._data_dir / point.link_id
        link_dir.mkdir(parents=True, exist_ok=True)
        path = link_dir / f"{point.metric_name}.jsonl"
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(point.as_dict()) + "\n")

    def query(
        self,
        link_id: str,
        metric_name: str,
        *,
        start_iso: str | None = None,
        end_iso: str | None = None,
        limit: int = 1000,
    ) -> list[MetricPoint]:
        """Read metric points, optionally filtering by time range."""
        path = self._data_dir / link_id / f"{metric_name}.jsonl"
        if not path.exists():
            return []

        points: list[MetricPoint] = []
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                ts = raw["timestamp_iso"]
                if start_iso is not None and ts < start_iso:
                    continue
                if end_iso is not None and ts > end_iso:
                    continue
                points.append(
                    MetricPoint(
                        timestamp_iso=raw["timestamp_iso"],
                        metric_name=raw["metric_name"],
                        value=raw["value"],
                        link_id=raw["link_id"],
                        tags=raw.get("tags", {}),
                    )
                )

        points.sort(key=lambda p: p.timestamp_iso)
        return points[:limit]

    def latest(self, link_id: str, metric_name: str) -> MetricPoint | None:
        """Return the most recent point for a metric, or None."""
        path = self._data_dir / link_id / f"{metric_name}.jsonl"
        if not path.exists():
            return None

        last_line: str | None = None
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if stripped:
                    last_line = stripped

        if last_line is None:
            return None

        raw = json.loads(last_line)
        return MetricPoint(
            timestamp_iso=raw["timestamp_iso"],
            metric_name=raw["metric_name"],
            value=raw["value"],
            link_id=raw["link_id"],
            tags=raw.get("tags", {}),
        )

    def link_ids(self) -> list[str]:
        """List all link IDs that have stored data."""
        if not self._data_dir.exists():
            return []
        return sorted(
            d.name
            for d in self._data_dir.iterdir()
            if d.is_dir()
        )
