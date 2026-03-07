"""Helpers for foundry-sealed API routes."""

from __future__ import annotations

import re
from typing import Any

from fastapi import HTTPException

from photonstrust.api import foundry_metrics as foundry_metrics_store


_SEALED_RUN_ID_RE = re.compile(r"^[a-z0-9_]{8,64}$")
_FOUNDRY_DRC_ALLOWED_BACKENDS = {"mock", "generic_cli", "local_rules", "local"}
_FOUNDRY_LVS_ALLOWED_BACKENDS = {"mock", "generic_cli", "local_lvs", "local"}
_FOUNDRY_PEX_ALLOWED_BACKENDS = {"mock", "generic_cli", "local_pex", "local"}
_UNTRUSTED_BACKENDS = {"mock", "stub"}


def parse_optional_sealed_run_id(payload: dict[str, Any], *, field_name: str = "run_id") -> str | None:
    raw = payload.get(field_name)
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise HTTPException(status_code=400, detail=f"{field_name} must be a string when provided")
    run_id = raw.strip().lower()
    if not run_id:
        return None
    if not _SEALED_RUN_ID_RE.fullmatch(run_id):
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} must match ^[a-z0-9_]{{8,64}}$ when provided",
        )
    return run_id


def _parse_foundry_backend(
    payload: dict[str, Any],
    *,
    execution_mode: str,
    stage_label: str,
    allowed_backends: set[str],
) -> str:
    backend = str(payload.get("backend", "mock") or "mock").strip().lower() or "mock"
    if backend not in allowed_backends:
        raise HTTPException(status_code=400, detail=f"backend must be one of: {', '.join(sorted(allowed_backends))}")
    if execution_mode == "certification" and backend in _UNTRUSTED_BACKENDS:
        raise HTTPException(
            status_code=400,
            detail=f"certification mode requires non-mock backend for foundry {stage_label.upper()}",
        )
    return backend


def parse_foundry_drc_backend(payload: dict[str, Any], *, execution_mode: str) -> str:
    return _parse_foundry_backend(
        payload,
        execution_mode=execution_mode,
        stage_label="drc",
        allowed_backends=_FOUNDRY_DRC_ALLOWED_BACKENDS,
    )


def parse_foundry_lvs_backend(payload: dict[str, Any], *, execution_mode: str) -> str:
    return _parse_foundry_backend(
        payload,
        execution_mode=execution_mode,
        stage_label="lvs",
        allowed_backends=_FOUNDRY_LVS_ALLOWED_BACKENDS,
    )


def parse_foundry_pex_backend(payload: dict[str, Any], *, execution_mode: str) -> str:
    return _parse_foundry_backend(
        payload,
        execution_mode=execution_mode,
        stage_label="pex",
        allowed_backends=_FOUNDRY_PEX_ALLOWED_BACKENDS,
    )


def enforce_foundry_certification_provenance(summary: dict[str, Any], *, stage_label: str) -> None:
    stage = stage_label.lower()
    backend = str(summary.get("execution_backend") or "").strip().lower()
    if not backend or backend in _UNTRUSTED_BACKENDS:
        raise HTTPException(status_code=400, detail=f"certification mode requires trusted execution_backend for foundry {stage}")

    counts = summary.get("check_counts") if isinstance(summary.get("check_counts"), dict) else {}
    total = int(counts.get("total", 0) or 0)
    if total <= 0:
        raise HTTPException(status_code=400, detail=f"certification mode requires non-empty check_counts for foundry {stage}")

    deck_fingerprint = str(summary.get("deck_fingerprint") or "").strip()
    if not deck_fingerprint:
        raise HTTPException(status_code=400, detail=f"certification mode requires deck_fingerprint for foundry {stage}")


def append_foundry_metric_event(*, stage: str, run_id: str, summary: dict[str, Any]) -> None:
    try:
        event = foundry_metrics_store.build_foundry_metric_event(stage=stage, run_id=run_id, summary=summary)
        foundry_metrics_store.append_foundry_metric_event(event)
    except Exception:
        return
