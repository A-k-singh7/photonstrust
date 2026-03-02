"""Foundry verification telemetry helpers (filesystem-backed JSONL store)."""

from __future__ import annotations

import json
import math
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.api import runs as run_store

FOUNDRY_EVENTS_BASENAME = "events.jsonl"
_ALLOWED_OUTCOMES = {"success", "timeout", "nonzero", "error"}

_APPEND_LOCK = threading.Lock()


def _repo_root() -> Path:
    # .../photonstrust/api/foundry_metrics.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def results_root() -> Path:
    """Resolve the base results root for foundry telemetry artifacts."""

    raw = str(os.environ.get("PHOTONTRUST_RESULTS_ROOT", "") or "").strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = _repo_root() / p
        return p.resolve()

    runs_root = run_store.runs_root()
    if str(runs_root.name).strip().lower() == "api_runs":
        return runs_root.parent.resolve()
    return runs_root.resolve()


def foundry_metrics_root() -> Path:
    return (results_root() / "foundry_metrics").resolve()


def foundry_metrics_events_path() -> Path:
    return foundry_metrics_root() / FOUNDRY_EVENTS_BASENAME


def append_foundry_metric_event(event: dict[str, Any]) -> Path:
    out_dir = foundry_metrics_root()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = foundry_metrics_events_path()
    line = json.dumps(event, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    with _APPEND_LOCK:
        with out_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return out_path


def read_foundry_metric_events(*, limit: int = 200) -> list[dict[str, Any]]:
    if limit < 1:
        limit = 1
    if limit > 5000:
        limit = 5000

    path = foundry_metrics_events_path()
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            obj = json.loads(text)
        except Exception:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows[-limit:]


def _is_timeout_error_code(error_code: str) -> bool:
    return "timeout" in str(error_code or "").strip().lower()


def _is_nonzero_error_code(error_code: str) -> bool:
    code = str(error_code or "").strip().lower()
    return code == "command_failed" or "nonzero" in code


def classify_foundry_outcome(*, status: str | None, error_code: str | None) -> str:
    status_norm = str(status or "").strip().lower()
    error_norm = str(error_code or "").strip().lower()

    if status_norm in {"pass", "fail"}:
        return "success"
    if status_norm == "error":
        if _is_timeout_error_code(error_norm):
            return "timeout"
        if _is_nonzero_error_code(error_norm):
            return "nonzero"
        return "error"

    if _is_timeout_error_code(error_norm):
        return "timeout"
    if _is_nonzero_error_code(error_norm):
        return "nonzero"
    return "error"


def _parse_duration_ms(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        parsed = int(round(float(text)))
    except Exception:
        return None
    if parsed < 0:
        return None
    return parsed


def _nearest_rank_percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    p = min(100.0, max(0.0, float(percentile)))
    if p <= 0.0:
        return int(values[0])
    n = len(values)
    rank = int(math.ceil((p / 100.0) * n))
    rank = max(1, min(n, rank))
    return int(values[rank - 1])


def aggregate_foundry_metrics(events: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = events if isinstance(events, list) else []

    per_backend: dict[str, dict[str, Any]] = {}
    total = 0
    success = 0
    timeout = 0
    nonzero = 0
    error = 0
    all_durations: list[int] = []

    for row in rows:
        if not isinstance(row, dict):
            continue
        backend = str(row.get("execution_backend") or "unknown").strip().lower() or "unknown"
        outcome_raw = str(row.get("outcome") or "").strip().lower()
        if outcome_raw in _ALLOWED_OUTCOMES:
            outcome = outcome_raw
        else:
            outcome = classify_foundry_outcome(status=row.get("status"), error_code=row.get("error_code"))

        duration_ms = _parse_duration_ms(row.get("duration_ms"))

        bucket = per_backend.setdefault(
            backend,
            {
                "total": 0,
                "success": 0,
                "timeout": 0,
                "nonzero": 0,
                "error": 0,
                "_durations": [],
            },
        )
        bucket["total"] = int(bucket.get("total", 0)) + 1
        bucket[outcome] = int(bucket.get(outcome, 0)) + 1
        total += 1

        if outcome == "success":
            success += 1
        elif outcome == "timeout":
            timeout += 1
        elif outcome == "nonzero":
            nonzero += 1
        else:
            error += 1

        if duration_ms is not None:
            bucket_durations = bucket.get("_durations")
            if isinstance(bucket_durations, list):
                bucket_durations.append(duration_ms)
            all_durations.append(duration_ms)

    by_backend: dict[str, Any] = {}
    for backend in sorted(per_backend):
        bucket = per_backend[backend]
        bucket_total = int(bucket.get("total", 0) or 0)
        bucket_success = int(bucket.get("success", 0) or 0)
        bucket_timeout = int(bucket.get("timeout", 0) or 0)
        bucket_nonzero = int(bucket.get("nonzero", 0) or 0)
        bucket_error = int(bucket.get("error", 0) or 0)
        durations = sorted(int(v) for v in (bucket.get("_durations") or []) if isinstance(v, int))

        by_backend[backend] = {
            "total": bucket_total,
            "success": bucket_success,
            "timeout": bucket_timeout,
            "nonzero": bucket_nonzero,
            "error": bucket_error,
            "success_rate": (bucket_success / bucket_total) if bucket_total else 0.0,
            "timeout_rate": (bucket_timeout / bucket_total) if bucket_total else 0.0,
            "nonzero_rate": (bucket_nonzero / bucket_total) if bucket_total else 0.0,
            "duration_ms": {
                "count": len(durations),
                "p50": _nearest_rank_percentile(durations, 50.0),
                "p95": _nearest_rank_percentile(durations, 95.0),
            },
        }

    durations_all_sorted = sorted(all_durations)
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.foundry_metrics_summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total": int(total),
        "success": int(success),
        "timeout": int(timeout),
        "nonzero": int(nonzero),
        "error": int(error),
        "success_rate": (success / total) if total else 0.0,
        "timeout_rate": (timeout / total) if total else 0.0,
        "nonzero_rate": (nonzero / total) if total else 0.0,
        "duration_ms": {
            "count": len(durations_all_sorted),
            "p50": _nearest_rank_percentile(durations_all_sorted, 50.0),
            "p95": _nearest_rank_percentile(durations_all_sorted, 95.0),
        },
        "by_backend": by_backend,
    }


def _parse_iso_ts(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _duration_ms_from_summary(summary: dict[str, Any]) -> int | None:
    started_at = _parse_iso_ts(summary.get("started_at"))
    finished_at = _parse_iso_ts(summary.get("finished_at"))
    if started_at is None or finished_at is None:
        return None
    delta_s = (finished_at - started_at).total_seconds()
    return max(0, int(round(delta_s * 1000.0)))


def build_foundry_metric_event(*, stage: str, run_id: str, summary: dict[str, Any]) -> dict[str, Any]:
    status = str(summary.get("status") or "").strip().lower()
    error_code_text = str(summary.get("error_code") or "").strip()
    error_code = error_code_text or None
    execution_backend = str(summary.get("execution_backend") or "").strip().lower() or "unknown"
    duration_ms = _duration_ms_from_summary(summary)
    if duration_ms is None:
        duration_ms = _parse_duration_ms(summary.get("duration_ms"))
    if duration_ms is None:
        duration_ms = 0

    check_counts = summary.get("check_counts") if isinstance(summary.get("check_counts"), dict) else {}
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.foundry_metric_event",
        "event_id": uuid.uuid4().hex[:12],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": str(run_id).strip(),
        "stage": str(stage).strip().lower() or "unknown",
        "execution_backend": execution_backend,
        "status": status or None,
        "error_code": error_code,
        "outcome": classify_foundry_outcome(status=status, error_code=error_code),
        "duration_ms": int(duration_ms),
        "check_counts": {
            "total": int(check_counts.get("total", 0) or 0),
            "passed": int(check_counts.get("passed", 0) or 0),
            "failed": int(check_counts.get("failed", 0) or 0),
            "errored": int(check_counts.get("errored", 0) or 0),
        },
    }
