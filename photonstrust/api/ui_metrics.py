"""UI telemetry event store helpers (local-dev).

This module uses a filesystem-backed JSONL append log to avoid database
dependencies while the product telemetry contract is being hardened.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from photonstrust.api import runs as run_store

UI_EVENTS_BASENAME = "events.jsonl"

_APPEND_LOCK = threading.Lock()


def _repo_root() -> Path:
    # .../photonstrust/api/ui_metrics.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def results_root() -> Path:
    """Resolve the base results root for telemetry artifacts.

    Priority:
    1) PHOTONTRUST_RESULTS_ROOT (absolute or repo-relative)
    2) Derive from PHOTONTRUST_API_RUNS_ROOT / run_store.runs_root()
       (if basename is `api_runs`, use parent)
    3) Fallback to `<repo>/results`
    """

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


def ui_metrics_root() -> Path:
    return (results_root() / "ui_metrics").resolve()


def ui_metrics_events_path() -> Path:
    return ui_metrics_root() / UI_EVENTS_BASENAME


def append_ui_metric_event(event: dict[str, Any]) -> Path:
    out_dir = ui_metrics_root()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = ui_metrics_events_path()
    line = json.dumps(event, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    with _APPEND_LOCK:
        with out_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return out_path
