"""Robustness utilities for inverse-design primitives.

We treat "robustness" as:
- a list of named cases (corners) expressed as per-node parameter overrides
- plus explicit objective aggregation rules.

This is intentionally compact-model friendly and solver-agnostic so it can be
reused by future EM/adjoint plugin backends.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal

from photonstrust.pic.simulate import simulate_pic_netlist

AggMode = Literal["mean", "max"]


@dataclass(frozen=True)
class RobustnessCase:
    id: str
    label: str
    overrides: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class RobustnessConfig:
    wavelength_objective_agg: AggMode
    case_objective_agg: AggMode
    cases: list[RobustnessCase]
    nominal_case_id: str
    required: bool
    thresholds: dict[str, float | None]


def _to_finite_float(value: Any, *, field: str) -> float:
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{field} must be finite")
    return out


def _normalize_thresholds(raw: dict[str, Any] | None) -> dict[str, float | None]:
    thresholds = raw if isinstance(raw, dict) else {}

    min_worst_case_fraction = None
    max_objective = None
    max_degradation_from_nominal = None

    if thresholds.get("min_worst_case_fraction") is not None:
        min_worst_case_fraction = _to_finite_float(
            thresholds.get("min_worst_case_fraction"),
            field="robustness_thresholds.min_worst_case_fraction",
        )
        if not (0.0 <= min_worst_case_fraction <= 1.0):
            raise ValueError("robustness_thresholds.min_worst_case_fraction must be between 0 and 1")

    if thresholds.get("max_objective") is not None:
        max_objective = _to_finite_float(
            thresholds.get("max_objective"),
            field="robustness_thresholds.max_objective",
        )
        if max_objective < 0.0:
            raise ValueError("robustness_thresholds.max_objective must be >= 0")

    if thresholds.get("max_degradation_from_nominal") is not None:
        max_degradation_from_nominal = _to_finite_float(
            thresholds.get("max_degradation_from_nominal"),
            field="robustness_thresholds.max_degradation_from_nominal",
        )
        if not (0.0 <= max_degradation_from_nominal <= 1.0):
            raise ValueError("robustness_thresholds.max_degradation_from_nominal must be between 0 and 1")

    return {
        "min_worst_case_fraction": min_worst_case_fraction,
        "max_objective": max_objective,
        "max_degradation_from_nominal": max_degradation_from_nominal,
    }


def _agg(values: list[float], mode: AggMode) -> float:
    if not values:
        return 0.0
    if mode == "mean":
        return float(sum(values) / len(values))
    if mode == "max":
        return float(max(values))
    raise ValueError(f"Unsupported agg mode: {mode}")


def normalize_robustness(
    robustness_cases: list[dict[str, Any]] | None,
    *,
    wavelength_objective_agg: str = "mean",
    case_objective_agg: str = "mean",
    max_cases: int = 64,
    required: bool = False,
    thresholds: dict[str, Any] | None = None,
) -> RobustnessConfig:
    w = str(wavelength_objective_agg or "mean").strip().lower()
    c = str(case_objective_agg or "mean").strip().lower()
    if w not in ("mean", "max"):
        raise ValueError("wavelength_objective_agg must be 'mean' or 'max'")
    if c not in ("mean", "max"):
        raise ValueError("case_objective_agg must be 'mean' or 'max'")

    required = bool(required)
    thresholds_out = _normalize_thresholds(thresholds)

    cases_in = robustness_cases or []
    if not isinstance(cases_in, list):
        raise TypeError("robustness_cases must be a list of case objects")

    cases: list[RobustnessCase] = []
    ids: set[str] = set()
    for idx, raw in enumerate(cases_in):
        if not isinstance(raw, dict):
            continue
        cid = str(raw.get("id", "")).strip() or f"case_{idx}"
        if cid in ids:
            raise ValueError(f"Duplicate robustness case id: {cid}")
        label = str(raw.get("label", cid)).strip() or cid
        overrides_raw = raw.get("overrides", {})
        overrides: dict[str, dict[str, Any]] = {}
        if isinstance(overrides_raw, dict):
            for node_id, ov in overrides_raw.items():
                nid = str(node_id).strip()
                if not nid:
                    continue
                if isinstance(ov, dict):
                    overrides[nid] = {str(k): v for k, v in ov.items()}
        cases.append(RobustnessCase(id=cid, label=label, overrides=overrides))
        ids.add(cid)
        if len(cases) >= int(max_cases):
            break

    if not cases:
        if required:
            raise ValueError("robustness_required=true requires explicit robustness_cases")
        cases = [RobustnessCase(id="nominal", label="Nominal", overrides={})]

    if required and len(cases) < 2:
        raise ValueError("robustness_required=true requires at least two robustness_cases")

    nominal = "nominal" if any(cs.id == "nominal" for cs in cases) else cases[0].id
    return RobustnessConfig(
        wavelength_objective_agg=w,  # type: ignore[arg-type]
        case_objective_agg=c,  # type: ignore[arg-type]
        cases=cases,
        nominal_case_id=nominal,
        required=required,
        thresholds=thresholds_out,
    )


def apply_param_overrides(netlist: dict, overrides_by_node: dict[str, dict[str, Any]] | None) -> dict:
    if not overrides_by_node:
        return dict(netlist)
    out = dict(netlist)
    nodes_out = []
    for n in (netlist.get("nodes", []) or []):
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id", "")).strip()
        ov = overrides_by_node.get(nid)
        if not (isinstance(ov, dict) and ov):
            nodes_out.append(n)
            continue
        params = n.get("params", {}) or {}
        if not isinstance(params, dict):
            params = {}
        merged = dict(params)
        merged.update({str(k): v for k, v in ov.items()})
        nodes_out.append({**n, "params": merged})
    out["nodes"] = nodes_out
    return out


def set_node_param(netlist: dict, *, node_id: str, param: str, value: Any) -> dict:
    out = dict(netlist)
    nodes_out = []
    for n in (netlist.get("nodes", []) or []):
        if not isinstance(n, dict):
            continue
        if str(n.get("id", "")).strip() != node_id:
            nodes_out.append(n)
            continue
        params = n.get("params", {}) or {}
        if not isinstance(params, dict):
            params = {}
        merged = dict(params)
        merged[str(param)] = value
        nodes_out.append({**n, "params": merged})
    out["nodes"] = nodes_out
    return out


def output_power_fraction_by_wavelength(
    netlist: dict,
    *,
    target_node: str,
    target_port: str,
    wavelengths_nm: list[float],
) -> list[dict[str, Any]]:
    rows = []
    for w in wavelengths_nm:
        wl = float(w)
        sim = simulate_pic_netlist(netlist, wavelength_nm=wl)
        dag = sim.get("dag_solver", {}) or {}
        outs = dag.get("external_outputs", []) or []
        total = 0.0
        target = 0.0
        for row in outs:
            if not isinstance(row, dict):
                continue
            pwr = float(row.get("power", 0.0) or 0.0)
            if pwr < 0.0:
                pwr = 0.0
            total += pwr
            if str(row.get("node", "")).strip() == target_node and str(row.get("port", "")).strip() == target_port:
                target += pwr
        frac = (target / total) if total > 0.0 else 0.0
        rows.append({"wavelength_nm": wl, "achieved_fraction": float(frac)})
    return rows


def evaluate_case_objective(
    netlist: dict,
    *,
    target_node: str,
    target_port: str,
    target_power_fraction: float,
    wavelengths_nm: list[float],
    wavelength_objective_agg: AggMode,
) -> dict[str, Any]:
    by_wl = output_power_fraction_by_wavelength(
        netlist,
        target_node=target_node,
        target_port=target_port,
        wavelengths_nm=wavelengths_nm,
    )
    fracs = [float(r.get("achieved_fraction", 0.0) or 0.0) for r in by_wl]
    errs = [float((f - float(target_power_fraction)) ** 2) for f in fracs]
    case_obj = _agg(errs, wavelength_objective_agg)
    frac_mean = _agg(fracs, "mean")
    for i in range(len(by_wl)):
        by_wl[i]["objective"] = float(errs[i])
    return {
        "objective": float(case_obj),
        "achieved_fraction_mean": float(frac_mean),
        "by_wavelength": by_wl,
    }


def evaluate_robust_objective(
    base_netlist: dict,
    *,
    design_node_id: str,
    design_param: str,
    design_value: Any,
    target_node: str,
    target_port: str,
    target_power_fraction: float,
    wavelengths_nm: list[float],
    robustness: RobustnessConfig,
) -> dict[str, Any]:
    """Evaluate objective for a candidate design value across cases + wavelengths."""

    case_rows = []
    case_objectives = []
    nominal_frac_mean = 0.0
    worst_case: dict[str, Any] = {
        "case_id": str(robustness.nominal_case_id),
        "wavelength_nm": float(wavelengths_nm[0]) if wavelengths_nm else 0.0,
        "objective": 0.0,
        "achieved_fraction": 0.0,
    }
    worst_objective = float("-inf")
    worst_case_sort_key = ("", float("inf"))

    for cs in robustness.cases:
        trial = apply_param_overrides(base_netlist, cs.overrides)
        trial = set_node_param(trial, node_id=design_node_id, param=design_param, value=design_value)
        r = evaluate_case_objective(
            trial,
            target_node=target_node,
            target_port=target_port,
            target_power_fraction=target_power_fraction,
            wavelengths_nm=wavelengths_nm,
            wavelength_objective_agg=robustness.wavelength_objective_agg,
        )
        case_obj = float(r["objective"])
        case_objectives.append(case_obj)
        if cs.id == robustness.nominal_case_id:
            nominal_frac_mean = float(r["achieved_fraction_mean"])
        case_rows.append(
            {
                "case_id": cs.id,
                "case_label": cs.label,
                "objective": case_obj,
                "achieved_fraction_mean": float(r["achieved_fraction_mean"]),
                "by_wavelength": r["by_wavelength"],
            }
        )

        by_wavelength = r["by_wavelength"] if isinstance(r.get("by_wavelength"), list) else []
        for row in by_wavelength:
            if not isinstance(row, dict):
                continue
            row_objective = float(row.get("objective", 0.0) or 0.0)
            row_fraction = float(row.get("achieved_fraction", 0.0) or 0.0)
            row_wavelength = float(row.get("wavelength_nm", 0.0) or 0.0)
            row_key = (str(cs.id).lower(), float(row_wavelength))
            if row_objective > worst_objective or (
                row_objective == worst_objective and row_key < worst_case_sort_key
            ):
                worst_objective = row_objective
                worst_case_sort_key = row_key
                worst_case = {
                    "case_id": str(cs.id),
                    "wavelength_nm": float(row_wavelength),
                    "objective": float(row_objective),
                    "achieved_fraction": float(row_fraction),
                }

    overall_obj = _agg(case_objectives, robustness.case_objective_agg)
    objective_case_max = _agg(case_objectives, "max")
    objective_case_mean = _agg(case_objectives, "mean")
    worst_case_fraction = float(worst_case.get("achieved_fraction", 0.0) or 0.0)
    degradation_from_nominal = max(0.0, float(nominal_frac_mean) - float(worst_case_fraction))

    threshold_violations: list[dict[str, Any]] = []
    min_worst = robustness.thresholds.get("min_worst_case_fraction")
    max_objective = robustness.thresholds.get("max_objective")
    max_degradation = robustness.thresholds.get("max_degradation_from_nominal")

    if min_worst is not None and worst_case_fraction < float(min_worst):
        threshold_violations.append(
            {
                "code": "invdesign.threshold.min_worst_case_fraction",
                "metric": "worst_case.achieved_fraction",
                "observed": float(worst_case_fraction),
                "threshold": float(min_worst),
            }
        )

    if max_objective is not None and float(objective_case_max) > float(max_objective):
        threshold_violations.append(
            {
                "code": "invdesign.threshold.max_objective",
                "metric": "metrics.objective_case_max",
                "observed": float(objective_case_max),
                "threshold": float(max_objective),
            }
        )

    if max_degradation is not None and float(degradation_from_nominal) > float(max_degradation):
        threshold_violations.append(
            {
                "code": "invdesign.threshold.max_degradation_from_nominal",
                "metric": "metrics.degradation_from_nominal",
                "observed": float(degradation_from_nominal),
                "threshold": float(max_degradation),
            }
        )

    return {
        "objective": float(overall_obj),
        "achieved_fraction_nominal_mean": float(nominal_frac_mean),
        "robustness_eval": {
            "objective_agg": {"wavelength": robustness.wavelength_objective_agg, "case": robustness.case_objective_agg},
            "objective_agg_value": float(overall_obj),
            "cases": case_rows,
            "worst_case": worst_case,
            "metrics": {
                "objective_case_max": float(objective_case_max),
                "objective_case_mean": float(objective_case_mean),
                "worst_case_achieved_fraction": float(worst_case_fraction),
                "nominal_achieved_fraction_mean": float(nominal_frac_mean),
                "degradation_from_nominal": float(degradation_from_nominal),
            },
            "threshold_eval": {
                "required": bool(robustness.required),
                "pass": len(threshold_violations) == 0,
                "thresholds": {
                    "min_worst_case_fraction": min_worst,
                    "max_objective": max_objective,
                    "max_degradation_from_nominal": max_degradation,
                },
                "violations": threshold_violations,
            },
        },
    }
