"""Deterministic WS4 nightly flow scaffolding with optional Prefect support."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

DETERMINISTIC_GENERATED_AT = "2026-03-02T00:00:00Z"
_PREFECT_MISSING_MESSAGE = (
    "Prefect mode requested but Prefect is not installed. "
    "Install optional dependency `prefect` to run mode=prefect."
)

try:  # pragma: no cover - depends on optional environment dependency
    from prefect import flow as _prefect_flow

    PREFECT_AVAILABLE = True
except Exception:  # pragma: no cover - depends on optional environment dependency
    _prefect_flow = None
    PREFECT_AVAILABLE = False


FLOW_NAME_BY_JOB = {
    "satellite": "nightly_satellite",
    "corner": "nightly_corner",
    "compliance": "nightly_compliance",
}


def _normalize_flow(flow: str) -> str:
    key = str(flow).strip().lower()
    if key not in FLOW_NAME_BY_JOB:
        allowed = ", ".join(sorted(FLOW_NAME_BY_JOB))
        raise ValueError(f"unsupported flow '{flow}', expected one of: {allowed}")
    return key


def _build_local_result(*, flow: str, output_dir: Path, config: Path | None, mode: str) -> dict:
    flow_key = _normalize_flow(flow)
    flow_name = FLOW_NAME_BY_JOB[flow_key]
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = output_dir / f"{flow_key}_nightly_summary.json"
    result = {
        "status": "ok",
        "flow_name": flow_name,
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "artifact_paths": {
            "summary_json": str(artifact_path),
        },
        "mode": str(mode),
        "config_path": str(config.resolve()) if config is not None else None,
    }
    artifact_payload = {
        "kind": "ws4_nightly_flow_artifact",
        "flow": flow_key,
        "flow_name": flow_name,
        "generated_at": DETERMINISTIC_GENERATED_AT,
        "config_path": result["config_path"],
    }
    artifact_path.write_text(json.dumps(artifact_payload, sort_keys=True), encoding="utf-8")
    return result


def _prefect_unavailable_callable(*args: object, **kwargs: object) -> dict:
    _ = args, kwargs
    raise RuntimeError(_PREFECT_MISSING_MESSAGE)


if PREFECT_AVAILABLE:

    @_prefect_flow(name=FLOW_NAME_BY_JOB["satellite"])
    def satellite_prefect_flow(*, output_dir: str, config_path: str | None = None) -> dict:
        return _build_local_result(
            flow="satellite",
            output_dir=Path(output_dir),
            config=Path(config_path) if config_path else None,
            mode="prefect",
        )


    @_prefect_flow(name=FLOW_NAME_BY_JOB["corner"])
    def corner_prefect_flow(*, output_dir: str, config_path: str | None = None) -> dict:
        return _build_local_result(
            flow="corner",
            output_dir=Path(output_dir),
            config=Path(config_path) if config_path else None,
            mode="prefect",
        )


    @_prefect_flow(name=FLOW_NAME_BY_JOB["compliance"])
    def compliance_prefect_flow(*, output_dir: str, config_path: str | None = None) -> dict:
        return _build_local_result(
            flow="compliance",
            output_dir=Path(output_dir),
            config=Path(config_path) if config_path else None,
            mode="prefect",
        )

else:
    satellite_prefect_flow = _prefect_unavailable_callable
    corner_prefect_flow = _prefect_unavailable_callable
    compliance_prefect_flow = _prefect_unavailable_callable


_PREFECT_ENTRYPOINTS: dict[str, Callable[..., dict]] = {
    "satellite": satellite_prefect_flow,
    "corner": corner_prefect_flow,
    "compliance": compliance_prefect_flow,
}


def run_nightly_flow(*, flow: str, output_dir: Path, config: Path | None = None, mode: str = "local") -> dict:
    flow_key = _normalize_flow(flow)
    selected_mode = str(mode).strip().lower()
    if selected_mode == "local":
        return _build_local_result(flow=flow_key, output_dir=output_dir, config=config, mode="local")
    if selected_mode != "prefect":
        raise ValueError(f"unsupported mode '{mode}', expected one of: local, prefect")
    if not PREFECT_AVAILABLE:
        raise RuntimeError(_PREFECT_MISSING_MESSAGE)
    return _PREFECT_ENTRYPOINTS[flow_key](
        output_dir=str(Path(output_dir).resolve()),
        config_path=str(Path(config).resolve()) if config is not None else None,
    )


def run_satellite_nightly(*, output_dir: Path, config: Path | None = None, mode: str = "local") -> dict:
    return run_nightly_flow(flow="satellite", output_dir=output_dir, config=config, mode=mode)


def run_corner_nightly(*, output_dir: Path, config: Path | None = None, mode: str = "local") -> dict:
    return run_nightly_flow(flow="corner", output_dir=output_dir, config=config, mode=mode)


def run_compliance_nightly(*, output_dir: Path, config: Path | None = None, mode: str = "local") -> dict:
    return run_nightly_flow(flow="compliance", output_dir=output_dir, config=config, mode=mode)
