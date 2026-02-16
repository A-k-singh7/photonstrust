"""Inverse design by tuning a single coupler coupling ratio (1D grid search)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from photonstrust.invdesign._robust import (
    evaluate_robust_objective,
    normalize_robustness,
    set_node_param,
)
from photonstrust.invdesign.plugin_boundary import resolve_invdesign_solver_metadata


@dataclass(frozen=True)
class CouplerRatioDesignResult:
    coupler_node_id: str
    best_coupling_ratio: float
    objective: float
    achieved_fraction: float
    target_output: dict[str, str]
    wavelengths_nm: list[float]
    updated_netlist: dict[str, Any]
    report: dict[str, Any]


def inverse_design_coupler_ratio(
    netlist: dict,
    *,
    coupler_node_id: str,
    target_output_node: str,
    target_output_port: str,
    target_power_fraction: float,
    wavelengths_nm: list[float] | None = None,
    steps: int = 101,
    robustness_cases: list[dict[str, Any]] | None = None,
    wavelength_objective_agg: str = "mean",
    case_objective_agg: str = "mean",
    robustness_required: bool = False,
    robustness_thresholds: dict[str, Any] | None = None,
    execution_mode: str = "preview",
    solver_backend: str = "core",
    solver_plugin: dict[str, Any] | None = None,
) -> CouplerRatioDesignResult:
    """Tune one `pic.coupler` node's `coupling_ratio` to hit a target output fraction."""

    if not isinstance(netlist, dict):
        raise TypeError("netlist must be an object")

    coupler_node_id = str(coupler_node_id).strip()
    if not coupler_node_id:
        raise ValueError("coupler_node_id is required")

    target_output_node = str(target_output_node).strip()
    target_output_port = str(target_output_port).strip()
    if not target_output_node or not target_output_port:
        raise ValueError("target_output_node and target_output_port are required")

    target_power_fraction = float(target_power_fraction)
    if not math.isfinite(target_power_fraction):
        raise ValueError("target_power_fraction must be finite")
    target_power_fraction = max(0.0, min(1.0, target_power_fraction))

    if wavelengths_nm is None:
        wl = (netlist.get("circuit", {}) or {}).get("wavelength_nm", 1550.0)
        wavelengths_nm = [float(wl) if wl is not None else 1550.0]
    wavelengths_nm = [float(w) for w in wavelengths_nm if float(w) > 0]
    if not wavelengths_nm:
        raise ValueError("wavelengths_nm must be non-empty")

    steps = int(steps)
    steps = max(16, min(4096, steps))

    robustness = normalize_robustness(
        robustness_cases,
        wavelength_objective_agg=wavelength_objective_agg,
        case_objective_agg=case_objective_agg,
        required=robustness_required,
        thresholds=robustness_thresholds,
    )
    solver_meta = resolve_invdesign_solver_metadata(solver_backend=solver_backend, solver_plugin=solver_plugin)

    # Locate the coupler node.
    nodes = netlist.get("nodes", []) or []
    found = None
    for n in nodes:
        if not isinstance(n, dict):
            continue
        if str(n.get("id", "")).strip() == coupler_node_id:
            found = n
            break
    if not found:
        raise ValueError(f"coupler_node_id not found in netlist: {coupler_node_id}")
    if str(found.get("kind", "")).strip().lower() != "pic.coupler":
        raise ValueError("coupler_node_id must refer to a pic.coupler node")

    points: list[dict[str, Any]] = []
    best_kappa = 0.5
    best_obj = float("inf")
    best_fraction = 0.0
    best_eval: dict[str, Any] | None = None

    # Include endpoints [0,1] for easier interpretation.
    denom = float(steps - 1) if steps > 1 else 1.0
    for i in range(steps):
        kappa = float(i) / denom
        ev = evaluate_robust_objective(
            netlist,
            design_node_id=coupler_node_id,
            design_param="coupling_ratio",
            design_value=float(kappa),
            target_node=target_output_node,
            target_port=target_output_port,
            target_power_fraction=target_power_fraction,
            wavelengths_nm=wavelengths_nm,
            robustness=robustness,
        )
        obj = float(ev["objective"])
        frac = float(ev["achieved_fraction_nominal_mean"])
        metrics = (ev.get("robustness_eval") or {}).get("metrics") if isinstance(ev.get("robustness_eval"), dict) else {}
        if not isinstance(metrics, dict):
            metrics = {}
        points.append(
            {
                "value": float(kappa),
                "objective": obj,
                "achieved_fraction_nominal_mean": float(frac),
                "objective_case_max": float(metrics.get("objective_case_max", obj) or obj),
                "worst_case_achieved_fraction": float(metrics.get("worst_case_achieved_fraction", frac) or frac),
            }
        )
        if obj < best_obj:
            best_obj = obj
            best_kappa = float(kappa)
            best_fraction = float(frac)
            best_eval = ev

    updated = set_node_param(netlist, node_id=coupler_node_id, param="coupling_ratio", value=float(best_kappa))
    if best_eval is None:
        best_eval = evaluate_robust_objective(
            netlist,
            design_node_id=coupler_node_id,
            design_param="coupling_ratio",
            design_value=float(best_kappa),
            target_node=target_output_node,
            target_port=target_output_port,
            target_power_fraction=target_power_fraction,
            wavelengths_nm=wavelengths_nm,
            robustness=robustness,
        )

    report = {
        "schema_version": "0.1",
        "kind": "pic.invdesign.coupler_ratio",
        "inputs": {
            "target_output": {"node": target_output_node, "port": target_output_port},
            "target_power_fraction": target_power_fraction,
            "wavelengths_nm": list(wavelengths_nm),
            "steps": steps,
            "robustness": {
                "wavelength_objective_agg": robustness.wavelength_objective_agg,
                "case_objective_agg": robustness.case_objective_agg,
                "required": bool(robustness.required),
                "thresholds": dict(robustness.thresholds),
                "cases": [{"id": cs.id, "label": cs.label, "overrides": cs.overrides} for cs in robustness.cases],
            },
        },
        "execution": {
            "mode": str(execution_mode or "preview").strip().lower() or "preview",
            "solver": solver_meta,
        },
        "design": {
            "node_id": coupler_node_id,
            "param": "coupling_ratio",
            "search": {"method": "grid", "steps": steps, "bounds": [0.0, 1.0]},
        },
        "best": {
            "value": best_kappa,
            "objective": best_obj,
            "achieved_fraction_nominal_mean": best_fraction,
            "robustness_eval": best_eval["robustness_eval"],
        },
        "curve": points,
    }
    return CouplerRatioDesignResult(
        coupler_node_id=coupler_node_id,
        best_coupling_ratio=best_kappa,
        objective=best_obj,
        achieved_fraction=best_fraction,
        target_output={"node": target_output_node, "port": target_output_port},
        wavelengths_nm=list(wavelengths_nm),
        updated_netlist=updated,
        report=report,
    )
