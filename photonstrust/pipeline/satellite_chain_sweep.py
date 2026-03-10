"""Scenario-sweep orchestration for satellite-chain runs."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.config import load_config
from photonstrust.ops.tracking import start_tracking_session
from photonstrust.pipeline.satellite_chain import run_satellite_chain
from photonstrust.utils import hash_dict
from photonstrust.workflow.schema import satellite_qkd_chain_sweep_schema_path


_ALLOWED_BACKENDS = {"local", "ray"}


def run_satellite_chain_sweep(
    config_paths: list[Path | str],
    *,
    output_root: Path | str,
    backend: str = "local",
    max_workers: int = 4,
    seed: int = 42,
    job_timeout_s: float | None = 600.0,
    max_retries: int = 1,
    ray_num_cpus: float = 1.0,
    ray_memory_mb: float | None = None,
    ray_max_in_flight: int | None = None,
    require_complete_results: bool = True,
    tracking_mode: str | None = "local_json",
    tracking_uri: str | None = None,
) -> dict[str, Any]:
    """Run many satellite-chain configs and return an aggregate summary."""

    output_dir = Path(output_root).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = _normalize_config_rows(config_paths)

    mode = str(backend or "local").strip().lower() or "local"
    if mode not in _ALLOWED_BACKENDS:
        known = ", ".join(sorted(_ALLOWED_BACKENDS))
        raise ValueError(f"unsupported backend {mode!r}; expected one of: {known}")

    timeout_s = _coerce_timeout(job_timeout_s)
    retries = max(0, int(max_retries))

    if mode == "ray":
        run_rows = _run_with_ray(
            rows=rows,
            output_root=output_dir,
            seed=int(seed),
            max_retries=retries,
            job_timeout_s=timeout_s,
            ray_num_cpus=float(ray_num_cpus),
            ray_memory_mb=ray_memory_mb,
            ray_max_in_flight=ray_max_in_flight,
        )
    else:
        run_rows = _run_with_threads(
            rows=rows,
            output_root=output_dir,
            max_workers=int(max_workers),
            seed=int(seed),
            max_retries=retries,
            job_timeout_s=timeout_s,
        )

    _validate_run_rows(run_rows, require_complete=require_complete_results)

    decisions = [
        "HOLD" if str(row.get("status") or "error") != "ok" else str(row.get("decision") or "HOLD")
        for row in run_rows
        if isinstance(row, dict)
    ]
    key_bits_total = sum(
        float(row.get("key_bits_accumulated", 0.0) or 0.0)
        for row in run_rows
        if isinstance(row, dict) and str(row.get("status") or "error") == "ok"
    )
    mean_rates = [
        float(row.get("mean_key_rate_bps", 0.0) or 0.0)
        for row in run_rows
        if isinstance(row, dict) and str(row.get("status") or "error") == "ok"
    ]
    error_count = int(
        sum(1 for row in run_rows if isinstance(row, dict) and str(row.get("status") or "error") != "ok")
    )

    summary = {
        "run_count": int(len(run_rows)),
        "decision_counts": {
            "GO": int(sum(1 for d in decisions if d == "GO")),
            "HOLD": int(sum(1 for d in decisions if d != "GO")),
        },
        "error_count": error_count,
        "key_bits_total": float(key_bits_total),
        "mean_key_rate_bps_avg": float(sum(mean_rates) / len(mean_rates)) if mean_rates else 0.0,
        "backend": mode,
        "seed": int(seed),
        "status": "ok" if error_count == 0 else "failed",
    }

    payload: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_sweep",
        "generated_at": _now_iso(),
        "summary": summary,
        "runs": run_rows,
        "lineage": {
            "seed": int(seed),
            "seed_source": "run_satellite_chain_sweep.seed",
            "seed_strategy": "sha256(base_seed, mission_id, row_index)",
            "input_order_fingerprint": _input_order_fingerprint(rows),
            "backend_metadata": _backend_metadata(mode),
            "execution_policy": {
                "job_timeout_s": timeout_s,
                "max_retries": retries,
                "max_workers": max(1, int(max_workers)),
                "ray_num_cpus": float(ray_num_cpus),
                "ray_memory_mb": float(ray_memory_mb) if ray_memory_mb is not None else None,
                "ray_max_in_flight": int(ray_max_in_flight)
                if ray_max_in_flight is not None
                else None,
                "require_complete_results": bool(require_complete_results),
            },
        },
    }

    _validate_sweep_report_schema_if_available(payload)
    report_path = output_dir / "satellite_chain_sweep.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    tracking = _track_sweep_run(
        payload=payload,
        output_dir=output_dir,
        report_path=report_path,
        tracking_mode=tracking_mode,
        tracking_uri=tracking_uri,
    )
    if tracking is not None:
        lineage_raw = payload.get("lineage")
        lineage = dict(lineage_raw) if isinstance(lineage_raw, dict) else {}
        lineage["tracking"] = tracking
        payload["lineage"] = lineage
        _validate_sweep_report_schema_if_available(payload)
        report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    payload["report_path"] = str(report_path)
    return payload


def _normalize_config_rows(config_paths: list[Path | str]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, raw in enumerate(config_paths):
        cfg_path = Path(raw).expanduser().resolve()
        config = load_config(cfg_path)
        chain = config.get("satellite_qkd_chain") if isinstance(config, dict) else {}
        if not isinstance(chain, dict):
            chain = {}
        mission_id = str(chain.get("id") or cfg_path.stem).strip() or cfg_path.stem
        out.append(
            {
                "row_index": int(index),
                "mission_id": mission_id,
                "config_path": cfg_path,
                "config": config,
                "config_hash": hash_dict(config),
            }
        )
    return out


def _run_with_threads(
    *,
    rows: list[dict[str, Any]],
    output_root: Path,
    max_workers: int,
    seed: int,
    max_retries: int,
    job_timeout_s: float | None,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    workers = max(1, int(max_workers))
    out: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        timeout_label = (
            f"{float(job_timeout_s):.3f}s"
            if job_timeout_s is not None
            else "none"
        )
        futures: dict[int, Any] = {}
        for row in rows:
            row_index = int(row.get("row_index", 0) or 0)
            futures[row_index] = executor.submit(
                _run_one_with_retries,
                row,
                output_root=output_root,
                base_seed=int(seed),
                max_retries=int(max_retries),
            )

        for row in rows:
            row_index = int(row.get("row_index", 0) or 0)
            future = futures[row_index]
            try:
                if job_timeout_s is None:
                    run_row = future.result()
                else:
                    run_row = future.result(timeout=float(job_timeout_s))
            except FuturesTimeoutError:
                run_row = _error_row(
                    row,
                    error=f"job_timeout_exceeded:{timeout_label}",
                    attempts=int(max_retries) + 1,
                    base_seed=int(seed),
                )
            except Exception as exc:  # pragma: no cover - defensive
                run_row = _error_row(
                    row,
                    error=str(exc),
                    attempts=int(max_retries) + 1,
                    base_seed=int(seed),
                )
            out.append(run_row)

    out.sort(
        key=lambda row: (
            str(row.get("mission_id") or ""),
            int(row.get("row_index", 0) or 0),
        )
    )
    return out


def _run_with_ray(
    *,
    rows: list[dict[str, Any]],
    output_root: Path,
    seed: int,
    max_retries: int,
    job_timeout_s: float | None,
    ray_num_cpus: float,
    ray_memory_mb: float | None,
    ray_max_in_flight: int | None,
) -> list[dict[str, Any]]:
    try:
        ray: Any = importlib.import_module("ray")
    except Exception as exc:
        raise RuntimeError("Ray backend requested but ray is not installed. Install with `.[ray]`.") from exc

    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True, include_dashboard=False, log_to_driver=False)

    @ray.remote
    def _ray_run(
        mission_id: str,
        row_index: int,
        config_hash: str,
        config_json: str,
        config_path: str,
        out_root: str,
        base_seed: int,
    ) -> dict[str, Any]:
        payload_raw = json.loads(config_json)
        payload = payload_raw if isinstance(payload_raw, dict) else {}
        payload = _inject_runtime_seed(
            payload,
            mission_id=mission_id,
            row_index=int(row_index),
            base_seed=base_seed,
        )
        mission_seed = _derived_seed(mission_id=mission_id, row_index=int(row_index), base_seed=base_seed)
        out_dir = Path(out_root) / f"{int(row_index):04d}_{mission_id}"
        result = run_satellite_chain(payload, output_dir=out_dir)
        return {
            "row_index": int(row_index),
            "mission_id": mission_id,
            "config_path": str(config_path),
            "config_hash": str(config_hash),
            "decision": str(result.get("decision") or "HOLD").strip().upper(),
            "key_bits_accumulated": float(result.get("key_bits_accumulated", 0.0) or 0.0),
            "mean_key_rate_bps": float(result.get("mean_key_rate_bps", 0.0) or 0.0),
            "output_path": result.get("output_path"),
            "seed": int(mission_seed),
            "status": "ok",
        }

    queue: list[dict[str, Any]] = [
        {
            "row": row,
            "attempt": 1,
        }
        for row in rows
    ]
    pending: dict[Any, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    max_in_flight = max(1, int(ray_max_in_flight) if ray_max_in_flight is not None else len(rows) or 1)

    def _submit(item: dict[str, Any]) -> None:
        row = item["row"]
        row_index = int(row.get("row_index", 0) or 0)
        options: dict[str, Any] = {
            "num_cpus": max(0.1, float(ray_num_cpus)),
        }
        if ray_memory_mb is not None and float(ray_memory_mb) > 0.0:
            options["memory"] = int(float(ray_memory_mb) * 1024 * 1024)
        ref = _ray_run.options(**options).remote(
            str(row.get("mission_id") or "mission"),
            int(row_index),
            str(row.get("config_hash") or ""),
            json.dumps(row.get("config") or {}),
            str(row.get("config_path") or ""),
            str(output_root),
            int(seed),
        )
        pending[ref] = {
            "row": row,
            "attempt": int(item.get("attempt", 1) or 1),
            "started_at": float(time.monotonic()),
        }

    while queue or pending:
        while queue and len(pending) < max_in_flight:
            item = queue.pop(0)
            _submit(item)

        if not pending:
            continue

        ready_refs, _ = ray.wait(list(pending.keys()), num_returns=1, timeout=0.05)
        now = float(time.monotonic())

        if job_timeout_s is not None:
            for ref, state in list(pending.items()):
                started_at = float(state.get("started_at") or now)
                if now - started_at <= float(job_timeout_s):
                    continue
                row = state["row"]
                attempt = int(state.get("attempt", 1) or 1)
                pending.pop(ref, None)
                try:
                    ray.cancel(ref, force=True)
                except Exception:
                    pass
                if attempt <= int(max_retries):
                    queue.append({"row": row, "attempt": attempt + 1})
                else:
                    out.append(
                        _error_row(
                            row,
                            error=f"job_timeout_exceeded:{float(job_timeout_s):.3f}s",
                            attempts=attempt,
                            base_seed=int(seed),
                        )
                    )

        for ref in ready_refs:
            state = pending.pop(ref, None)
            if state is None:
                continue
            row = state["row"]
            attempt = int(state.get("attempt", 1) or 1)
            try:
                result = ray.get(ref)
            except Exception as exc:
                if attempt <= int(max_retries):
                    queue.append({"row": row, "attempt": attempt + 1})
                else:
                    out.append(
                        _error_row(
                            row,
                            error=str(exc),
                            attempts=attempt,
                            base_seed=int(seed),
                        )
                    )
                continue

            normalized = dict(result) if isinstance(result, dict) else {}
            normalized["attempts"] = attempt
            normalized["status"] = "ok"
            out.append(normalized)

    out.sort(
        key=lambda row: (
            str(row.get("mission_id") or ""),
            int(row.get("row_index", 0) or 0),
        )
    )
    return out


def _run_one_with_retries(
    row: dict[str, Any],
    *,
    output_root: Path,
    base_seed: int,
    max_retries: int,
) -> dict[str, Any]:
    attempts_allowed = max(0, int(max_retries)) + 1
    last_error = "unknown"
    for attempt in range(1, attempts_allowed + 1):
        try:
            run_row = _run_one_seeded(row, output_root=output_root, base_seed=base_seed)
            run_row["attempts"] = int(attempt)
            run_row["status"] = "ok"
            return run_row
        except Exception as exc:
            last_error = str(exc)
    return _error_row(
        row,
        error=last_error,
        attempts=attempts_allowed,
        base_seed=int(base_seed),
    )


def _derived_seed(*, mission_id: str, row_index: int, base_seed: int) -> int:
    digest = hashlib.sha256(
        f"{int(base_seed)}:{int(row_index)}:{mission_id}".encode("utf-8")
    ).hexdigest()
    return int(digest[:8], 16)


def _inject_runtime_seed(
    config: dict[str, Any],
    *,
    mission_id: str,
    row_index: int,
    base_seed: int,
) -> dict[str, Any]:
    payload = copy.deepcopy(config)
    sat_raw = payload.get("satellite_qkd_chain")
    if isinstance(sat_raw, dict):
        sat = sat_raw
    else:
        sat = {}
        payload["satellite_qkd_chain"] = sat

    runtime_raw = sat.get("runtime")
    if isinstance(runtime_raw, dict):
        runtime = runtime_raw
    else:
        runtime = {}
        sat["runtime"] = runtime

    runtime["rng_seed"] = int(
        _derived_seed(
            mission_id=mission_id,
            row_index=int(row_index),
            base_seed=base_seed,
        )
    )
    return payload


def _run_one_seeded(row: dict[str, Any], *, output_root: Path, base_seed: int) -> dict[str, Any]:
    mission_id = str(row.get("mission_id") or "mission").strip() or "mission"
    row_index = int(row.get("row_index", 0) or 0)
    config_raw = row.get("config")
    config: dict[str, Any] = dict(config_raw) if isinstance(config_raw, dict) else {}
    cfg_path_raw = row.get("config_path")
    cfg_path = Path(str(cfg_path_raw)) if cfg_path_raw is not None else Path("")
    mission_seed = _derived_seed(
        mission_id=mission_id,
        row_index=int(row_index),
        base_seed=base_seed,
    )
    seeded = _inject_runtime_seed(
        config,
        mission_id=mission_id,
        row_index=int(row_index),
        base_seed=base_seed,
    )
    out_dir = output_root / f"{int(row_index):04d}_{mission_id}"
    result = run_satellite_chain(seeded, output_dir=out_dir)

    return {
        "row_index": int(row_index),
        "mission_id": mission_id,
        "config_path": str(cfg_path),
        "config_hash": str(row.get("config_hash") or hash_dict(config)),
        "decision": str(result.get("decision") or "HOLD").strip().upper(),
        "key_bits_accumulated": float(result.get("key_bits_accumulated", 0.0) or 0.0),
        "mean_key_rate_bps": float(result.get("mean_key_rate_bps", 0.0) or 0.0),
        "output_path": result.get("output_path"),
        "seed": int(mission_seed),
    }


def _error_row(
    row: dict[str, Any],
    *,
    error: str,
    attempts: int,
    base_seed: int,
) -> dict[str, Any]:
    return {
        "row_index": int(row.get("row_index", 0) or 0),
        "mission_id": str(row.get("mission_id") or "mission"),
        "config_path": str(row.get("config_path") or ""),
        "config_hash": str(row.get("config_hash") or ""),
        "decision": "HOLD",
        "key_bits_accumulated": 0.0,
        "mean_key_rate_bps": 0.0,
        "output_path": None,
        "seed": int(
            _derived_seed(
                mission_id=str(row.get("mission_id") or "mission"),
                row_index=int(row.get("row_index", 0) or 0),
                base_seed=int(base_seed),
            )
        ),
        "status": "error",
        "error": str(error),
        "attempts": int(attempts),
    }


def _validate_run_rows(rows: list[dict[str, Any]], *, require_complete: bool) -> None:
    errors: list[str] = []
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"run[{idx}] not an object")
            continue
        status = str(row.get("status") or "error")
        if status != "ok":
            errors.append(
                f"run[{idx}] status={status!r} mission={str(row.get('mission_id') or '')!r} error={str(row.get('error') or '')!r}"
            )
            continue

        decision = str(row.get("decision") or "").strip().upper()
        if decision not in {"GO", "HOLD"}:
            errors.append(f"run[{idx}] invalid decision {decision!r}")

        for key in ("key_bits_accumulated", "mean_key_rate_bps"):
            value = row.get(key)
            parsed = _coerce_float(value)
            if parsed is None:
                errors.append(f"run[{idx}] invalid numeric field {key!r}")
                continue
            if not math.isfinite(parsed):
                errors.append(f"run[{idx}] non-finite numeric field {key!r}")

        output_path = row.get("output_path")
        if output_path is not None and not str(output_path).strip():
            errors.append(f"run[{idx}] output_path is empty string")

    if require_complete and errors:
        sample = "; ".join(errors[:3])
        raise RuntimeError(f"sweep run failed closed due to incomplete/corrupt results: {sample}")


def _coerce_timeout(value: float | None) -> float | None:
    if value is None:
        return None
    timeout = float(value)
    if timeout <= 0.0:
        return None
    return timeout


def _coerce_float(value: Any) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def _backend_metadata(mode: str) -> dict[str, Any]:
    normalized = str(mode).strip().lower() or "local"
    if normalized == "ray":
        try:
            ray = importlib.import_module("ray")
            version = str(getattr(ray, "__version__", "unknown"))
        except Exception:
            version = "unknown"
        return {
            "name": "ray",
            "version": version,
            "python_version": str(sys.version.split()[0]),
        }
    return {
        "name": "local",
        "version": "threadpool",
        "python_version": str(sys.version.split()[0]),
    }


def _input_order_fingerprint(rows: list[dict[str, Any]]) -> str:
    payload = [
        {
            "row_index": int(row.get("row_index", 0) or 0),
            "mission_id": str(row.get("mission_id") or ""),
            "config_path": str(row.get("config_path") or ""),
            "config_hash": str(row.get("config_hash") or ""),
        }
        for row in rows
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _track_sweep_run(
    *,
    payload: dict[str, Any],
    output_dir: Path,
    report_path: Path,
    tracking_mode: str | None,
    tracking_uri: str | None,
) -> dict[str, Any] | None:
    mode = str(tracking_mode or "").strip().lower()
    if not mode or mode == "none":
        return None

    lineage_raw = payload.get("lineage")
    lineage = lineage_raw if isinstance(lineage_raw, dict) else {}
    run_id = "sweep_" + str((str(lineage.get("input_order_fingerprint") or ""))[:12])
    session = start_tracking_session(
        mode=mode,
        output_dir=output_dir / "tracking",
        run_id=run_id,
        tracking_uri=tracking_uri,
    )
    summary_raw = payload.get("summary")
    summary = summary_raw if isinstance(summary_raw, dict) else {}
    session.log_params(
        {
            "backend": summary.get("backend"),
            "seed": summary.get("seed"),
            "run_count": summary.get("run_count"),
            "report_kind": payload.get("kind"),
        }
    )
    session.log_metrics(
        {
            "key_bits_total": float(summary.get("key_bits_total", 0.0) or 0.0),
            "mean_key_rate_bps_avg": float(summary.get("mean_key_rate_bps_avg", 0.0) or 0.0),
            "error_count": float(summary.get("error_count", 0.0) or 0.0),
        },
        step=0,
    )
    session.log_artifact(report_path, name="satellite_chain_sweep.json")
    session.finalize(status="finished")
    return {
        "mode": str(session.mode),
        "run_id": str(session.run_id),
        "tracking_uri": str(session.tracking_uri or ""),
    }


def _validate_sweep_report_schema_if_available(report: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return

    schema_path = satellite_qkd_chain_sweep_schema_path()
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
