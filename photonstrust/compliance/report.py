"""Compliance report builders for ETSI QKD requirements."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.compliance.checkers import float_or_none, normalize_sweep_rows, row_value, scenario_protocol_name
from photonstrust.compliance.registry import get_requirements, get_use_case_requirement, run_requirement
from photonstrust.compliance.types import (
    STATUS_FAIL,
    STATUS_NOT_ASSESSED,
    STATUS_PASS,
    STATUS_WARNING,
    RequirementResult,
)
from photonstrust.evidence.signing import sign_bytes_ed25519
from photonstrust.workflow.schema import etsi_qkd_compliance_report_schema_path


def build_compliance_report(
    sweep_result: Any,
    scenario: dict[str, Any],
    *,
    standards: list[str] | None = None,
    use_case_id: str | None = None,
    k_min_bps: float = 1000.0,
    d_spec_km: float | None = None,
    epsilon_target: float = 1e-10,
    signing_key_path: str | Path | None = None,
) -> dict[str, Any]:
    rows = normalize_sweep_rows(sweep_result)
    normalized_scenario = dict(scenario) if isinstance(scenario, dict) else {}

    context = {
        "k_min_bps": float(k_min_bps),
        "d_spec_km": _resolve_d_spec_km(d_spec_km=d_spec_km, scenario=normalized_scenario, rows=rows),
        "epsilon_target": float(epsilon_target),
        "use_case_id": str(use_case_id).strip() if use_case_id is not None else "",
    }

    requirements = get_requirements(standards)
    if context["use_case_id"]:
        requirements = [*requirements, get_use_case_requirement()]

    requirement_rows: list[RequirementResult] = []
    for req in requirements:
        requirement_rows.append(
            run_requirement(
                req,
                sweep_result=sweep_result,
                scenario=normalized_scenario,
                context=context,
            )
        )

    req_payloads = [_result_to_payload(row) for row in requirement_rows]
    summary = _summary(req_payloads)
    report: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "etsi_qkd_compliance_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standards": sorted({row.standard for row in requirement_rows}),
        "requirements": req_payloads,
        "summary": summary,
        "overall_status": _overall_status(summary),
        "scenario_summary": _scenario_summary(normalized_scenario, rows, context=context),
        "signature": None,
        "hashes": {
            "report_sha256": "",
        },
    }

    report["hashes"]["report_sha256"] = _report_hash(report)

    if signing_key_path is not None:
        key_path = Path(signing_key_path).resolve()
        message = _canonical_json_without_signature(report)
        signature_b64 = sign_bytes_ed25519(private_key_pem_path=key_path, message=message)
        report["signature"] = {
            "algorithm": "ed25519",
            "key_path": str(key_path),
            "signature_b64": signature_b64,
            "message_sha256": hashlib.sha256(message).hexdigest(),
        }
        report["hashes"]["report_sha256"] = _report_hash(report)

    _validate_schema_if_available(report)
    return report


def render_pdf_report(report: dict[str, Any], output_path: Path) -> Path:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except Exception as exc:
        raise RuntimeError("render_pdf_report requires optional dependency 'reportlab'") from exc

    output = Path(output_path).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf = canvas.Canvas(str(output), pagesize=A4)
    width, height = A4
    _ = width
    x = 15 * mm
    y = height - 20 * mm

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x, y, "ETSI QKD Compliance Report")
    y -= 8 * mm

    pdf.setFont("Helvetica", 10)
    pdf.drawString(x, y, f"overall_status: {report.get('overall_status')}")
    y -= 6 * mm
    pdf.drawString(x, y, f"generated_at: {report.get('generated_at')}")
    y -= 8 * mm

    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(x, y, "Requirements")
    y -= 6 * mm
    pdf.setFont("Helvetica", 9)

    requirements = report.get("requirements") if isinstance(report.get("requirements"), list) else []
    for row in requirements:
        if y < 15 * mm:
            pdf.showPage()
            y = height - 20 * mm
            pdf.setFont("Helvetica", 9)
        req = row if isinstance(row, dict) else {}
        line = f"{req.get('req_id', '')} | {req.get('status', '')} | value={req.get('computed_value', None)}"
        pdf.drawString(x, y, line[:145])
        y -= 5 * mm

    pdf.save()
    return output


def _result_to_payload(row: RequirementResult) -> dict[str, Any]:
    return {
        "req_id": row.req_id,
        "standard": row.standard,
        "clause": row.clause,
        "description": row.description,
        "status": row.status,
        "computed_value": row.computed_value,
        "threshold": row.threshold,
        "unit": row.unit,
        "notes": list(row.notes),
    }


def _summary(requirements: list[dict[str, Any]]) -> dict[str, int]:
    pass_count = 0
    fail_count = 0
    warning_count = 0
    not_assessed_count = 0
    for row in requirements:
        status = str(row.get("status", "")).upper()
        if status == STATUS_PASS:
            pass_count += 1
        elif status == STATUS_FAIL:
            fail_count += 1
        elif status == STATUS_WARNING:
            warning_count += 1
        elif status == STATUS_NOT_ASSESSED:
            not_assessed_count += 1

    return {
        "total": int(len(requirements)),
        "pass": int(pass_count),
        "fail": int(fail_count),
        "warning": int(warning_count),
        "not_assessed": int(not_assessed_count),
    }


def _overall_status(summary: dict[str, int]) -> str:
    fail_count = int(summary.get("fail", 0))
    warning_count = int(summary.get("warning", 0))
    na_count = int(summary.get("not_assessed", 0))
    if fail_count > 0:
        return "FAIL"
    if na_count > 0:
        return "PARTIAL"
    if warning_count > 0:
        return "CONDITIONAL_PASS"
    return "PASS"


def _resolve_d_spec_km(*, d_spec_km: float | None, scenario: dict[str, Any], rows: list[dict[str, Any]]) -> float:
    from_arg = float_or_none(d_spec_km)
    if from_arg is not None:
        return float(from_arg)

    from_scenario = float_or_none((scenario or {}).get("distance_km"))
    if from_scenario is not None:
        return float(from_scenario)

    scenario_distances = (scenario or {}).get("distances_km")
    if isinstance(scenario_distances, list):
        parsed = [float_or_none(value) for value in scenario_distances]
        parsed = [d for d in parsed if d is not None]
        if parsed:
            return float(max(parsed))

    distances = [float_or_none(row_value(row, "distance_km", None)) for row in rows]
    distances = [d for d in distances if d is not None]
    if distances:
        return float(max(distances))
    return 50.0


def _scenario_summary(scenario: dict[str, Any], rows: list[dict[str, Any]], *, context: dict[str, Any]) -> dict[str, Any]:
    distances = [float_or_none(row_value(row, "distance_km", None)) for row in rows]
    distances = [float(d) for d in distances if d is not None]
    key_rates = [float_or_none(row_value(row, "key_rate_bps", None)) for row in rows]
    key_rates = [float(v) for v in key_rates if v is not None]
    qbers = [float_or_none(row_value(row, "qber_total", None)) for row in rows]
    qbers = [float(v) for v in qbers if v is not None]

    return {
        "scenario_id": str((scenario or {}).get("scenario_id", "")).strip() or None,
        "protocol": scenario_protocol_name(scenario) or None,
        "target_distance_km": float(context.get("d_spec_km", 50.0)),
        "wavelength_nm": float_or_none((scenario or {}).get("wavelength_nm")),
        "row_count": int(len(rows)),
        "distance_min_km": min(distances) if distances else None,
        "distance_max_km": max(distances) if distances else None,
        "key_rate_min_bps": min(key_rates) if key_rates else None,
        "key_rate_max_bps": max(key_rates) if key_rates else None,
        "qber_min": min(qbers) if qbers else None,
        "qber_max": max(qbers) if qbers else None,
        "k_min_bps": float(context.get("k_min_bps", 1000.0)),
        "epsilon_target": float(context.get("epsilon_target", 1e-10)),
        "use_case_id": str(context.get("use_case_id", "") or "") or None,
    }


def _canonical_json_without_signature(report: dict[str, Any]) -> bytes:
    payload = json.loads(json.dumps(report))
    payload["signature"] = None
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _report_hash(report: dict[str, Any]) -> str:
    payload = json.loads(json.dumps(report))
    hashes = payload.get("hashes")
    if isinstance(hashes, dict):
        hashes["report_sha256"] = ""
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _validate_schema_if_available(report: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return
    schema = json.loads(etsi_qkd_compliance_report_schema_path().read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)
