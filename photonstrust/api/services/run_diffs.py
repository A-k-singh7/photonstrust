"""Run diff helpers for manifest comparisons."""

from __future__ import annotations

from typing import Any

from photonstrust.api import runs as run_store
from photonstrust.api.diff import diff_json, diff_violations


def _violation_rows_or_none(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, list):
        return None
    out = [item for item in value if isinstance(item, dict)]
    if out:
        return out
    return [] if not value else None


def extract_violation_rows(value: Any) -> list[dict[str, Any]] | None:
    if not isinstance(value, dict):
        return None

    for key in ("violations_annotated", "violations"):
        rows = _violation_rows_or_none(value.get(key))
        if rows is not None:
            return rows

    for child in value.values():
        if isinstance(child, dict):
            rows = extract_violation_rows(child)
            if rows is not None:
                return rows
    return None


def extract_interop_view(manifest: dict[str, Any]) -> dict[str, Any]:
    outputs = manifest.get("outputs_summary") if isinstance(manifest.get("outputs_summary"), dict) else {}
    qkd = outputs.get("qkd") if isinstance(outputs.get("qkd"), dict) else None
    if isinstance(qkd, dict):
        cards = qkd.get("cards") if isinstance(qkd.get("cards"), list) else []
        first = cards[0] if cards and isinstance(cards[0], dict) else {}
        return {
            "source": "native",
            "protocol_selected": qkd.get("protocol_selected"),
            "key_rate_bps": first.get("key_rate_bps"),
            "qber": first.get("qber"),
        }

    ext = outputs.get("qkd_external_import") if isinstance(outputs.get("qkd_external_import"), dict) else None
    if isinstance(ext, dict):
        return {
            "source": "external_import",
            "protocol_selected": ext.get("protocol_selected"),
            "key_rate_bps": ext.get("key_rate_bps"),
            "qber": ext.get("qber_total"),
        }
    return {}


def interop_diff(lhs_manifest: dict[str, Any], rhs_manifest: dict[str, Any]) -> dict[str, Any] | None:
    lhs = extract_interop_view(lhs_manifest)
    rhs = extract_interop_view(rhs_manifest)
    if not lhs or not rhs:
        return None

    try:
        key_rate_delta = float(rhs.get("key_rate_bps")) - float(lhs.get("key_rate_bps"))
    except Exception:
        key_rate_delta = None
    try:
        qber_delta = float(rhs.get("qber")) - float(lhs.get("qber"))
    except Exception:
        qber_delta = None

    return {
        "lhs_source": lhs.get("source"),
        "rhs_source": rhs.get("source"),
        "lhs_protocol_selected": lhs.get("protocol_selected"),
        "rhs_protocol_selected": rhs.get("protocol_selected"),
        "key_rate_bps_delta": key_rate_delta,
        "qber_delta": qber_delta,
    }


def build_runs_diff_payload(
    *,
    lhs_manifest: dict[str, Any],
    rhs_manifest: dict[str, Any],
    scope: str,
    limit: int,
) -> dict[str, Any]:
    if scope == "input":
        lhs_obj = lhs_manifest.get("input", {})
        rhs_obj = rhs_manifest.get("input", {})
    elif scope == "outputs_summary":
        lhs_obj = lhs_manifest.get("outputs_summary", {})
        rhs_obj = rhs_manifest.get("outputs_summary", {})
    else:
        lhs_obj = lhs_manifest
        rhs_obj = rhs_manifest
    if not isinstance(lhs_obj, dict):
        lhs_obj = {}
    if not isinstance(rhs_obj, dict):
        rhs_obj = {}

    diff = diff_json(lhs_obj, rhs_obj, limit=limit)
    violation_diff = None
    if scope in ("outputs_summary", "all"):
        lhs_outputs = lhs_manifest.get("outputs_summary", {}) if isinstance(lhs_manifest, dict) else {}
        rhs_outputs = rhs_manifest.get("outputs_summary", {}) if isinstance(rhs_manifest, dict) else {}
        lhs_rows = extract_violation_rows(lhs_outputs)
        rhs_rows = extract_violation_rows(rhs_outputs)
        if lhs_rows is not None and rhs_rows is not None:
            violation_diff = diff_violations(lhs_rows, rhs_rows)

    payload: dict[str, Any] = {
        "changes": diff.get("changes", []),
        "summary": {
            "change_count": len(diff.get("changes", []) or []),
            "truncated": bool(diff.get("truncated", False)),
        },
    }
    if violation_diff is not None:
        payload["violation_diff"] = violation_diff
    interop = interop_diff(lhs_manifest, rhs_manifest)
    if interop is not None:
        payload["interop_diff"] = interop

    return {
        "lhs": run_store.summarize_manifest(lhs_manifest),
        "rhs": run_store.summarize_manifest(rhs_manifest),
        "diff": payload,
    }
