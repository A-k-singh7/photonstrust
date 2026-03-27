"""Data helpers for Streamlit UI."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request


def _is_within_root(path_text: str, root_text: str) -> bool:
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def _allowed_results_roots() -> tuple[str, ...]:
    roots = (
        os.path.realpath(os.getcwd()),
        os.path.realpath(tempfile.gettempdir()),
        os.path.realpath(str(Path.home())),
    )
    return tuple(dict.fromkeys(roots))


def _resolve_results_root(path_value: Path) -> Path:
    resolved = os.path.realpath(os.fspath(Path(path_value)))
    if not any(_is_within_root(resolved, root_text) for root_text in _allowed_results_roots()):
        raise ValueError("results_root must stay within the workspace, home, or temp directories")
    return Path(resolved)


def list_runs(results_root: Path) -> list[Path]:
    results_root = _resolve_results_root(results_root)
    if not results_root.exists():
        return []
    registry = results_root / "run_registry.json"
    if registry.exists():
        try:
            payload = json.loads(registry.read_text(encoding="utf-8"))
            return [Path(entry["card_path"]) for entry in payload if entry.get("card_path")]
        except json.JSONDecodeError:
            pass
    return sorted(results_root.glob("**/reliability_card.json"))


def load_card(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_dataset_entries(results_root: Path) -> list[Path]:
    results_root = _resolve_results_root(results_root)
    if not results_root.exists():
        return []
    return sorted(results_root.glob("**/dataset_entry.json"))


def load_dataset_entry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _join_api_url(base_url: str, path: str) -> str:
    root = str(base_url or "").strip().rstrip("/")
    if not root:
        raise RuntimeError("API base URL is empty")
    suffix = str(path or "").strip()
    if not suffix.startswith("/"):
        suffix = "/" + suffix
    return root + suffix


def _extract_http_error_detail(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        return "unknown error"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if detail is not None:
            return str(detail)
    return text


def _request_json(
    *,
    method: str,
    url: str,
    payload: dict[str, Any] | None,
    timeout_s: float,
) -> dict[str, Any]:
    body = None
    headers = {"accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"

    req = request.Request(url=url, data=body, method=method.upper(), headers=headers)
    try:
        with request.urlopen(req, timeout=max(1.0, float(timeout_s))) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = _extract_http_error_detail(exc.read().decode("utf-8", errors="replace"))
        raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach API at {url}: {exc.reason}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"API returned non-JSON response from {url}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"API returned unexpected response shape from {url}")
    return payload


def api_get_json(base_url: str, path: str, *, timeout_s: float = 15.0) -> dict[str, Any]:
    url = _join_api_url(base_url, path)
    return _request_json(method="GET", url=url, payload=None, timeout_s=timeout_s)


def api_post_json(
    base_url: str,
    path: str,
    payload: dict[str, Any],
    *,
    timeout_s: float = 60.0,
) -> dict[str, Any]:
    url = _join_api_url(base_url, path)
    return _request_json(method="POST", url=url, payload=payload, timeout_s=timeout_s)


def api_artifact_url(base_url: str, run_id: str, artifact_relpath: str) -> str:
    rid = str(run_id or "").strip()
    rel = str(artifact_relpath or "").strip()
    if not rid or not rel:
        raise RuntimeError("run_id and artifact_relpath are required")
    path = f"/v0/runs/{rid}/artifact?path={parse.quote(rel, safe='/')}"
    return _join_api_url(base_url, path)


def append_ui_metric_event(
    *,
    results_root: Path,
    event_name: str,
    payload: dict[str, Any] | None = None,
) -> Path:
    root = _resolve_results_root(results_root)
    out_dir = root / "ui_metrics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "events.jsonl"

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": str(event_name or "").strip() or "unknown_event",
        "payload": payload if isinstance(payload, dict) else {},
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=True) + "\n")
    return path


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def stable_json_hash(payload: Any) -> str:
    raw = stable_json_dumps(payload).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def save_ui_run_profile(
    *,
    results_root: Path,
    profile: dict[str, Any],
    profile_name: str | None = None,
) -> Path:
    root = _resolve_results_root(results_root)
    out_dir = root / "ui_profiles"
    out_dir.mkdir(parents=True, exist_ok=True)

    digest = stable_json_hash(profile)
    name = str(profile_name or "").strip().lower()
    if name:
        safe = re.sub(r"[^a-z0-9._-]+", "_", name).strip("._-")
        if not safe:
            safe = f"profile_{digest[:12]}"
        filename = f"{safe}.json"
    else:
        filename = f"profile_{digest[:12]}.json"

    path = out_dir / filename
    path.write_text(json.dumps(profile, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _safe_slug(value: str, *, fallback: str = "item", max_len: int = 48) -> str:
    text = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").strip().lower())
    text = text.strip("_-")
    if not text:
        text = str(fallback).strip().lower() or "item"
    if len(text) > int(max_len):
        text = text[: int(max_len)]
    if not text[0].isalnum():
        text = f"x{text}"
    while len(text) < 3:
        text += "x"
    return text


def save_ui_pic_run_bundle(
    *,
    results_root: Path,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
) -> dict[str, Path]:
    root = _resolve_results_root(results_root)
    out_root = root / "ui_pic_runs"
    out_root.mkdir(parents=True, exist_ok=True)

    req = dict(request_payload) if isinstance(request_payload, dict) else {}
    res = dict(response_payload) if isinstance(response_payload, dict) else {}

    graph = req.get("graph") if isinstance(req.get("graph"), dict) else {}
    graph_id = str(graph.get("graph_id", "")).strip() or "pic_graph"
    slug = _safe_slug(graph_id, fallback="pic_graph")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = out_root / f"{ts}_{slug}"
    idx = 1
    while bundle_dir.exists():
        bundle_dir = out_root / f"{ts}_{slug}_{idx:02d}"
        idx += 1
    bundle_dir.mkdir(parents=True, exist_ok=True)

    request_path = bundle_dir / "request.json"
    response_path = bundle_dir / "response.json"
    summary_path = bundle_dir / "summary.json"
    summary_md_path = bundle_dir / "summary.md"
    graph_path = bundle_dir / "graph.json"
    netlist_path = bundle_dir / "netlist.json"

    request_path.write_text(json.dumps(req, indent=2, sort_keys=True), encoding="utf-8")
    response_path.write_text(json.dumps(res, indent=2, sort_keys=True), encoding="utf-8")
    graph_path.write_text(json.dumps(graph, indent=2, sort_keys=True), encoding="utf-8")

    netlist = res.get("netlist") if isinstance(res.get("netlist"), dict) else {}
    netlist_path.write_text(json.dumps(netlist, indent=2, sort_keys=True), encoding="utf-8")

    results = res.get("results") if isinstance(res.get("results"), dict) else {}
    sweep = results.get("sweep") if isinstance(results.get("sweep"), dict) else None
    mode = "sweep" if isinstance(sweep, dict) else "single"

    overview: dict[str, Any] = {
        "mode": mode,
        "wavelength_nm": req.get("wavelength_nm"),
        "wavelength_sweep_nm": req.get("wavelength_sweep_nm"),
        "graph_hash": res.get("graph_hash"),
        "generated_at": res.get("generated_at"),
    }
    if isinstance(sweep, dict):
        points = sweep.get("points") if isinstance(sweep.get("points"), list) else []
        eta_values: list[float] = []
        for point in points:
            if not isinstance(point, dict):
                continue
            chain = point.get("chain_solver") if isinstance(point.get("chain_solver"), dict) else {}
            try:
                eta_values.append(float(chain.get("eta_total")))
            except (TypeError, ValueError):
                pass
        overview["sweep_points"] = len(points)
        overview["chain_eta_total_min"] = min(eta_values) if eta_values else None
        overview["chain_eta_total_max"] = max(eta_values) if eta_values else None
    else:
        chain = results.get("chain_solver") if isinstance(results.get("chain_solver"), dict) else {}
        scatt = results.get("scattering_solver") if isinstance(results.get("scattering_solver"), dict) else {}
        overview["chain_eta_total"] = chain.get("eta_total")
        overview["chain_total_loss_db"] = chain.get("total_loss_db")
        overview["scattering_applicable"] = bool(scatt.get("applicable", False))

    summary = {
        "schema_version": "0.1",
        "kind": "photonstrust.ui_pic_run_bundle",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "bundle_dir": str(bundle_dir),
        "files": {
            "request_json": str(request_path),
            "response_json": str(response_path),
            "graph_json": str(graph_path),
            "netlist_json": str(netlist_path),
            "summary_json": str(summary_path),
            "summary_md": str(summary_md_path),
        },
        "graph_id": graph_id,
        "overview": overview,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    md_lines = [
        "# UI PIC Run Bundle",
        "",
        f"- saved_at: `{summary['saved_at']}`",
        f"- graph_id: `{graph_id}`",
        f"- mode: `{mode}`",
        f"- graph_hash: `{overview.get('graph_hash')}`",
        f"- generated_at: `{overview.get('generated_at')}`",
        "",
        "## Files",
        f"- request: `{request_path}`",
        f"- response: `{response_path}`",
        f"- graph: `{graph_path}`",
        f"- netlist: `{netlist_path}`",
        f"- summary: `{summary_path}`",
        "",
    ]
    if mode == "sweep":
        md_lines.append(f"- sweep_points: `{overview.get('sweep_points')}`")
        md_lines.append(f"- chain_eta_total_min: `{overview.get('chain_eta_total_min')}`")
        md_lines.append(f"- chain_eta_total_max: `{overview.get('chain_eta_total_max')}`")
    else:
        md_lines.append(f"- chain_eta_total: `{overview.get('chain_eta_total')}`")
        md_lines.append(f"- chain_total_loss_db: `{overview.get('chain_total_loss_db')}`")
        md_lines.append(f"- scattering_applicable: `{overview.get('scattering_applicable')}`")
    summary_md_path.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    return {
        "bundle_dir": bundle_dir,
        "request_json": request_path,
        "response_json": response_path,
        "graph_json": graph_path,
        "netlist_json": netlist_path,
        "summary_json": summary_path,
        "summary_md": summary_md_path,
    }


def diagnose_api_runtime_error(err: Exception | str) -> dict[str, str]:
    text = str(err or "").strip()
    low = text.lower()

    category = "unknown"
    title = "Unexpected error"
    hint = "Retry once. If it persists, inspect API logs and payload."

    if "could not reach api" in low or "connection refused" in low:
        category = "connectivity"
        title = "API not reachable"
        hint = "Start API server (`uvicorn photonstrust.api.server:app --host 127.0.0.1 --port 8000`) and verify API base URL."
    elif "timed out" in low:
        category = "timeout"
        title = "API request timed out"
        hint = "Retry with smaller scenario scope first; if repeated, check server load and logs."
    else:
        status_code = _parse_status_code_from_message(text)
        if status_code in {401, 403}:
            category = "auth_scope"
            title = "Authorization or project-scope error"
            hint = "Use a permitted project_id and ensure your API token/role has runner access."
        elif status_code == 400:
            category = "input_validation"
            title = "Input validation failed"
            hint = "Check required fields and parameter ranges in Run Builder."
            if "certification mode requires explicit pdk manifest context" in low:
                hint = "Switch execution mode to `preview` for quick runs, or provide pdk/pdk_manifest for certification mode."
            elif "expects a graph with profile=qkd_link" in low:
                hint = "Run Builder must submit `profile=qkd_link`. Re-generate payload and retry."
            elif "must be > 0" in low:
                hint = "One numeric field is non-positive. Check rep_rate_mhz, pde, and timing values."
        elif status_code is not None and status_code >= 500:
            category = "backend_failure"
            title = "Server-side failure"
            hint = "Inspect API server traceback/logs, then retry after fixing backend error."

    return {
        "category": category,
        "title": title,
        "hint": hint,
        "detail": text,
    }


def _parse_status_code_from_message(text: str) -> int | None:
    raw = str(text or "").strip()
    match = re.search(r"API request failed \((\d{3})\)", raw)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _ui_product_state_path(results_root: Path) -> Path:
    root = _resolve_results_root(results_root)
    out_dir = root / "ui_product_state"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / "state.json"


def load_ui_product_state(results_root: Path) -> dict[str, Any]:
    path = _ui_product_state_path(results_root)
    if not path.exists():
        return {
            "schema_version": "0.1",
            "kind": "photonstrust.ui_product_state",
            "baselines": {},
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    if not isinstance(payload.get("baselines"), dict):
        payload["baselines"] = {}
    payload.setdefault("schema_version", "0.1")
    payload.setdefault("kind", "photonstrust.ui_product_state")
    return payload


def save_ui_product_state(results_root: Path, state: dict[str, Any]) -> Path:
    path = _ui_product_state_path(results_root)
    payload = dict(state) if isinstance(state, dict) else {}
    if not isinstance(payload.get("baselines"), dict):
        payload["baselines"] = {}
    payload.setdefault("schema_version", "0.1")
    payload.setdefault("kind", "photonstrust.ui_product_state")
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def get_ui_project_baseline(results_root: Path, project_id: str) -> dict[str, Any] | None:
    pid = str(project_id or "").strip().lower() or "default"
    state = load_ui_product_state(results_root)
    baselines = state.get("baselines") if isinstance(state.get("baselines"), dict) else {}
    record = baselines.get(pid)
    return record if isinstance(record, dict) else None


def promote_ui_project_baseline(
    *,
    results_root: Path,
    project_id: str,
    baseline_record: dict[str, Any],
) -> tuple[dict[str, Any], Path]:
    pid = str(project_id or "").strip().lower() or "default"
    state = load_ui_product_state(results_root)
    baselines = state.get("baselines") if isinstance(state.get("baselines"), dict) else {}

    record = dict(baseline_record) if isinstance(baseline_record, dict) else {}
    record["project_id"] = pid
    record["promoted_at"] = datetime.now(timezone.utc).isoformat()
    baselines[pid] = record
    state["baselines"] = baselines
    path = save_ui_product_state(results_root, state)
    return record, path
