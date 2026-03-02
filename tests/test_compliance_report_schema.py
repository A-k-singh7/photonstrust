from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pytest

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.qkd import compute_sweep

compliance_report_mod = pytest.importorskip("photonstrust.compliance.report", exc_type=ImportError)
build_compliance_report = compliance_report_mod.build_compliance_report
render_pdf_report = compliance_report_mod.render_pdf_report


def _base_scenario() -> dict[str, Any]:
    return {
        "scenario_id": "compliance_schema_base",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [50.0],
        "source": {
            "type": "wcp",
            "rep_rate_mhz": 200.0,
            "collection_efficiency": 1.0,
            "coupling_efficiency": 0.9,
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.75,
            "dark_counts_cps": 100.0,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 20.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {
            "sync_drift_ps_rms": 5.0,
            "coincidence_window_ps": 200.0,
        },
        "protocol": {
            "name": "BB84_DECOY",
            "mu": 0.5,
            "nu": 0.1,
            "omega": 0.0,
            "sifting_factor": 0.5,
            "ec_efficiency": 1.16,
            "misalignment_prob": 0.01,
        },
        "uncertainty": {},
    }


def _unwrap_report(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict) and isinstance(raw.get("report"), dict):
        return dict(raw["report"])
    if isinstance(raw, dict):
        return dict(raw)
    raise TypeError("compliance report must be an object")


def _invoke_build_report(*, scenario: dict[str, Any], sweep_result: dict[str, Any]) -> dict[str, Any]:
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
            return _unwrap_report(fn(**kwargs))
        except TypeError:
            pass
    for args in ((scenario, sweep_result), (scenario,), (sweep_result, scenario), (sweep_result,)):
        try:
            return _unwrap_report(fn(*args))
        except TypeError:
            continue
    raise RuntimeError("Unable to call build_compliance_report")


def _invoke_render_pdf(*, report: dict[str, Any], pdf_path: Path) -> Path:
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


def test_compliance_report_schema_validation() -> None:
    try:
        import photonstrust.workflow.schema as schema_mod
    except Exception as exc:  # pragma: no cover - defensive import
        pytest.skip(f"workflow schema module unavailable: {exc}")

    if not hasattr(schema_mod, "etsi_qkd_compliance_report_schema_path"):
        pytest.skip("etsi_qkd_compliance_report_schema_path helper is not available yet")

    scenario = _base_scenario()
    sweep = compute_sweep(scenario, include_uncertainty=False)
    report = _invoke_build_report(scenario=scenario, sweep_result=sweep)

    schema_path = schema_mod.etsi_qkd_compliance_report_schema_path()
    validate_instance(report, schema_path)


def test_compliance_pdf_generation_writes_non_empty_file(tmp_path: Path) -> None:
    pytest.importorskip("reportlab")

    scenario = _base_scenario()
    sweep = compute_sweep(scenario, include_uncertainty=False)
    report = _invoke_build_report(scenario=scenario, sweep_result=sweep)

    pdf_path = tmp_path / "compliance_report.pdf"
    written_path = _invoke_render_pdf(report=report, pdf_path=pdf_path)
    assert written_path.exists()
    assert written_path.stat().st_size > 0
