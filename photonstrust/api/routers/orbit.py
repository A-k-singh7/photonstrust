"""Orbit pass validation and execution routes."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from photonstrust.api import runs as run_store
from photonstrust.api.common import project_id_or_400
from photonstrust.api.common import reject_output_root_override
from photonstrust.api.runtime import generated_at_utc, runtime_provenance
from photonstrust.orbit.diagnostics import validate_orbit_pass_semantics
from photonstrust.orbit.pass_envelope import run_orbit_pass_from_config
from photonstrust.orbit.schema import validate_orbit_pass_config
from photonstrust.utils import hash_dict


router = APIRouter()


def _config_from_payload(payload: Any) -> dict[str, Any]:
    config = payload.get("config") if isinstance(payload, dict) else None
    if not isinstance(config, dict):
        config = payload
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="Expected JSON object for orbit pass config payload")
    return config


def _orbit_outputs_summary(results: dict[str, Any] | None, *, orbit_pass_id: str, band: str) -> dict[str, Any]:
    outputs_summary: dict[str, Any] = {"orbit_pass": {"pass_id": orbit_pass_id, "band": band, "cases": []}}
    if not isinstance(results, dict):
        return outputs_summary

    cases = results.get("cases", []) or []
    if isinstance(cases, list):
        out_cases = []
        for case in cases:
            if not isinstance(case, dict):
                continue
            summary = case.get("summary", {}) or {}
            if not isinstance(summary, dict):
                summary = {}
            out_cases.append(
                {
                    "case_id": case.get("case_id"),
                    "label": case.get("label"),
                    "total_keys_bits": summary.get("total_keys_bits"),
                    "expected_total_keys_bits": summary.get("expected_total_keys_bits"),
                    "avg_key_rate_bps": summary.get("avg_key_rate_bps"),
                    "min_key_rate_bps": summary.get("min_key_rate_bps"),
                    "max_key_rate_bps": summary.get("max_key_rate_bps"),
                    "avg_channel_outage_probability": summary.get("avg_channel_outage_probability"),
                    "max_channel_outage_probability": summary.get("max_channel_outage_probability"),
                    "background_model": summary.get("background_model"),
                    "background_day_night": summary.get("background_day_night"),
                    "avg_background_counts_cps": summary.get("avg_background_counts_cps"),
                    "max_background_counts_cps": summary.get("max_background_counts_cps"),
                    "finite_key": summary.get("finite_key"),
                }
            )
        outputs_summary["orbit_pass"]["cases"] = out_cases

    trust = results.get("trust_label", {}) or {}
    if isinstance(trust, dict):
        outputs_summary["orbit_pass"]["trust_label"] = {
            "mode": trust.get("mode"),
            "label": trust.get("label"),
            "regime": trust.get("regime"),
        }

    finite_key = results.get("finite_key", {}) or {}
    if isinstance(finite_key, dict):
        outputs_summary["orbit_pass"]["finite_key"] = {
            "enabled": finite_key.get("enabled"),
            "effective_signals_per_block": finite_key.get("effective_signals_per_block"),
            "signals_per_pass_budget": finite_key.get("signals_per_pass_budget"),
            "security_epsilon": finite_key.get("security_epsilon"),
            "pass_duration_s": finite_key.get("pass_duration_s"),
        }
    return outputs_summary


@router.post("/v0/orbit/pass/validate")
def orbit_pass_validate(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    config = _config_from_payload(payload)
    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    try:
        validate_orbit_pass_config(config, require_jsonschema=require_schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "generated_at": generated_at_utc(),
        "config_hash": hash_dict(config),
        "diagnostics": validate_orbit_pass_semantics(config),
        "provenance": runtime_provenance(),
    }


@router.post("/v0/orbit/pass/run")
def orbit_pass_run(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    config = _config_from_payload(payload)
    require_schema = bool(payload.get("require_schema", False)) if isinstance(payload, dict) else False
    reject_output_root_override(payload)
    project_id = project_id_or_400(payload)

    run_id = uuid.uuid4().hex[:12]
    run_dir = run_store.run_dir_for_id(run_id)
    try:
        validate_orbit_pass_config(config, require_jsonschema=require_schema)
        diagnostics = validate_orbit_pass_semantics(config)
        artifacts = run_orbit_pass_from_config(config, run_dir)
        results_path = Path(str(artifacts.get("results_path", "")))
        results = json.loads(results_path.read_text(encoding="utf-8")) if results_path.exists() else None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated_at = generated_at_utc()
    config = dict(config)
    orbit_pass_raw = config.get("orbit_pass")
    orbit_pass: dict[str, Any] = orbit_pass_raw if isinstance(orbit_pass_raw, dict) else {}
    orbit_pass_id = str(orbit_pass.get("id", "")).strip()
    band = str(orbit_pass.get("band", "")).strip()
    report_rel = f"{orbit_pass_id}/{band}/orbit_pass_report.html" if orbit_pass_id and band else None
    results_rel = f"{orbit_pass_id}/{band}/orbit_pass_results.json" if orbit_pass_id and band else None

    manifest = {
        "schema_version": "0.1",
        "run_id": run_id,
        "run_type": "orbit_pass",
        "generated_at": generated_at,
        "output_dir": str(run_dir),
        "input": {
            "project_id": project_id,
            "config_hash": hash_dict(config),
            "orbit_pass_id": orbit_pass_id,
            "band": band,
        },
        "outputs_summary": _orbit_outputs_summary(results, orbit_pass_id=orbit_pass_id, band=band),
        "artifacts": {
            "orbit_pass_report_html": report_rel,
            "orbit_pass_results_json": results_rel,
        },
        "provenance": runtime_provenance(),
    }
    manifest_path = run_store.write_run_manifest(run_dir, manifest)

    return {
        "generated_at": generated_at,
        "run_id": run_id,
        "config_hash": hash_dict(config),
        "output_dir": str(artifacts.get("output_dir", "")),
        "results_path": str(artifacts.get("results_path", "")),
        "report_html_path": str(artifacts.get("report_html_path", "")),
        "diagnostics": diagnostics,
        "results": results,
        "manifest_path": str(manifest_path),
        "artifact_relpaths": {
            "orbit_pass_report_html": report_rel,
            "orbit_pass_results_json": results_rel,
        },
        "provenance": runtime_provenance(),
    }
