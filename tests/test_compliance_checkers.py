from __future__ import annotations

import copy
import inspect
from typing import Any

import pytest

from photonstrust.qkd import compute_sweep

compliance_report_mod = pytest.importorskip("photonstrust.compliance.report", exc_type=ImportError)
build_compliance_report = compliance_report_mod.build_compliance_report


def _base_scenario() -> dict[str, Any]:
    return {
        "scenario_id": "compliance_checker_base",
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


def _invoke_build_report(*, scenario: dict[str, Any], sweep_result: dict[str, Any] | None = None) -> dict[str, Any]:
    fn = build_compliance_report
    if sweep_result is None:
        sweep_result = compute_sweep(scenario, include_uncertainty=False)

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

    last_exc: Exception | None = None
    for args in ((scenario, sweep_result), (scenario,), (sweep_result, scenario), (sweep_result,)):
        try:
            return _unwrap_report(fn(*args))
        except TypeError as exc:
            last_exc = exc
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unable to call build_compliance_report")


def _req_status(report: dict[str, Any], requirement_id: str) -> str:
    req_upper = str(requirement_id).upper()
    for row in list(report.get("requirements") or []):
        if not isinstance(row, dict):
            continue
        rid = ""
        for key in ("id", "requirement_id", "req_id"):
            if str(row.get(key) or "").strip():
                rid = str(row.get(key)).strip()
                break
        rid_upper = rid.upper()
        if rid_upper == req_upper or rid_upper.endswith(req_upper):
            return str(row.get("status") or "").strip().upper()
    raise AssertionError(f"Requirement not present in report: {requirement_id}")


def test_f1_pass_fail_boundary() -> None:
    s_pass = _base_scenario()
    s_pass["distances_km"] = [5.0]

    s_fail = _base_scenario()
    s_fail["distances_km"] = [250.0]
    s_fail["channel"]["fiber_loss_db_per_km"] = 0.4
    s_fail["source"]["coupling_efficiency"] = 0.2
    s_fail["detector"]["pde"] = 0.05

    report_pass = _invoke_build_report(scenario=s_pass)
    report_fail = _invoke_build_report(scenario=s_fail)

    assert _req_status(report_pass, "GS-QKD-004-F1") == "PASS"
    assert _req_status(report_fail, "GS-QKD-004-F1") == "FAIL"


def test_f2_pass_fail_boundary() -> None:
    s_pass = _base_scenario()
    s_pass["protocol"]["misalignment_prob"] = 0.01

    s_fail = _base_scenario()
    s_fail["protocol"]["misalignment_prob"] = 0.25
    s_fail["detector"]["dark_counts_cps"] = 5e4

    report_pass = _invoke_build_report(scenario=s_pass)
    report_fail = _invoke_build_report(scenario=s_fail)

    assert _req_status(report_pass, "GS-QKD-004-F2") == "PASS"
    assert _req_status(report_fail, "GS-QKD-004-F2") == "FAIL"


def test_s2_boundary_prefers_sweep_single_photon_error_ub_when_available() -> None:
    s_low = _base_scenario()
    sweep_low = compute_sweep(s_low, include_uncertainty=False)
    sweep_low_mod = copy.deepcopy(sweep_low)
    for row in list(sweep_low_mod.get("results") or []):
        if isinstance(row, dict):
            row["single_photon_error_ub"] = 0.499
    s_low["protocol"]["single_photon_error_ub"] = 0.499

    s_high = _base_scenario()
    sweep_high = compute_sweep(s_high, include_uncertainty=False)
    sweep_high_mod = copy.deepcopy(sweep_high)
    for row in list(sweep_high_mod.get("results") or []):
        if isinstance(row, dict):
            row["single_photon_error_ub"] = 0.501
    s_high["protocol"]["single_photon_error_ub"] = 0.501

    report_pass = _invoke_build_report(scenario=s_low, sweep_result=sweep_low_mod)
    report_fail = _invoke_build_report(scenario=s_high, sweep_result=sweep_high_mod)

    assert _req_status(report_pass, "GS-QKD-008-S2") == "PASS"
    assert _req_status(report_fail, "GS-QKD-008-S2") == "FAIL"


def test_s3_mu_boundary_pass_warning_fail() -> None:
    s_pass = _base_scenario()
    s_pass["protocol"]["mu"] = 0.59

    s_warn = _base_scenario()
    s_warn["protocol"]["mu"] = 0.61

    s_fail = _base_scenario()
    s_fail["protocol"]["mu"] = 1.01

    report_pass = _invoke_build_report(scenario=s_pass)
    report_warn = _invoke_build_report(scenario=s_warn)
    report_fail = _invoke_build_report(scenario=s_fail)

    assert _req_status(report_pass, "GS-QKD-008-S3") == "PASS"
    assert _req_status(report_warn, "GS-QKD-008-S3") in {"WARNING", "WARN"}
    assert _req_status(report_fail, "GS-QKD-008-S3") == "FAIL"


def test_c2_dcr_boundary_pass_fail() -> None:
    s_pass = _base_scenario()
    s_pass["detector"]["dark_counts_cps"] = 9999

    s_fail = _base_scenario()
    s_fail["detector"]["dark_counts_cps"] = 10001

    report_pass = _invoke_build_report(scenario=s_pass)
    report_fail = _invoke_build_report(scenario=s_fail)

    assert _req_status(report_pass, "GS-QKD-011-C2") == "PASS"
    assert _req_status(report_fail, "GS-QKD-011-C2") == "FAIL"


def test_c4_jitter_penalty_classification() -> None:
    s_pass = _base_scenario()
    s_pass["detector"]["jitter_ps_fwhm"] = 30

    s_warn = _base_scenario()
    s_warn["detector"]["jitter_ps_fwhm"] = 170

    s_fail = _base_scenario()
    s_fail["detector"]["jitter_ps_fwhm"] = 220

    report_pass = _invoke_build_report(scenario=s_pass)
    report_warn = _invoke_build_report(scenario=s_warn)
    report_fail = _invoke_build_report(scenario=s_fail)

    assert _req_status(report_pass, "GS-QKD-011-C4") == "PASS"
    assert _req_status(report_warn, "GS-QKD-011-C4") in {"WARNING", "WARN"}
    assert _req_status(report_fail, "GS-QKD-011-C4") == "FAIL"
