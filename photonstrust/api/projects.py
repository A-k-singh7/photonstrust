"""Project registry + approvals log (local-dev).

This module intentionally uses a filesystem-backed event log (JSONL) to avoid
adding DB dependencies during early rollout phases.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.api import runs as run_store

PROJECT_APPROVALS_BASENAME = "approvals.jsonl"

_PROJECT_ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")


def validate_project_id(project_id: str) -> str:
    pid = str(project_id or "").strip().lower()
    if not pid:
        pid = "default"
    if not _PROJECT_ID_RE.match(pid):
        raise ValueError("Invalid project_id format")
    return pid


def projects_root() -> Path:
    return (run_store.runs_root() / "projects").resolve()


def project_dir_for_id(project_id: str) -> Path:
    pid = validate_project_id(project_id)
    return projects_root() / f"project_{pid}"


def approvals_path(project_id: str) -> Path:
    return project_dir_for_id(project_id) / PROJECT_APPROVALS_BASENAME


def append_approval_event(project_id: str, event: dict[str, Any]) -> Path:
    pid = validate_project_id(project_id)
    pdir = project_dir_for_id(pid)
    pdir.mkdir(parents=True, exist_ok=True)
    path = approvals_path(pid)
    line = json.dumps(event, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    return path


def list_approval_events(project_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    pid = validate_project_id(project_id)
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    path = approvals_path(pid)
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if isinstance(obj, dict):
            events.append(obj)

    # Keep newest last; callers can choose display ordering.
    return events[-limit:]


def list_projects(*, limit: int = 200) -> list[dict[str, Any]]:
    """Infer project summaries from stored run manifests."""

    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    root = run_store.runs_root()
    if not root.exists():
        return []

    by_project: dict[str, dict[str, Any]] = {}
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        name = str(entry.name)
        if not name.startswith("run_"):
            continue
        run_id = name[4:]
        try:
            run_store.validate_run_id(run_id)
        except Exception:
            continue

        m = run_store.read_run_manifest(entry) or {}
        if not isinstance(m, dict):
            m = {}
        inp = m.get("input", {}) or {}
        if not isinstance(inp, dict):
            inp = {}

        pid_raw = inp.get("project_id") or "default"
        try:
            pid = validate_project_id(str(pid_raw))
        except Exception:
            pid = "default"

        generated_at = m.get("generated_at")
        ts = _parse_ts(generated_at)
        if ts is None:
            ts = float(entry.stat().st_mtime)
            generated_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()

        s = by_project.get(pid)
        if not s:
            by_project[pid] = {
                "project_id": pid,
                "run_count": 1,
                "last_run_at": generated_at,
                "_last_ts": ts,
            }
        else:
            s["run_count"] = int(s.get("run_count", 0) or 0) + 1
            if ts >= float(s.get("_last_ts", 0.0) or 0.0):
                s["_last_ts"] = ts
                s["last_run_at"] = generated_at

    out = list(by_project.values())
    out.sort(key=lambda x: float(x.get("_last_ts", 0.0) or 0.0), reverse=True)
    for item in out:
        item.pop("_last_ts", None)

    return out[:limit]


def _parse_ts(text: Any) -> float | None:
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except Exception:
        return None

