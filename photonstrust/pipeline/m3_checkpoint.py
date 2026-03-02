"""M3 checkpoint engine for flagship QKD and repeater quality."""

from __future__ import annotations

import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.config import build_scenarios, load_config
from photonstrust.optimize.optimizer import run_optimization
from photonstrust.qkd import compute_sweep
from photonstrust.report import build_reliability_card


def run_m3_checkpoint(
    *,
    qkd_config_path: Path,
    repeater_config_path: Path,
    output_dir: Path | None = None,
    force_analytic_backend: bool = True,
    perturbation_fraction: float = 0.05,
) -> dict[str, Any]:
    """Run M3 checkpoint checks and return a deterministic report payload."""

    qkd_path = Path(qkd_config_path).expanduser().resolve()
    repeater_path = Path(repeater_config_path).expanduser().resolve()
    out_root = Path(output_dir).expanduser().resolve() if output_dir is not None else None

    if out_root is None:
        with tempfile.TemporaryDirectory(prefix="photonstrust_m3_checkpoint_") as tmp:
            scratch_root = Path(tmp)
            report = _build_report(
                qkd_config_path=qkd_path,
                repeater_config_path=repeater_path,
                output_root=None,
                scratch_root=scratch_root,
                force_analytic_backend=bool(force_analytic_backend),
                perturbation_fraction=float(perturbation_fraction),
            )
    else:
        out_root.mkdir(parents=True, exist_ok=True)
        report = _build_report(
            qkd_config_path=qkd_path,
            repeater_config_path=repeater_path,
            output_root=out_root,
            scratch_root=out_root,
            force_analytic_backend=bool(force_analytic_backend),
            perturbation_fraction=float(perturbation_fraction),
        )
        report_path = out_root / "m3_checkpoint_report.json"
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    _validate_schema_if_available(report)
    return report


def _build_report(
    *,
    qkd_config_path: Path,
    repeater_config_path: Path,
    output_root: Path | None,
    scratch_root: Path,
    force_analytic_backend: bool,
    perturbation_fraction: float,
) -> dict[str, Any]:
    qkd_config = load_config(qkd_config_path)
    scenarios = build_scenarios(qkd_config)
    qkd_card_root = scratch_root / "m3_qkd_cards"
    qkd_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        qkd_rows.append(
            _evaluate_qkd_scenario(
                scenario=scenario,
                qkd_card_root=qkd_card_root,
                force_analytic_backend=force_analytic_backend,
            )
        )
    qkd_rows.sort(key=lambda row: (str(row.get("scenario_id", "")), str(row.get("band", ""))))
    qkd_pass_count = sum(1 for row in qkd_rows if row.get("status") == "PASS")
    qkd_total = len(qkd_rows)
    qkd_status = "PASS" if qkd_total > 0 and qkd_pass_count == qkd_total else "HOLD"

    repeater = _evaluate_repeater(
        repeater_config_path=repeater_config_path,
        repeater_output_root=(scratch_root / "m3_repeater"),
        force_analytic_backend=force_analytic_backend,
        perturbation_fraction=perturbation_fraction,
    )
    repeater_distances = repeater.get("distances", [])
    stable_count = sum(1 for row in repeater_distances if bool(row.get("stable", False)))
    repeater_total = len(repeater_distances)

    qkd_all_pass = qkd_status == "PASS"
    repeater_all_pass = repeater.get("status") == "PASS" and repeater_total > 0
    overall_status = "PASS" if (qkd_all_pass and repeater_all_pass) else "HOLD"

    report: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "photonstrust.m3_checkpoint_report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "qkd_config_path": str(qkd_config_path),
            "repeater_config_path": str(repeater_config_path),
            "output_dir": str(output_root) if output_root is not None else None,
            "force_analytic_backend": bool(force_analytic_backend),
            "perturbation_fraction": float(perturbation_fraction),
        },
        "qkd": {
            "scenario_count": int(qkd_total),
            "bands": qkd_rows,
            "status": qkd_status,
        },
        "repeater": repeater,
        "summary": {
            "qkd_pass_bands": int(qkd_pass_count),
            "qkd_total_bands": int(qkd_total),
            "repeater_stable_distances": int(stable_count),
            "repeater_total_distances": int(repeater_total),
            "all_qkd_checks_pass": bool(qkd_all_pass),
            "repeater_stability_pass": bool(repeater_all_pass),
        },
        "overall_status": overall_status,
    }
    return report


