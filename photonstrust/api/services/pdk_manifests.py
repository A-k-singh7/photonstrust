"""Helpers for resolving and persisting PDK manifest context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from photonstrust.api import runs as run_store
from photonstrust.api.common import safe_read_json_object
from photonstrust.api.runtime import generated_at_utc
from photonstrust.pdk import resolve_pdk_contract


def extract_pdk_request_from_manifest(manifest: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(manifest, dict):
        return None

    input_obj = manifest.get("input") if isinstance(manifest.get("input"), dict) else {}
    raw_pdk = input_obj.get("pdk")
    if isinstance(raw_pdk, str) and raw_pdk.strip():
        return {"name": raw_pdk.strip()}

    if isinstance(raw_pdk, dict):
        out: dict[str, Any] = {}
        name = raw_pdk.get("name")
        if isinstance(name, str) and name.strip():
            out["name"] = name.strip()
        manifest_path = raw_pdk.get("manifest_path")
        if isinstance(manifest_path, str) and manifest_path.strip():
            out["manifest_path"] = manifest_path.strip()
        if out:
            return out

    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    pic_layout = outputs.get("pic_layout") if isinstance(outputs.get("pic_layout"), dict) else {}
    pdk_name = pic_layout.get("pdk")
    if isinstance(pdk_name, str) and pdk_name.strip():
        return {"name": pdk_name.strip()}
    return None


def build_pdk_manifest_payload(
    pdk_request: dict[str, Any] | None,
    *,
    execution_mode: str,
    source_run_id: str | None = None,
) -> dict[str, Any]:
    contract = resolve_pdk_contract(pdk_request if isinstance(pdk_request, dict) else {})

    source_id = None
    if isinstance(source_run_id, str) and source_run_id.strip():
        try:
            source_id = run_store.validate_run_id(source_run_id)
        except Exception:
            source_id = None

    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pdk_manifest",
        "generated_at": generated_at_utc(),
        "execution_mode": execution_mode,
        "source_run_id": source_id,
        "adapter": str(contract.get("adapter", "registry.v0") or "registry.v0"),
        "request": {
            "name": (contract.get("request") or {}).get("name"),
            "manifest_path": (contract.get("request") or {}).get("manifest_path"),
        },
        "pdk": {
            "name": (contract.get("pdk") or {}).get("name"),
            "version": (contract.get("pdk") or {}).get("version"),
            "design_rules": dict(((contract.get("pdk") or {}).get("design_rules") or {})),
            "notes": list(((contract.get("pdk") or {}).get("notes") or [])),
        },
        "capabilities": {
            "supports_layout": bool(((contract.get("capabilities") or {}).get("supports_layout", True))),
            "supports_performance_drc": bool(((contract.get("capabilities") or {}).get("supports_performance_drc", True))),
            "supports_lvs_lite_signoff": bool(
                ((contract.get("capabilities") or {}).get("supports_lvs_lite_signoff", True))
            ),
            "supports_spice_export": bool(((contract.get("capabilities") or {}).get("supports_spice_export", True))),
        },
    }


def coerce_pdk_manifest_payload(
    payload: dict[str, Any] | None,
    *,
    execution_mode: str,
    source_run_id: str | None = None,
) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None

    out = dict(payload)
    request = out.get("request") if isinstance(out.get("request"), dict) else {}
    req_name = request.get("name")
    req_manifest = request.get("manifest_path")
    out["request"] = {
        "name": str(req_name).strip() if isinstance(req_name, str) and req_name.strip() else None,
        "manifest_path": str(req_manifest).strip() if isinstance(req_manifest, str) and req_manifest.strip() else None,
    }

    pdk = out.get("pdk") if isinstance(out.get("pdk"), dict) else None
    if not isinstance(pdk, dict) or not str(pdk.get("name", "")).strip():
        try:
            return build_pdk_manifest_payload(out.get("request"), execution_mode=execution_mode, source_run_id=source_run_id)
        except Exception:
            return None

    out["pdk"] = {
        "name": str(pdk.get("name", "")).strip(),
        "version": str(pdk.get("version", "0")).strip() or "0",
        "design_rules": dict(pdk.get("design_rules") if isinstance(pdk.get("design_rules"), dict) else {}),
        "notes": [str(note) for note in (pdk.get("notes") if isinstance(pdk.get("notes"), list) else [])],
    }

    capabilities = out.get("capabilities") if isinstance(out.get("capabilities"), dict) else {}
    out["capabilities"] = {
        "supports_layout": bool(capabilities.get("supports_layout", True)),
        "supports_performance_drc": bool(capabilities.get("supports_performance_drc", True)),
        "supports_lvs_lite_signoff": bool(capabilities.get("supports_lvs_lite_signoff", True)),
        "supports_spice_export": bool(capabilities.get("supports_spice_export", True)),
    }

    resolved_source_run_id = None
    if isinstance(source_run_id, str) and source_run_id.strip():
        try:
            resolved_source_run_id = run_store.validate_run_id(source_run_id)
        except Exception:
            resolved_source_run_id = None
    elif isinstance(out.get("source_run_id"), str) and str(out.get("source_run_id") or "").strip():
        try:
            resolved_source_run_id = run_store.validate_run_id(str(out.get("source_run_id")))
        except Exception:
            resolved_source_run_id = None

    out["schema_version"] = "0.1"
    out["kind"] = "photonstrust.pdk_manifest"
    out["generated_at"] = (
        str(out.get("generated_at")).strip()
        if isinstance(out.get("generated_at"), str) and str(out.get("generated_at")).strip()
        else generated_at_utc()
    )
    out["execution_mode"] = execution_mode
    out["source_run_id"] = resolved_source_run_id
    out["adapter"] = str(out.get("adapter", "registry.v0") or "registry.v0").strip() or "registry.v0"
    return out


def load_pdk_manifest_from_run(run_dir: Path) -> dict[str, Any] | None:
    manifest = run_store.read_run_manifest(run_dir)
    if not isinstance(manifest, dict):
        return None

    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    rel = artifacts.get("pdk_manifest_json")
    if isinstance(rel, str) and rel.strip():
        try:
            path = run_store.resolve_artifact_path(run_dir, str(rel).strip())
        except Exception:
            path = None
        if isinstance(path, Path):
            payload = safe_read_json_object(path)
            if isinstance(payload, dict):
                return payload

    request = extract_pdk_request_from_manifest(manifest)
    if isinstance(request, dict):
        return build_pdk_manifest_payload(
            request,
            execution_mode="preview",
            source_run_id=str(manifest.get("run_id", "")).strip() or None,
        )
    return None


def resolve_run_pdk_manifest(
    *,
    pdk_request: dict[str, Any] | None,
    execution_mode: str,
    source_run_dir: Path | None = None,
    source_run_id: str | None = None,
    require_context_in_cert: bool,
) -> dict[str, Any] | None:
    payload = None
    if isinstance(source_run_dir, Path):
        payload = load_pdk_manifest_from_run(source_run_dir)

    if payload is None and isinstance(pdk_request, dict):
        payload = build_pdk_manifest_payload(
            pdk_request,
            execution_mode=execution_mode,
            source_run_id=source_run_id,
        )

    if payload is None:
        if execution_mode == "certification" and require_context_in_cert:
            return None
        payload = build_pdk_manifest_payload({}, execution_mode=execution_mode, source_run_id=source_run_id)

    return coerce_pdk_manifest_payload(payload, execution_mode=execution_mode, source_run_id=source_run_id)


def write_pdk_manifest_artifact(run_dir: Path, payload: dict[str, Any]) -> str:
    rel = "pdk_manifest.json"
    (Path(run_dir) / rel).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return rel
