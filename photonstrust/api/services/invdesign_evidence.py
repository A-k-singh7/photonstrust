"""Inverse-design evidence validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import HTTPException

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.invdesign.schema import invdesign_report_schema_path


INVDESIGN_REQUIRED_ARTIFACT_KEYS = ("invdesign_report_json", "optimized_graph_json")


def validate_invdesign_report_schema_or_400(report: dict[str, Any], *, require_jsonschema: bool) -> None:
    try:
        validate_instance(report, invdesign_report_schema_path(), require_jsonschema=require_jsonschema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invdesign evidence schema validation failed: {exc}") from exc


def invdesign_certification_evidence_issues(report: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    inputs = report.get("inputs") if isinstance(report.get("inputs"), dict) else {}
    robustness = inputs.get("robustness") if isinstance(inputs.get("robustness"), dict) else {}
    cases = robustness.get("cases") if isinstance(robustness.get("cases"), list) else []
    if not bool(robustness.get("required", False)):
        issues.append("inputs.robustness.required must be true in certification mode")
    if len(cases) < 2:
        issues.append("inputs.robustness.cases must include at least two cases in certification mode")

    best = report.get("best") if isinstance(report.get("best"), dict) else {}
    robustness_eval = best.get("robustness_eval") if isinstance(best.get("robustness_eval"), dict) else {}
    if not isinstance(robustness_eval.get("worst_case"), dict):
        issues.append("best.robustness_eval.worst_case is required in certification mode")
    threshold_eval = robustness_eval.get("threshold_eval") if isinstance(robustness_eval.get("threshold_eval"), dict) else None
    if not isinstance(threshold_eval, dict):
        issues.append("best.robustness_eval.threshold_eval is required in certification mode")
    elif not isinstance(threshold_eval.get("pass"), bool):
        issues.append("best.robustness_eval.threshold_eval.pass must be boolean")

    execution = report.get("execution") if isinstance(report.get("execution"), dict) else {}
    if str(execution.get("mode", "")).strip().lower() != "certification":
        issues.append("execution.mode must be 'certification' in certification runs")
    solver = execution.get("solver") if isinstance(execution.get("solver"), dict) else {}
    if not str(solver.get("backend_requested", "")).strip():
        issues.append("execution.solver.backend_requested is required")
    if not str(solver.get("backend_used", "")).strip():
        issues.append("execution.solver.backend_used is required")

    return issues


def enforce_invdesign_evidence_or_400(
    *,
    report: dict[str, Any],
    run_dir: Path,
    artifact_relpaths: dict[str, Any],
    execution_mode: str,
) -> None:
    validate_invdesign_report_schema_or_400(report, require_jsonschema=(execution_mode == "certification"))

    missing_artifacts: list[str] = []
    for key in INVDESIGN_REQUIRED_ARTIFACT_KEYS:
        rel = artifact_relpaths.get(key)
        if not isinstance(rel, str) or not rel.strip():
            missing_artifacts.append(key)
            continue
        artifact_path = Path(run_dir) / rel
        if not artifact_path.exists() or not artifact_path.is_file():
            missing_artifacts.append(key)
    if missing_artifacts:
        raise HTTPException(
            status_code=400,
            detail=f"invdesign evidence artifacts missing: {', '.join(sorted(missing_artifacts))}",
        )

    if execution_mode == "certification":
        issues = invdesign_certification_evidence_issues(report)
        if issues:
            raise HTTPException(
                status_code=400,
                detail=f"certification mode requires complete inverse-design evidence: {'; '.join(issues)}",
            )
