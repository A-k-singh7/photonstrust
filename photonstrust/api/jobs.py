"""Filesystem-backed async job registry for API background tasks."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.api import runs as run_store
from photonstrust.utils import hash_dict

JOB_MANIFEST_BASENAME = "job_manifest.json"
_JOB_ID_RE = re.compile(r"^[a-f0-9]{8,64}$")
_JOB_STATUS_VALUES = {"queued", "running", "succeeded", "failed"}


def jobs_root() -> Path:
    root = run_store.runs_root() / "_jobs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def validate_job_id(job_id: str) -> str:
    value = str(job_id or "").strip().lower()
    if not _JOB_ID_RE.match(value):
        raise ValueError("Invalid job_id format")
    return value


def job_dir_for_id(job_id: str) -> Path:
    jid = validate_job_id(job_id)
    return jobs_root() / f"job_{jid}"


def _manifest_path(job_dir: Path) -> Path:
    return Path(job_dir) / JOB_MANIFEST_BASENAME


def read_job(job_id: str) -> dict[str, Any] | None:
    path = _manifest_path(job_dir_for_id(job_id))
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def create_job(
    *,
    job_type: str,
    payload: dict[str, Any],
    project_id: str,
    input_hash: str | None = None,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()

    run_dir = job_dir_for_id(job_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    request_path = run_dir / "job_request.json"
    request_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    manifest: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "photonstrust.api_job",
        "job_id": job_id,
        "job_type": str(job_type or "unknown"),
        "status": "queued",
        "created_at": now,
        "updated_at": now,
        "input": {
            "project_id": str(project_id or "default"),
            "input_hash": str(input_hash or hash_dict(payload)),
        },
        "result": None,
        "error": None,
        "artifacts": {
            "job_request_json": "job_request.json",
        },
        "provenance": {
            "store": "filesystem.v0",
        },
    }
    _manifest_path(run_dir).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def set_status(job_id: str, status: str) -> dict[str, Any]:
    value = str(status or "").strip().lower()
    if value not in _JOB_STATUS_VALUES:
        raise ValueError(f"Unsupported job status: {status!r}")
    manifest = read_job(job_id)
    if not isinstance(manifest, dict):
        raise FileNotFoundError("job not found")
    manifest["status"] = value
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _manifest_path(job_dir_for_id(job_id)).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def set_result(job_id: str, result: dict[str, Any]) -> dict[str, Any]:
    manifest = read_job(job_id)
    if not isinstance(manifest, dict):
        raise FileNotFoundError("job not found")

    run_dir = job_dir_for_id(job_id)
    result_path = run_dir / "job_result.json"
    result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    artifacts["job_result_json"] = "job_result.json"
    manifest["artifacts"] = artifacts
    manifest["result"] = dict(result)
    manifest["error"] = None
    manifest["status"] = "succeeded"
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _manifest_path(run_dir).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def set_error(job_id: str, error: dict[str, Any]) -> dict[str, Any]:
    manifest = read_job(job_id)
    if not isinstance(manifest, dict):
        raise FileNotFoundError("job not found")

    run_dir = job_dir_for_id(job_id)
    error_path = run_dir / "job_error.json"
    error_path.write_text(json.dumps(error, indent=2), encoding="utf-8")

    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    artifacts["job_error_json"] = "job_error.json"
    manifest["artifacts"] = artifacts
    manifest["result"] = None
    manifest["error"] = dict(error)
    manifest["status"] = "failed"
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    _manifest_path(run_dir).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def list_jobs(*, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
    root = jobs_root()
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    status_filter = str(status or "").strip().lower() or None
    if status_filter is not None and status_filter not in _JOB_STATUS_VALUES:
        raise ValueError("status must be one of queued, running, succeeded, failed")

    rows: list[tuple[float, dict[str, Any]]] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        name = str(entry.name)
        if not name.startswith("job_"):
            continue
        job_id = name[4:]
        try:
            validate_job_id(job_id)
        except Exception:
            continue
        manifest = read_job(job_id)
        if not isinstance(manifest, dict):
            continue
        if status_filter is not None and str(manifest.get("status", "")).strip().lower() != status_filter:
            continue
        ts = _parse_ts(manifest.get("updated_at"))
        if ts is None:
            ts = float(entry.stat().st_mtime)
        rows.append((ts, manifest))

    rows.sort(key=lambda item: item[0], reverse=True)
    return [item for _, item in rows[:limit]]


def _parse_ts(value: Any) -> float | None:
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return float(dt.timestamp())
    except Exception:
        return None
