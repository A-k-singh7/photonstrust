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
from photonstrust.product_demo import PILOT_CASES, build_pilot_graph, safe_demo_id

PROJECT_APPROVALS_BASENAME = "approvals.jsonl"
PROJECT_MANIFEST_BASENAME = "project_manifest.json"
PROJECT_WORKSPACE_BASENAME = "workspace.json"

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


def project_manifest_path(project_id: str) -> Path:
    return project_dir_for_id(project_id) / PROJECT_MANIFEST_BASENAME


def project_workspace_path(project_id: str) -> Path:
    return project_dir_for_id(project_id) / PROJECT_WORKSPACE_BASENAME


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


def approvals_count(project_id: str) -> int:
    path = approvals_path(project_id)
    if not path.exists():
        return 0
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            count += 1
    return count


def read_project_manifest(project_id: str) -> dict[str, Any] | None:
    path = project_manifest_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def write_project_manifest(project_id: str, manifest: dict[str, Any]) -> Path:
    pid = validate_project_id(project_id)
    pdir = project_dir_for_id(pid)
    pdir.mkdir(parents=True, exist_ok=True)
    path = project_manifest_path(pid)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def read_project_workspace(project_id: str) -> dict[str, Any] | None:
    path = project_workspace_path(project_id)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def write_project_workspace(project_id: str, workspace: dict[str, Any]) -> Path:
    pid = validate_project_id(project_id)
    pdir = project_dir_for_id(pid)
    pdir.mkdir(parents=True, exist_ok=True)
    path = project_workspace_path(pid)
    path.write_text(json.dumps(workspace, indent=2), encoding="utf-8")
    return path


def _generated_at_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_project_id_from_payload(payload: dict[str, Any]) -> str:
    demo_case_id = str(payload.get("demo_case_id") or "").strip()
    template_id = str(payload.get("template_id") or "").strip()
    title = str(payload.get("title") or "").strip()
    candidate = demo_case_id or title or template_id or "project"
    return validate_project_id(safe_demo_id(candidate, fallback="project"))


def _default_workspace_payload(*, project_id: str, title: str, template_id: str, graph: dict[str, Any] | None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "photonstrust.project_workspace",
        "project_id": project_id,
        "title": title,
        "template_id": template_id or None,
        "stage": "build",
        "mode": "graph",
        "selected_run_id": None,
        "compare": {
            "baseline_run_id": None,
            "candidate_run_ids": [],
            "scope": "input",
        },
    }
    if isinstance(graph, dict):
        out["graph"] = graph
    return out


def _merge_workspace(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(override, dict):
        return base
    out = dict(base)
    for key, value in override.items():
        if key == "graph" and isinstance(value, dict):
            out[key] = value
            continue
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = {**out[key], **value}
            continue
        out[key] = value
    return out


def bootstrap_project(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, dict) else {}
    project_id_raw = str(data.get("project_id") or "").strip().lower()
    project_id = validate_project_id(project_id_raw) if project_id_raw else _default_project_id_from_payload(data)
    existing_manifest = read_project_manifest(project_id) or {}
    created_at = str(existing_manifest.get("created_at") or _generated_at_now())
    updated_at = _generated_at_now()

    template_id = str(data.get("template_id") or existing_manifest.get("template_id") or "qkd").strip() or "qkd"
    execution_mode = str(data.get("execution_mode") or "preview").strip().lower() or "preview"
    demo_case_id = str(data.get("demo_case_id") or existing_manifest.get("demo_case_id") or "").strip()
    demo_case = next((case for case in PILOT_CASES if case.case_id == demo_case_id), None)

    graph = None
    if demo_case is not None:
        graph = build_pilot_graph(
            demo_case,
            run_token=safe_demo_id(project_id, max_len=20, fallback="project"),
            execution_mode=execution_mode,
        )
    elif isinstance(data.get("graph"), dict):
        graph = data.get("graph")

    title_default = demo_case.case_id.replace("_", " ").title() if demo_case is not None else project_id.replace("_", " ").title()
    title = str(data.get("title") or existing_manifest.get("title") or title_default).strip() or title_default
    description = str(data.get("description") or existing_manifest.get("description") or "").strip()
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else existing_manifest.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}

    manifest = {
        "schema_version": "0.1",
        "kind": "photonstrust.project_manifest",
        "project_id": project_id,
        "title": title,
        "description": description,
        "template_id": template_id,
        "demo_case_id": demo_case.case_id if demo_case is not None else (demo_case_id or None),
        "execution_mode": execution_mode,
        "created_at": created_at,
        "updated_at": updated_at,
        "metadata": metadata,
    }
    write_project_manifest(project_id, manifest)

    workspace = _default_workspace_payload(project_id=project_id, title=title, template_id=template_id, graph=graph)
    workspace = _merge_workspace(workspace, data.get("workspace") if isinstance(data.get("workspace"), dict) else None)
    workspace["project_id"] = project_id
    workspace["title"] = title
    workspace["template_id"] = template_id
    write_project_workspace(project_id, workspace)

    return get_project(project_id)