def _evaluate_qkd_scenario(
    *,
    scenario: dict[str, Any],
    qkd_card_root: Path,
    force_analytic_backend: bool,
) -> dict[str, Any]:
    scenario_eval = copy.deepcopy(scenario)
    if force_analytic_backend:
        _force_analytic_qkd_scenario(scenario_eval)

    sweep = compute_sweep(scenario_eval, include_uncertainty=False)
    results_raw = sweep.get("results")
    results = list(results_raw) if isinstance(results_raw, list) else []
    results.sort(key=lambda row: float(getattr(row, "distance_km", 0.0)))

    key_rates = [float(getattr(row, "key_rate_bps", 0.0)) for row in results]
    qbers = [float(getattr(row, "qber_total", -1.0)) for row in results]

    max_positive_delta = 0.0
    for index in range(len(key_rates) - 1):
        delta = key_rates[index + 1] - key_rates[index]
        if delta > max_positive_delta:
            max_positive_delta = float(delta)
    key_rate_pass = max_positive_delta <= 1.0e-12

    qber_pass = all((0.0 <= qber <= 1.0) for qber in qbers)

    card_dir = qkd_card_root / _scenario_slug(scenario_eval)
    reliability_pass = False
    reliability_note: str | None = None
    card_schema_version: str | None = None
    try:
        card = build_reliability_card(
            scenario_eval,
            results,
            sweep.get("uncertainty") if isinstance(sweep, dict) else None,
            card_dir,
        )
        reliability_pass = isinstance(card, dict)
        if reliability_pass:
            card_schema_version = str(card.get("schema_version")) if card.get("schema_version") is not None else None
        else:
            reliability_note = "build_reliability_card returned a non-dict payload."
    except Exception as exc:  # pragma: no cover - defensive
        reliability_pass = False
        reliability_note = str(exc)

    checks = {
        "key_rate_non_increasing_over_distance": {
            "pass": bool(key_rate_pass),
            "max_positive_delta_bps": float(max_positive_delta),
            "distance_count": int(len(results)),
        },
        "qber_within_unit_interval": {
            "pass": bool(qber_pass),
            "qber_min": float(min(qbers)) if qbers else None,
            "qber_max": float(max(qbers)) if qbers else None,
            "distance_count": int(len(results)),
        },
        "reliability_card_generated": {
            "pass": bool(reliability_pass),
            "card_schema_version": card_schema_version,
            "note": reliability_note,
        },
    }

    row_status = "PASS" if all(bool(value.get("pass", False)) for value in checks.values()) else "HOLD"
    return {
        "scenario_id": str(scenario_eval.get("scenario_id", "")),
        "band": str(scenario_eval.get("band", "")),
        "checks": checks,
        "status": row_status,
    }


def _evaluate_repeater(
    *,
    repeater_config_path: Path,
    repeater_output_root: Path,
    force_analytic_backend: bool,
    perturbation_fraction: float,
) -> dict[str, Any]:
    repeater_output_root.mkdir(parents=True, exist_ok=True)
    base_config_raw = load_config(repeater_config_path)
    base_config = _normalize_repeater_config(base_config_raw)
    if force_analytic_backend:
        _force_analytic_repeater_config(base_config)

    p = max(0.0, float(perturbation_fraction))
    minus_factor = max(0.0, 1.0 - p)
    plus_factor = max(0.0, 1.0 + p)

    try:
        base_best = _run_repeater_case(base_config, repeater_output_root / "base")
        minus_best = _run_repeater_case(
            _perturb_repeater_config(base_config, minus_factor),
            repeater_output_root / "minus",
        )
        plus_best = _run_repeater_case(
            _perturb_repeater_config(base_config, plus_factor),
            repeater_output_root / "plus",
        )
    except Exception as exc:
        return {
            "checks": {
                "optimization_runs_succeeded": False,
                "perturbation_fraction": float(p),
                "stability_threshold_ratio": 0.30,
                "error": str(exc),
            },
            "distances": [],
            "status": "HOLD",
        }

    distances = sorted(base_best.keys())
    rows: list[dict[str, Any]] = []
    for distance in distances:
        base_spacing = base_best.get(distance)
        minus_spacing = minus_best.get(distance)
        plus_spacing = plus_best.get(distance)

        if base_spacing is None or minus_spacing is None or plus_spacing is None:
            drift_ratio = None
            stable = False
        else:
            denominator = max(abs(base_spacing), 1.0e-12)
            drift_ratio = max(
                abs(minus_spacing - base_spacing) / denominator,
                abs(plus_spacing - base_spacing) / denominator,
            )
            stable = drift_ratio <= 0.30

        rows.append(
            {
                "total_distance_km": float(distance),
                "base_best_spacing_km": float(base_spacing) if base_spacing is not None else None,
                "minus_best_spacing_km": float(minus_spacing) if minus_spacing is not None else None,
                "plus_best_spacing_km": float(plus_spacing) if plus_spacing is not None else None,
                "drift_ratio": float(drift_ratio) if drift_ratio is not None else None,
                "stable": bool(stable),
            }
        )

    stable_count = sum(1 for row in rows if bool(row.get("stable", False)))
    status = "PASS" if rows and stable_count == len(rows) else "HOLD"
    return {
        "checks": {
            "optimization_runs_succeeded": True,
            "perturbation_fraction": float(p),
            "stability_threshold_ratio": 0.30,
        },
        "distances": rows,
        "status": status,
    }


