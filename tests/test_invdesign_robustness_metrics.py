from __future__ import annotations

import pytest

from photonstrust.graph.compiler import compile_graph
from photonstrust.invdesign._robust import evaluate_robust_objective, normalize_robustness
from photonstrust.invdesign.coupler_ratio import inverse_design_coupler_ratio


def _coupler_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "inv_phase58_robust_cpl",
        "profile": "pic_circuit",
        "metadata": {"title": "inv_phase58_robust_cpl", "description": "", "created_at": "2026-02-16"},
        "circuit": {
            "id": "inv_phase58_robust_cpl",
            "wavelength_nm": 1550.0,
            "inputs": [
                {"node": "cpl", "port": "in1", "amplitude": 1.0},
                {"node": "cpl", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [{"id": "cpl", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.0}}],
        "edges": [],
    }


def test_normalize_robustness_requires_explicit_corners_in_required_mode() -> None:
    with pytest.raises(ValueError):
        normalize_robustness(None, required=True)

    with pytest.raises(ValueError):
        normalize_robustness(
            [{"id": "nominal", "label": "Nominal", "overrides": {}}],
            required=True,
        )


def test_evaluate_robust_objective_emits_worst_case_and_threshold_eval() -> None:
    netlist = dict(compile_graph(_coupler_graph(), require_schema=False).compiled)

    robustness = normalize_robustness(
        [
            {"id": "nominal", "label": "Nominal", "overrides": {}},
            {"id": "corner_fast", "label": "Fast", "overrides": {"cpl": {"coupling_ratio": 0.40}}},
        ],
        case_objective_agg="max",
        required=True,
        thresholds={
            "min_worst_case_fraction": 0.40,
            "max_objective": 1.0,
            "max_degradation_from_nominal": 0.50,
        },
    )

    ev = evaluate_robust_objective(
        netlist,
        design_node_id="cpl",
        design_param="coupling_ratio",
        design_value=0.10,
        target_node="cpl",
        target_port="out1",
        target_power_fraction=0.85,
        wavelengths_nm=[1550.0],
        robustness=robustness,
    )

    robust_eval = ev["robustness_eval"]
    assert isinstance(robust_eval.get("worst_case"), dict)
    assert isinstance(robust_eval.get("metrics"), dict)
    assert isinstance(robust_eval.get("threshold_eval"), dict)
    assert isinstance((robust_eval.get("threshold_eval") or {}).get("pass"), bool)
    assert (robust_eval.get("metrics") or {}).get("objective_case_max") is not None


def test_invdesign_coupler_report_contains_solver_boundary_and_robust_curve_metrics() -> None:
    netlist = dict(compile_graph(_coupler_graph(), require_schema=False).compiled)

    result = inverse_design_coupler_ratio(
        netlist,
        coupler_node_id="cpl",
        target_output_node="cpl",
        target_output_port="out1",
        target_power_fraction=0.85,
        wavelengths_nm=[1550.0],
        steps=24,
        robustness_cases=[
            {"id": "nominal", "label": "Nominal", "overrides": {}},
            {"id": "corner_slow", "label": "Slow", "overrides": {"cpl": {"coupling_ratio": 0.60}}},
        ],
        robustness_required=True,
        robustness_thresholds={
            "min_worst_case_fraction": 0.30,
            "max_objective": 1.0,
            "max_degradation_from_nominal": 0.70,
        },
        execution_mode="certification",
        solver_backend="adjoint_gpl",
        solver_plugin={
            "plugin_id": "ext.adjoint.demo",
            "plugin_version": "0.1",
            "license_class": "copyleft",
            "available": False,
        },
    )

    report = result.report
    solver = ((report.get("execution") or {}).get("solver") or {})
    assert solver.get("backend_requested") == "adjoint_gpl"
    assert solver.get("backend_used") == "core"
    assert (solver.get("applicability") or {}).get("status") == "fallback"
    assert solver.get("fallback_reason") == "plugin_unavailable"
    assert solver.get("license_class") == "copyleft"

    curve = report.get("curve") or []
    assert curve
    first = curve[0]
    assert "objective_case_max" in first
    assert "worst_case_achieved_fraction" in first
