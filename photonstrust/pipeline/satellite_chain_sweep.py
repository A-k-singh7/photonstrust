"""Scenario-sweep orchestration for satellite-chain runs."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from photonstrust.config import load_config
from photonstrust.pipeline.satellite_chain import run_satellite_chain


def run_satellite_chain_sweep(
    config_paths: list[Path | str],
    *,
    output_root: Path | str,
    backend: str = "local",
    max_workers: int = 4,
) -> dict[str, Any]:
    """Run many satellite-chain configs and return an aggregate summary."""

    output_dir = Path(output_root).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _normalize_config_rows(config_paths)
    mode = str(backend or "local").strip().lower()

    if mode == "ray":
        run_rows = _run_with_ray(rows=rows, output_root=output_dir)
    else:
        run_rows = _run_with_threads(rows=rows, output_root=output_dir, max_workers=int(max_workers))

    decisions = [str(row.get("decision") or "HOLD").strip().upper() for row in run_rows if isinstance(row, dict)]
    key_bits_total = sum(float(row.get("key_bits_accumulated", 0.0) or 0.0) for row in run_rows if isinstance(row, dict))
    mean_rates = [float(row.get("mean_key_rate_bps", 0.0) or 0.0) for row in run_rows if isinstance(row, dict)]

    summary = {
        "run_count": int(len(run_rows)),
        "decision_counts": {
            "GO": int(sum(1 for d in decisions if d == "GO")),
            "HOLD": int(sum(1 for d in decisions if d != "GO")),
        },
        "key_bits_total": float(key_bits_total),
        "mean_key_rate_bps_avg": float(sum(mean_rates) / len(mean_rates)) if mean_rates else 0.0,
        "backend": mode,
    }

    payload = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_sweep",
        "summary": summary,
        "runs": run_rows,
    }
    report_path = output_dir / "satellite_chain_sweep.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload


def _normalize_config_rows(config_paths: list[Path | str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in config_paths:
        cfg_path = Path(raw).expanduser().resolve()
        config = load_config(cfg_path)
        chain = config.get("satellite_qkd_chain") if isinstance(config, dict) else {}
        if not isinstance(chain, dict):
            chain = {}
        mission_id = str(chain.get("id") or cfg_path.stem).strip() or cfg_path.stem
        out.append({"mission_id": mission_id, "config_path": cfg_path, "config": config})
    return out


def _run_one(row: dict[str, Any], *, output_root: Path) -> dict[str, Any]:
    mission_id = str(row.get("mission_id") or "mission").strip() or "mission"
    config = row.get("config") if isinstance(row.get("config"), dict) else {}
    cfg_path = Path(row.get("config_path"))
    out_dir = output_root / mission_id
    result = run_satellite_chain(config, output_dir=out_dir)

    return {
        "mission_id": mission_id,
        "config_path": str(cfg_path),
        "decision": str(result.get("decision") or "HOLD").strip().upper(),
        "key_bits_accumulated": float(result.get("key_bits_accumulated", 0.0) or 0.0),
        "mean_key_rate_bps": float(result.get("mean_key_rate_bps", 0.0) or 0.0),
        "output_path": result.get("output_path"),
    }


def _run_with_threads(*, rows: list[dict[str, Any]], output_root: Path, max_workers: int) -> list[dict[str, Any]]:
    workers = max(1, int(max_workers))
    out: list[dict[str, Any]] = []

    if workers == 1 or len(rows) <= 1:
        for row in rows:
            out.append(_run_one(row, output_root=output_root))
        return out

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_run_one, row, output_root=output_root) for row in rows]
        for future in as_completed(futures):
            out.append(future.result())
    out.sort(key=lambda row: str(row.get("mission_id", "")))
    return out


def _run_with_ray(*, rows: list[dict[str, Any]], output_root: Path) -> list[dict[str, Any]]:
    try:
        import ray
    except Exception as exc:
        raise RuntimeError("Ray backend requested but ray is not installed. Install with `.[ray]`.") from exc

    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, include_dashboard=False, log_to_driver=False)

    @ray.remote
    def _ray_run(mission_id: str, config_json: str, config_path: str, out_root: str) -> dict[str, Any]:
        payload = json.loads(config_json)
        out_dir = Path(out_root) / mission_id
        result = run_satellite_chain(payload, output_dir=out_dir)
        return {
            "mission_id": mission_id,
            "config_path": str(config_path),
            "decision": str(result.get("decision") or "HOLD").strip().upper(),
            "key_bits_accumulated": float(result.get("key_bits_accumulated", 0.0) or 0.0),
            "mean_key_rate_bps": float(result.get("mean_key_rate_bps", 0.0) or 0.0),
            "output_path": result.get("output_path"),
        }

    tasks = []
    for row in rows:
        mission_id = str(row.get("mission_id") or "mission")
        config_json = json.dumps(row.get("config") or {})
        cfg_path = str(row.get("config_path") or "")
        tasks.append(_ray_run.remote(mission_id, config_json, cfg_path, str(output_root)))

    out = list(ray.get(tasks))
    out.sort(key=lambda row: str(row.get("mission_id", "")))
    return out

