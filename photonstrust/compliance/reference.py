"""Deterministic compliance baselines for regression locking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from photonstrust.compliance.report import build_compliance_report
from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep


DEFAULT_CONFIGS: tuple[str, ...] = (
    "configs/compliance/compliant_bb84_snspd.yml",
    "configs/compliance/marginal_bb84_ingaas.yml",
    "configs/compliance/noncompliant_high_qber.yml",
)


def build_reference_fixture(
    repo_root: Path,
    *,
    config_paths: list[Path] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    selected = config_paths if config_paths is not None else [root / rel for rel in DEFAULT_CONFIGS]
    cases: list[dict[str, Any]] = []
    for config_path in selected:
        path = Path(config_path).resolve()
        config = load_config(path)
        scenarios = build_scenarios(config)
        if not scenarios:
            raise ValueError(f"No scenarios produced by config: {path}")
        scenario = dict(scenarios[0])
        sweep = compute_sweep(scenario, include_uncertainty=False)
        report = build_compliance_report(sweep, scenario)
        cases.append(
            {
                "config": str(path.relative_to(root)).replace("\\", "/"),
                "report": canonicalize_report(report),
            }
        )

    cases.sort(key=lambda row: row["config"])
    return {
        "kind": "photonstrust.compliance_reference_baselines.v0",
        "cases": cases,
    }


def canonicalize_report(report: dict[str, Any]) -> dict[str, Any]:
    payload = report if isinstance(report, dict) else {}
    requirements = payload.get("requirements")
    req_rows: list[dict[str, Any]] = []
    if isinstance(requirements, list):
        for row in requirements:
            if not isinstance(row, dict):
                continue
            req_rows.append(
                {
                    "req_id": str(row.get("req_id") or ""),
                    "status": str(row.get("status") or ""),
                    "computed_value": _stable(row.get("computed_value")),
                    "threshold": _stable(row.get("threshold")),
                    "unit": _stable(row.get("unit")),
                    "notes": _stable(row.get("notes")),
                }
            )
    req_rows.sort(key=lambda row: row["req_id"])

    scenario_summary = payload.get("scenario_summary")
    scenario = scenario_summary if isinstance(scenario_summary, dict) else {}

    standards_raw = payload.get("standards")
    standards = [str(value) for value in standards_raw] if isinstance(standards_raw, list) else []
    standards.sort()

    return {
        "kind": str(payload.get("kind") or ""),
        "schema_version": str(payload.get("schema_version") or ""),
        "standards": standards,
        "overall_status": str(payload.get("overall_status") or ""),
        "summary": _stable(payload.get("summary")),
        "scenario_summary": {
            "protocol": _stable(scenario.get("protocol")),
            "target_distance_km": _stable(scenario.get("target_distance_km")),
            "wavelength_nm": _stable(scenario.get("wavelength_nm")),
            "row_count": _stable(scenario.get("row_count")),
            "key_rate_min_bps": _stable(scenario.get("key_rate_min_bps")),
            "key_rate_max_bps": _stable(scenario.get("key_rate_max_bps")),
            "qber_min": _stable(scenario.get("qber_min")),
            "qber_max": _stable(scenario.get("qber_max")),
        },
        "requirements": req_rows,
    }


def _stable(value: Any) -> Any:
    if isinstance(value, float):
        if value != value:
            return None
        return float(f"{value:.12g}")
    if isinstance(value, list):
        return [_stable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _stable(value[key]) for key in sorted(value)}
    return value
