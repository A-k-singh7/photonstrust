#!/usr/bin/env python3
"""Run three compliance fixtures and emit compact JSON summary."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from typing import Any

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep

try:
    from photonstrust.compliance.report import build_compliance_report, render_pdf_report
except Exception as exc:  # pragma: no cover - environment-dependent
    print(json.dumps({"ok": False, "error": f"compliance_api_unavailable: {exc}"}))
    raise SystemExit(2)


def _invoke_build_compliance_report(*, scenario: dict[str, Any], sweep_result: dict[str, Any]) -> dict[str, Any]:
    fn = build_compliance_report
    sig = inspect.signature(fn)
    params = sig.parameters

    kwargs: dict[str, Any] = {}
    if "scenario" in params:
        kwargs["scenario"] = scenario
    if "sweep_result" in params:
        kwargs["sweep_result"] = sweep_result
    if "sweep" in params:
        kwargs["sweep"] = sweep_result
    if "sweep_rows" in params:
        kwargs["sweep_rows"] = list(sweep_result.get("results") or [])
    if "target_distance_km" in params:
        kwargs["target_distance_km"] = float((scenario.get("distances_km") or [0.0])[-1])

    if kwargs:
        try:
            raw = fn(**kwargs)
            return _unwrap_report(raw)
        except TypeError:
            pass

    last_exc: Exception | None = None
    for args in ((scenario, sweep_result), (scenario,), (sweep_result, scenario), (sweep_result,)):
        try:
            raw = fn(*args)
            return _unwrap_report(raw)
        except TypeError as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("unable to call build_compliance_report")


def _invoke_render_pdf_report(*, report: dict[str, Any], pdf_path: Path) -> Path:
    fn = render_pdf_report
    sig = inspect.signature(fn)
    params = sig.parameters

    kwargs: dict[str, Any] = {}
    if "report" in params:
        kwargs["report"] = report
    if "output_path" in params:
        kwargs["output_path"] = str(pdf_path)
    elif "pdf_path" in params:
        kwargs["pdf_path"] = str(pdf_path)
    elif "path" in params:
        kwargs["path"] = str(pdf_path)

    if kwargs:
        out = fn(**kwargs)
    else:
        out = fn(report, str(pdf_path))
    if isinstance(out, (str, Path)):
        return Path(out)
    return pdf_path


def _unwrap_report(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and isinstance(raw.get("report"), dict):
        return dict(raw["report"])
    if isinstance(raw, dict):
        return dict(raw)
    raise TypeError("compliance report must be a JSON object")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    configs = [
        repo_root / "configs" / "compliance" / "compliant_bb84_snspd.yml",
        repo_root / "configs" / "compliance" / "marginal_bb84_ingaas.yml",
        repo_root / "configs" / "compliance" / "noncompliant_high_qber.yml",
    ]
    output_root = (repo_root / "results" / "compliance_demo").resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for cfg_path in configs:
        config = load_config(cfg_path)
        scenarios = build_scenarios(config)
        if not scenarios:
            raise RuntimeError(f"no scenarios built from config: {cfg_path}")
        scenario = dict(scenarios[0])
        sweep = compute_sweep(scenario, include_uncertainty=False)
        report = _invoke_build_compliance_report(scenario=scenario, sweep_result=sweep)

        stem = cfg_path.stem
        report_path = output_root / f"{stem}.compliance_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

        pdf_path = output_root / f"{stem}.compliance_report.pdf"
        try:
            final_pdf_path = _invoke_render_pdf_report(report=report, pdf_path=pdf_path)
            pdf_written = bool(final_pdf_path.exists()) and final_pdf_path.stat().st_size > 0
        except Exception:
            final_pdf_path = pdf_path
            pdf_written = False

        rows.append(
            {
                "config": str(cfg_path.relative_to(repo_root)),
                "report_json": str(report_path.relative_to(repo_root)),
                "report_pdf": str(final_pdf_path.relative_to(repo_root)),
                "overall_status": str(report.get("overall_status") or "UNKNOWN"),
                "pdf_written": bool(pdf_written),
            }
        )

    print(
        json.dumps(
            {
                "ok": True,
                "output_root": str(output_root.relative_to(repo_root)),
                "cases": rows,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
