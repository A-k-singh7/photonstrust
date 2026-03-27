"""Run registry + artifact serving helpers (local-dev).

This module intentionally uses a filesystem-backed run manifest (`run_manifest.json`)
to avoid adding DB dependencies during early rollout phases.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

RUN_MANIFEST_BASENAME = "run_manifest.json"

_RUN_ID_RE = re.compile(r"^[a-f0-9]{8,64}$")


def _repo_root() -> Path:
    # .../photonstrust/api/runs.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def _is_within_root(path_text: str, root_text: str) -> bool:
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def _allowed_runs_roots() -> tuple[str, ...]:
    roots = (
        os.path.realpath(os.fspath(_repo_root())),
        os.path.realpath(tempfile.gettempdir()),
        os.path.realpath(str(Path.home())),
    )
    return tuple(dict.fromkeys(roots))


def _resolve_runs_root_candidate(path_value: Path | str) -> Path:
    resolved = os.path.realpath(os.fspath(Path(path_value)))
    if not any(_is_within_root(resolved, root_text) for root_text in _allowed_runs_roots()):
        raise ValueError("runs root must stay within the repository, home, or temp directories")
    return Path(resolved)


def _resolve_run_dir_candidate(path_value: Path | str) -> Path:
    candidate = os.path.realpath(os.fspath(Path(path_value)))
    root_text = os.path.realpath(os.fspath(runs_root()))
    if not _is_within_root(candidate, root_text):
        raise ValueError("run directory must stay within runs root")
    return Path(candidate)


def runs_root() -> Path:
    """Root directory containing API-run directories (`run_<id>`).

    Override with environment variable `PHOTONTRUST_API_RUNS_ROOT` for tests/dev.
    If relative, it is interpreted relative to the repo root.
    """

    raw = str(os.environ.get("PHOTONTRUST_API_RUNS_ROOT", "")).strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = _repo_root() / p
        return _resolve_runs_root_candidate(p)
    return _resolve_runs_root_candidate(_repo_root() / "results" / "api_runs")


def validate_run_id(run_id: str) -> str:
    rid = str(run_id or "").strip().lower()
    if not _RUN_ID_RE.match(rid):
        raise ValueError("Invalid run_id format")
    return rid


def run_dir_for_id(run_id: str) -> Path:
    rid = validate_run_id(run_id)
    root = runs_root()
    candidate = os.path.realpath(os.path.join(os.fspath(root), f"run_{rid}"))
    root_text = os.path.realpath(os.fspath(root))
    if not _is_within_root(candidate, root_text):
        raise ValueError("run_id resolves outside runs root")
    return Path(candidate)


def manifest_path(run_dir: Path) -> Path:
    return _resolve_run_dir_candidate(run_dir) / RUN_MANIFEST_BASENAME


def write_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    run_dir = _resolve_run_dir_candidate(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    out_path = manifest_path(run_dir)
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return out_path


def read_run_manifest(run_dir: Path) -> dict[str, Any] | None:
    path = manifest_path(run_dir)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def summarize_manifest(m: dict[str, Any]) -> dict[str, Any]:
    outputs = m.get("outputs_summary", {}) if isinstance(m.get("outputs_summary"), dict) else {}
    qkd = outputs.get("qkd", {}) if isinstance(outputs.get("qkd"), dict) else {}
    qkd_multifidelity = qkd.get("multifidelity", {}) if isinstance(qkd.get("multifidelity"), dict) else {}
    protocol_selected = qkd.get("protocol_selected") if isinstance(qkd.get("protocol_selected"), str) else None
    artifacts = m.get("artifacts", {}) if isinstance(m.get("artifacts"), dict) else {}

    return {
        "run_id": m.get("run_id"),
        "run_type": m.get("run_type"),
        "generated_at": m.get("generated_at"),
        "output_dir": m.get("output_dir"),
        "project_id": (m.get("input", {}) or {}).get("project_id") or "default",
        "input_hash": m.get("input", {}).get("graph_hash") or m.get("input", {}).get("config_hash"),
        "protocol_selected": protocol_selected or (m.get("input", {}) or {}).get("protocol_selected"),
        "source_job_id": (m.get("input", {}) or {}).get("source_job_id"),
        "compile_cache_key": (m.get("input", {}) or {}).get("compile_cache_key"),
        "multifidelity_present": bool(
            qkd_multifidelity.get("present")
            or (isinstance(artifacts.get("multifidelity_report_json"), str) and artifacts.get("multifidelity_report_json"))
        ),
    }


def list_runs(*, limit: int = 50, project_id: str | None = None) -> list[dict[str, Any]]:
    root = runs_root()
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    pid_filter = None
    if project_id is not None:
        raw = str(project_id or "").strip().lower()
        if raw:
            pid_filter = raw

    if not root.exists():
        return []

    items: list[tuple[float, dict[str, Any]]] = []
    for entry in root.iterdir():
        if not entry.is_dir():
            continue
        name = str(entry.name)
        if not name.startswith("run_"):
            continue
        run_id = name[4:]
        try:
            validate_run_id(run_id)
        except Exception:
            continue

        m = read_run_manifest(entry)
        if not m:
            # Backwards-compatible fallback for older runs.
            ts = float(entry.stat().st_mtime)
            generated_at = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
            m = {
                "schema_version": "0.0",
                "run_id": run_id,
                "run_type": "unknown",
                "generated_at": generated_at,
                "output_dir": str(entry),
                "input": {},
                "artifacts": {},
                "provenance": {},
            }
        if pid_filter is not None:
            project = (m.get("input", {}) or {}).get("project_id") or "default"
            if str(project).strip().lower() != pid_filter:
                continue
        sort_ts = _parse_ts(m.get("generated_at")) or float(entry.stat().st_mtime)
        items.append((sort_ts, summarize_manifest(m)))

    items.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in items[:limit]]


def resolve_artifact_path(run_dir: Path, rel_path: str) -> Path:
    """Resolve a safe artifact path within `run_dir`.

    - Reject absolute paths, drive letters, and '..' segments.
    - Enforce canonical containment under `run_dir` after resolution.
    """

    run_dir = _resolve_run_dir_candidate(run_dir)
    raw = str(rel_path or "").strip()
    if not raw:
        raise ValueError("path is required")
    if raw.startswith(("/", "\\")):
        raise ValueError("path must be relative")
    if ":" in raw:
        raise ValueError("path must not contain ':'")

    p = Path(raw)
    if p.is_absolute():
        raise ValueError("path must be relative")
    if any(part in ("..", "") for part in p.parts):
        raise ValueError("path must not contain '..'")

    base_text = os.path.realpath(os.fspath(run_dir))
    candidate_text = os.path.realpath(os.path.join(base_text, os.fspath(p)))
    if not _is_within_root(candidate_text, base_text):
        raise ValueError("path escapes run directory")
    candidate = Path(candidate_text)

    if not candidate.exists():
        raise FileNotFoundError("artifact not found")
    if not candidate.is_file():
        raise ValueError("artifact is not a file")
    return candidate


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
