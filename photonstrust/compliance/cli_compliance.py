"""CLI bridge for ETSI compliance checks."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from typing import Any

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep

_PIC_CERT_KIND = "photonstrust.pic_qkd_certificate"
_REPORT_FORMATS = {"json", "pdf", "text"}


def run_compliance_check(
    input_path: Path,
    *,
    standards: list[str] | None,
    use_case_id: str | None,
    k_min_bps: float,
    d_spec_km: float | None,
    output_path: Path | None,
    output_format: str,
    signing_key: Path | None,
    strict: bool,
) -> dict:
    """Build a compliance report from scenario YAML or PIC-QKD certificate JSON."""

    path = Path(input_path).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Input path does not exist: {path}")

    normalized_format = str(output_format or "json").strip().lower()
    if normalized_format not in _REPORT_FORMATS:
        supported = ", ".join(sorted(_REPORT_FORMATS))
        raise ValueError(f"Unsupported output format {output_format!r}. Expected one of: {supported}")

    qkd_scenario: dict[str, Any]
    qkd_sweep: dict[str, Any]
    input_kind: str

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        config = load_config(path)
        scenarios = build_scenarios(config)
        if not scenarios:
            raise ValueError(f"Scenario config produced no scenarios: {path}")
        scenario = scenarios[0]
        if not isinstance(scenario, dict):
            raise ValueError(f"First scenario is not a mapping in config: {path}")
        qkd_scenario = scenario
        qkd_sweep = compute_sweep(qkd_scenario, include_uncertainty=False)
        if not isinstance(qkd_sweep, dict):
            raise ValueError("compute_sweep() returned a non-dict payload")
        input_kind = "scenario_yaml"
    elif suffix == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or str(raw.get("kind") or "").strip() != _PIC_CERT_KIND:
            raise ValueError(
                "JSON input must be a PIC QKD certificate payload with "
                f"kind={_PIC_CERT_KIND!r}: {path}"
            )
        cert_sweep = raw.get("qkd_sweep")
        cert_scenario = raw.get("qkd_scenario")
        if not isinstance(cert_scenario, dict):
            raise ValueError(f"Certificate is missing required dict field 'qkd_scenario': {path}")
        if not isinstance(cert_sweep, dict):
            raise ValueError(
                "Certificate is missing required dict field 'qkd_sweep' "
                "(certificate may have been generated in dry-run mode): "
                f"{path}"
            )
        qkd_scenario = cert_scenario
        qkd_sweep = cert_sweep
        input_kind = "pic_qkd_certificate"
    else:
        raise ValueError(
            "Unsupported input type. Expected a scenario YAML config (*.yml/*.yaml) "
            f"or a PIC certificate JSON (*.json), got: {path}"
        )

    from photonstrust.compliance.report import build_compliance_report, render_pdf_report

    standards_norm = _normalize_standards(standards)
    use_case_norm = str(use_case_id).strip() if use_case_id else None
    signing_key_norm = Path(signing_key).expanduser().resolve() if signing_key else None

    report = _call_build_compliance_report(
        build_compliance_report,
        qkd_sweep=qkd_sweep,
        qkd_scenario=qkd_scenario,
        standards=standards_norm,
        use_case_id=use_case_norm,
        k_min_bps=float(k_min_bps),
        d_spec_km=float(d_spec_km) if d_spec_km is not None else None,
        signing_key=signing_key_norm,
    )
    if not isinstance(report, dict):
        raise ValueError("build_compliance_report() returned a non-dict payload")

    output_json: Path | None = None
    if output_path is not None and normalized_format in _REPORT_FORMATS:
        output_json = Path(output_path).expanduser().resolve()
        output_json.parent.mkdir(parents=True, exist_ok=True)
        output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    pdf_path: Path | None = None
    if normalized_format == "pdf":
        pdf_path = (
            output_json.with_suffix(".pdf")
            if output_json is not None
            else path.parent / f"{path.stem}_compliance_report.pdf"
        )
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        render_pdf_report(report, pdf_path)

    failure_count = _failure_count(report)
    has_failures = failure_count > 0
    strict_violation = bool(strict) and has_failures

    return {
        "input_path": str(path),
        "input_kind": input_kind,
        "output_format": normalized_format,
        "output_path": str(output_json) if output_json is not None else None,
        "pdf_path": str(pdf_path) if pdf_path is not None else None,
        "has_failures": bool(has_failures),
        "failure_count": int(failure_count),
        "strict_violation": bool(strict_violation),
        "report": report,
    }


def _call_build_compliance_report(
    build_fn: Any,
    *,
    qkd_sweep: dict[str, Any],
    qkd_scenario: dict[str, Any],
    standards: list[str] | None,
    use_case_id: str | None,
    k_min_bps: float,
    d_spec_km: float | None,
    signing_key: Path | None,
) -> dict[str, Any]:
    candidate_by_param = {
        "sweep_result": qkd_sweep,
        "qkd_sweep": qkd_sweep,
        "sweep": qkd_sweep,
        "scenario": qkd_scenario,
        "qkd_scenario": qkd_scenario,
        "standards": standards,
        "use_case_id": use_case_id,
        "k_min_bps": float(k_min_bps),
        "d_spec_km": d_spec_km,
        "signing_key": str(signing_key) if signing_key is not None else None,
        "signing_key_path": str(signing_key) if signing_key is not None else None,
    }

    try:
        signature = inspect.signature(build_fn)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        kwargs: dict[str, Any] = {}
        for name, param in signature.parameters.items():
            if param.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
                continue
            if name in candidate_by_param:
                value = candidate_by_param[name]
                if value is None and param.default is inspect.Parameter.empty:
                    continue
                kwargs[name] = value
        try:
            built = build_fn(**kwargs)
            if isinstance(built, dict):
                return built
        except TypeError:
            pass

    try:
        built_fallback = build_fn(
            qkd_sweep,
            qkd_scenario,
            standards=standards,
            use_case_id=use_case_id,
            k_min_bps=float(k_min_bps),
            d_spec_km=d_spec_km,
            signing_key=str(signing_key) if signing_key is not None else None,
        )
    except TypeError:
        built_fallback = build_fn(qkd_sweep, qkd_scenario)
    if not isinstance(built_fallback, dict):
        raise ValueError("build_compliance_report() fallback call returned non-dict payload")
    return built_fallback


def _normalize_standards(standards: list[str] | None) -> list[str] | None:
    if not standards:
        return None
    out: list[str] = []
    seen: set[str] = set()
    for raw in standards:
        for part in str(raw).split(","):
            value = part.strip()
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
    return out or None


def _failure_count(report: dict[str, Any]) -> int:
    summary = report.get("summary")
    if isinstance(summary, dict):
        for key in ("fail", "failed", "failure_count", "fail_count"):
            raw = summary.get(key)
            if raw is None:
                continue
            try:
                count = int(raw)
            except (TypeError, ValueError):
                continue
            if count > 0:
                return count

    overall_status = str(report.get("overall_status") or report.get("status") or "").strip().upper()
    if overall_status in {"FAIL", "FAILED"}:
        return 1

    requirements = report.get("requirements")
    if isinstance(requirements, list):
        failed = 0
        for row in requirements:
            if not isinstance(row, dict):
                continue
            status = str(row.get("status") or "").strip().upper()
            if status == "FAIL":
                failed += 1
        if failed > 0:
            return failed

    return 0