def update_project_workspace(project_id: str, workspace: dict[str, Any]) -> dict[str, Any]:
    pid = validate_project_id(project_id)
    current = read_project_workspace(pid) or {
        "schema_version": "0.1",
        "kind": "photonstrust.project_workspace",
        "project_id": pid,
    }
    merged = _merge_workspace(current, workspace)
    merged["schema_version"] = "0.1"
    merged["kind"] = "photonstrust.project_workspace"
    merged["project_id"] = pid
    write_project_workspace(pid, merged)

    manifest = read_project_manifest(pid)
    if isinstance(manifest, dict):
        manifest["updated_at"] = _generated_at_now()
        write_project_manifest(pid, manifest)

    return merged


def list_projects(*, limit: int = 200) -> list[dict[str, Any]]:
    """List project summaries from stored manifests and run history."""

    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    by_project: dict[str, dict[str, Any]] = {}
    projects_dir = projects_root()
    if projects_dir.exists():
        for entry in projects_dir.iterdir():
            if not entry.is_dir():
                continue
            name = str(entry.name)
            if not name.startswith("project_"):
                continue
            pid = name[8:]
            try:
                pid = validate_project_id(pid)
            except Exception:
                continue
            manifest = read_project_manifest(pid) or {}
            workspace_present = project_workspace_path(pid).exists()
            updated_at = manifest.get("updated_at") or manifest.get("created_at")
            ts = _parse_ts(updated_at)
            if ts is None:
                ts = float(entry.stat().st_mtime)
                updated_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            by_project[pid] = {
                "project_id": pid,
                "title": manifest.get("title") or pid,
                "description": manifest.get("description") or "",
                "template_id": manifest.get("template_id"),
                "demo_case_id": manifest.get("demo_case_id"),
                "created_at": manifest.get("created_at"),
                "updated_at": manifest.get("updated_at") or updated_at,
                "workspace_present": workspace_present,
                "approval_count": approvals_count(pid),
                "run_count": 0,
                "last_run_at": None,
                "_last_ts": ts,
            }

    root = run_store.runs_root()
    if root.exists():
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

            summary = by_project.get(pid)
            if not summary:
                manifest = read_project_manifest(pid) or {}
                summary = {
                    "project_id": pid,
                    "title": manifest.get("title") or pid,
                    "description": manifest.get("description") or "",
                    "template_id": manifest.get("template_id"),
                    "demo_case_id": manifest.get("demo_case_id"),
                    "created_at": manifest.get("created_at"),
                    "updated_at": manifest.get("updated_at"),
                    "workspace_present": project_workspace_path(pid).exists(),
                    "approval_count": approvals_count(pid),
                    "run_count": 0,
                    "last_run_at": None,
                    "_last_ts": 0.0,
                }
                by_project[pid] = summary

            summary["run_count"] = int(summary.get("run_count", 0) or 0) + 1
            if ts >= float(summary.get("_last_ts", 0.0) or 0.0):
                summary["_last_ts"] = ts
                summary["last_run_at"] = generated_at

    out = list(by_project.values())
    out.sort(key=lambda x: float(x.get("_last_ts", 0.0) or 0.0), reverse=True)
    for item in out:
        item.pop("_last_ts", None)

    return out[:limit]


def get_project(project_id: str) -> dict[str, Any]:
    pid = validate_project_id(project_id)
    manifest = read_project_manifest(pid) or {}
    workspace = read_project_workspace(pid)
    summaries = list_projects(limit=500)
    summary = next((item for item in summaries if str(item.get("project_id")) == pid), None)
    if summary is None and not manifest and workspace is None:
        raise FileNotFoundError("project not found")
    if summary is None:
        summary = {
            "project_id": pid,
            "title": manifest.get("title") or pid,
            "description": manifest.get("description") or "",
            "template_id": manifest.get("template_id"),
            "demo_case_id": manifest.get("demo_case_id"),
            "created_at": manifest.get("created_at"),
            "updated_at": manifest.get("updated_at"),
            "workspace_present": workspace is not None,
            "approval_count": approvals_count(pid),
            "run_count": 0,
            "last_run_at": None,
        }
    return {
        "project": summary,
        "manifest": manifest,
        "workspace": workspace,
    }


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