def _normalize_repeater_config(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError("Repeater config must be a mapping.")
    if isinstance(raw.get("optimization"), dict):
        return copy.deepcopy(raw)
    if isinstance(raw.get("repeater_optimization"), dict):
        payload = copy.deepcopy(raw)
        payload["optimization"] = copy.deepcopy(payload["repeater_optimization"])
        return payload
    raise ValueError("Repeater config must contain 'optimization' or 'repeater_optimization'.")


def _force_analytic_qkd_scenario(scenario: dict[str, Any]) -> None:
    source = scenario.get("source")
    if isinstance(source, dict):
        source["physics_backend"] = "analytic"
    detector = scenario.get("detector")
    if isinstance(detector, dict):
        detector["physics_backend"] = "analytic"


def _force_analytic_repeater_config(config: dict[str, Any]) -> None:
    optimization = config.get("optimization")
    if not isinstance(optimization, dict):
        return
    memory = optimization.get("memory")
    if isinstance(memory, dict):
        memory["physics_backend"] = "analytic"
    link = optimization.get("link_scenario")
    if isinstance(link, dict):
        source = link.get("source")
        if isinstance(source, dict):
            source["physics_backend"] = "analytic"
        detector = link.get("detector")
        if isinstance(detector, dict):
            detector["physics_backend"] = "analytic"


def _perturb_repeater_config(base_config: dict[str, Any], factor: float) -> dict[str, Any]:
    cfg = copy.deepcopy(base_config)
    optimization = cfg.get("optimization")
    if not isinstance(optimization, dict):
        return cfg
    memory = optimization.get("memory")
    if not isinstance(memory, dict):
        return cfg

    t2_ms = _float_or_none(memory.get("t2_ms"))
    if t2_ms is not None:
        memory["t2_ms"] = max(1.0e-12, float(t2_ms) * factor)
    retrieval = _float_or_none(memory.get("retrieval_efficiency"))
    if retrieval is not None:
        memory["retrieval_efficiency"] = min(1.0, max(0.0, float(retrieval) * factor))
    return cfg


def _run_repeater_case(config: dict[str, Any], output_dir: Path) -> dict[float, float | None]:
    result = run_optimization(config, output_dir)
    best = result.get("best")
    if not isinstance(best, dict):
        raise ValueError("run_optimization did not return a 'best' mapping.")

    best_by_distance: dict[float, float | None] = {}
    for key, row in best.items():
        distance = _float_or_none(key)
        if distance is None:
            continue
        spacing = None
        if isinstance(row, dict):
            spacing = _float_or_none(row.get("spacing_km"))
        best_by_distance[float(distance)] = float(spacing) if spacing is not None else None
    return best_by_distance


def _scenario_slug(scenario: dict[str, Any]) -> str:
    scenario_id = str(scenario.get("scenario_id", "scenario")).strip() or "scenario"
    band = str(scenario.get("band", "band")).strip() or "band"
    slug = f"{scenario_id}_{band}"
    cleaned = []
    for ch in slug:
        if ch.isalnum() or ch in {"-", "_"}:
            cleaned.append(ch)
        else:
            cleaned.append("_")
    return "".join(cleaned)


def _float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:
        return None
    return parsed


def _validate_schema_if_available(report: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return
    try:
        from photonstrust.workflow.schema import m3_checkpoint_report_schema_path
    except Exception:
        return
    schema_path = m3_checkpoint_report_schema_path()
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)

