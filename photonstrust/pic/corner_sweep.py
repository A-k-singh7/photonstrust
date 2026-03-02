"""PIC process-corner sweep and risk assessment helpers."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.graph import compile_graph, load_graph_file
from photonstrust.pdk.registry import get_pdk, load_pdk_manifest
from photonstrust.pic import simulate_pic_netlist
from photonstrust.pic.perturbation import perturb_netlist, sample_process_parameters
from photonstrust.pipeline.pic_qkd_bridge import (
    build_qkd_scenario_from_pic,
    extract_eta_chip,
    pdk_coupler_efficiency,
)
from photonstrust.qkd import compute_point
from photonstrust.workflow.schema import pic_corner_sweep_schema_path

_CANONICAL_CORNERS = ("SS", "TT", "FF", "FS", "SF")


def run_corner_sweep(
    graph_path: Path | str,
    *,
    pdk_name: str | None = None,
    pdk_manifest_path: str | Path | None = None,
    protocol: str = "BB84_DECOY",
    target_distance_km: float = 50.0,
    wavelength_nm: float = 1550.0,
    corners: str = "all",
    n_monte_carlo: int = 0,
    mc_seed: int = 42,
    key_rate_threshold_bps: float = 1000.0,
    output_dir: Path | str | None = None,
) -> dict:
    """Run nominal/corner PIC->QKD evaluation and return a report payload."""

    graph_file = Path(graph_path).expanduser().resolve()
    graph_payload = load_graph_file(graph_file)
    compiled = compile_graph(graph_payload, require_schema=False)
    if str(compiled.profile).strip().lower() != "pic_circuit":
        raise ValueError("run_corner_sweep requires graph.profile=pic_circuit")

    base_netlist = compiled.compiled
    if not isinstance(base_netlist, dict):
        raise ValueError("Compiled pic_circuit netlist is not an object")

    pdk = _resolve_pdk(pdk_name=pdk_name, pdk_manifest_path=pdk_manifest_path)
    target_distance = max(0.0, float(target_distance_km))
    wavelength = float(wavelength_nm)
    threshold = float(key_rate_threshold_bps)
    normalized_protocol = str(protocol or "BB84_DECOY").strip().upper() or "BB84_DECOY"

    nominal = _evaluate_run(
        base_netlist=base_netlist,
        graph_payload=graph_payload,
        process_params={},
        pdk=pdk,
        protocol=normalized_protocol,
        target_distance_km=target_distance,
        wavelength_nm=wavelength,
    )
    nominal["label"] = "nominal"

    selected_corners = _select_corners(pdk, corners)
    corner_rows: list[dict[str, Any]] = []
    for corner_name, params in selected_corners:
        row = _evaluate_run(
            base_netlist=base_netlist,
            graph_payload=graph_payload,
            process_params=params,
            pdk=pdk,
            protocol=normalized_protocol,
            target_distance_km=target_distance,
            wavelength_nm=wavelength,
        )
        row["corner"] = str(corner_name)
        corner_rows.append(row)
    corner_rows_by_name = {
        str(row.get("corner")): dict(row)
        for row in corner_rows
        if isinstance(row, dict) and str(row.get("corner", "")).strip()
    }

    monte_carlo = _run_monte_carlo(
        base_netlist=base_netlist,
        graph_payload=graph_payload,
        pdk=pdk,
        protocol=normalized_protocol,
        target_distance_km=target_distance,
        wavelength_nm=wavelength,
        n_monte_carlo=int(max(0, n_monte_carlo)),
        mc_seed=int(mc_seed),
        key_rate_threshold_bps=threshold,
    )

    sensitivity_rank = compute_sensitivity_rank(
        base_netlist,
        pdk=pdk,
        protocol=normalized_protocol,
        target_distance_km=target_distance,
        wavelength_nm=wavelength,
    )
    dominant_sensitivity = sensitivity_rank[0]["parameter"] if sensitivity_rank else None

    worst_case_key_rate_bps, worst_corner = _worst_case_rate(nominal=nominal, corners=corner_rows)
    yield_fraction = monte_carlo.get("yield_fraction_above_threshold")
    yield_fraction_f = _to_float(yield_fraction)

    risk_assessment = {
        "worst_case_key_rate_bps": float(worst_case_key_rate_bps),
        "worst_corner": worst_corner,
        "yield_above_threshold": float(yield_fraction_f) if yield_fraction_f is not None else None,
        "key_rate_threshold_bps": float(threshold),
        "risk_level": classify_risk_level(
            worst_case_key_rate_bps=float(worst_case_key_rate_bps),
            key_rate_threshold_bps=float(threshold),
            yield_fraction=yield_fraction_f,
        ),
        "dominant_sensitivity": dominant_sensitivity,
        "sensitivity_rank": sensitivity_rank,
    }

    report = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_corner_sweep",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "graph_path": str(graph_file),
            "pdk_name": str(pdk_name) if pdk_name is not None else None,
            "pdk_manifest_path": str(Path(pdk_manifest_path).expanduser().resolve())
            if pdk_manifest_path is not None
            else None,
            "resolved_pdk_name": str(getattr(pdk, "name", "")),
            "resolved_pdk_version": str(getattr(pdk, "version", "")),
            "protocol": normalized_protocol,
            "target_distance_km": float(target_distance),
            "wavelength_nm": float(wavelength),
            "corners": str(corners),
            "n_monte_carlo": int(max(0, n_monte_carlo)),
            "mc_seed": int(mc_seed),
            "key_rate_threshold_bps": float(threshold),
            "output_dir": str(Path(output_dir).expanduser().resolve()) if output_dir is not None else None,
        },
        "nominal": nominal,
        "corners": {
            "requested": str(corners),
            "selected": [str(name) for name, _ in selected_corners],
            "count": int(len(corner_rows)),
            "evaluated": corner_rows,
            **corner_rows_by_name,
        },
        "monte_carlo": monte_carlo,
        "risk_assessment": risk_assessment,
    }

    _validate_schema_if_available(report)

    if output_dir is not None:
        output_root = Path(output_dir).expanduser().resolve()
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / "pic_corner_sweep.json").write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )

    return report


def compute_sensitivity_rank(
    base_netlist_or_corner_results: dict[str, Any] | Mapping[str, Any],
    sigma_dict: Mapping[str, Any] | None = None,
    *,
    pdk: Any | None = None,
    protocol: str | None = None,
    target_distance_km: float | None = None,
    wavelength_nm: float | None = None,
) -> list[dict]:
    """Compute sensitivity ranking.

    Supports two modes:
    - runtime mode: pass ``base_netlist_or_corner_results`` as netlist + ``pdk/protocol/target_distance_km/wavelength_nm``.
    - analytical mode: pass ``base_netlist_or_corner_results`` as corner-results mapping + ``sigma_dict``.
    """

    is_runtime_mode = (
        pdk is not None
        and protocol is not None
        and target_distance_km is not None
        and wavelength_nm is not None
    )
    if is_runtime_mode:
        if not isinstance(base_netlist_or_corner_results, dict):
            raise TypeError("base_netlist must be an object")
        return _compute_sensitivity_rank_from_netlist(
            base_netlist=base_netlist_or_corner_results,
            pdk=pdk,
            protocol=str(protocol),
            target_distance_km=float(target_distance_km),
            wavelength_nm=float(wavelength_nm),
        )

    return _compute_sensitivity_rank_from_corner_results(
        corner_results=base_netlist_or_corner_results,
        sigma_dict=sigma_dict or {},
    )


def _compute_sensitivity_rank_from_netlist(
    *,
    base_netlist: dict[str, Any],
    pdk: Any,
    protocol: str,
    target_distance_km: float,
    wavelength_nm: float,
) -> list[dict]:
    baseline = _evaluate_run(
        base_netlist=base_netlist,
        graph_payload=None,
        process_params={},
        pdk=pdk,
        protocol=str(protocol),
        target_distance_km=float(target_distance_km),
        wavelength_nm=float(wavelength_nm),
    )
    baseline_rate = _to_float(baseline.get("key_rate_bps"))
    if baseline.get("status") != "ok" or baseline_rate is None:
        return []

    candidates = _sensitivity_candidates(pdk)
    rows: list[dict[str, Any]] = []
    for param in sorted(candidates.keys()):
        sigma = float(candidates[param].get("sigma", 0.0) or 0.0)
        if sigma <= 0.0:
            continue

        plus_case = _evaluate_run(
            base_netlist=base_netlist,
            graph_payload=None,
            process_params={param: sigma},
            pdk=pdk,
            protocol=str(protocol),
            target_distance_km=float(target_distance_km),
            wavelength_nm=float(wavelength_nm),
        )
        minus_case = _evaluate_run(
            base_netlist=base_netlist,
            graph_payload=None,
            process_params={param: -sigma},
            pdk=pdk,
            protocol=str(protocol),
            target_distance_km=float(target_distance_km),
            wavelength_nm=float(wavelength_nm),
        )

        plus_rate = _to_float(plus_case.get("key_rate_bps")) if plus_case.get("status") == "ok" else None
        minus_rate = _to_float(minus_case.get("key_rate_bps")) if minus_case.get("status") == "ok" else None
        delta_plus = (plus_rate - baseline_rate) if plus_rate is not None else 0.0
        delta_minus = (minus_rate - baseline_rate) if minus_rate is not None else 0.0
        sensitivity_abs = max(abs(delta_plus), abs(delta_minus))

        coeff = candidates[param].get("coefficient")
        coeff_f = _to_float(coeff)
        rows.append(
            {
                "parameter": str(param),
                "sigma": float(sigma),
                "coefficient": float(coeff_f) if coeff_f is not None else None,
                "base_key_rate_bps": float(baseline_rate),
                "plus_key_rate_bps": float(plus_rate) if plus_rate is not None else None,
                "minus_key_rate_bps": float(minus_rate) if minus_rate is not None else None,
                "delta_plus_bps": float(delta_plus),
                "delta_minus_bps": float(delta_minus),
                "sensitivity_abs_bps": float(sensitivity_abs),
            }
        )

    _normalize_variance_fractions(rows)
    rows.sort(
        key=lambda row: (
            -float(row.get("sensitivity_abs_bps", 0.0) or 0.0),
            -abs(float(row.get("coefficient", 0.0) or 0.0)),
            str(row.get("parameter", "")),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["rank"] = int(index)
    return rows


def _compute_sensitivity_rank_from_corner_results(
    *,
    corner_results: Mapping[str, Any] | dict[str, Any],
    sigma_dict: Mapping[str, Any],
) -> list[dict]:
    rows = _extract_corner_rows_mapping(corner_results)
    rates = [_to_float(value.get("key_rate_bps")) for value in rows.values() if isinstance(value, Mapping)]
    clean_rates = [float(rate) for rate in rates if rate is not None]
    if not clean_rates:
        return []

    spread_bps = max(clean_rates) - min(clean_rates)
    if spread_bps <= 0.0:
        spread_bps = 1.0

    sigma_payload = _flatten_numeric(dict(sigma_dict)) if isinstance(sigma_dict, Mapping) else {}
    out: list[dict[str, Any]] = []
    for param in sorted(sigma_payload.keys()):
        sigma = abs(float(sigma_payload[param]))
        if sigma <= 0.0:
            continue
        sensitivity_abs = float(spread_bps * sigma)
        out.append(
            {
                "parameter": str(param),
                "sigma": float(sigma),
                "coefficient": None,
                "base_key_rate_bps": _baseline_rate_from_corner_rows(rows),
                "plus_key_rate_bps": None,
                "minus_key_rate_bps": None,
                "delta_plus_bps": None,
                "delta_minus_bps": None,
                "sensitivity_abs_bps": sensitivity_abs,
            }
        )

    _normalize_variance_fractions(out)
    out.sort(
        key=lambda row: (
            -float(row.get("sensitivity_abs_bps", 0.0) or 0.0),
            str(row.get("parameter", "")),
        )
    )
    for idx, row in enumerate(out, start=1):
        row["rank"] = int(idx)
    return out


def classify_risk_level(
    corner_results: Mapping[str, Any] | None = None,
    threshold_bps: float | None = None,
    *,
    worst_case_key_rate_bps: float | None = None,
    key_rate_threshold_bps: float | None = None,
    yield_fraction: float | None = None,
) -> str:
    """Classify risk level from explicit values or corner-result payloads."""

    if worst_case_key_rate_bps is None and corner_results is not None:
        extracted = _extract_corner_rows_mapping(corner_results)
        if extracted:
            values = [
                _to_float(row.get("key_rate_bps"))
                for row in extracted.values()
                if isinstance(row, Mapping)
            ]
            valid = [float(v) for v in values if v is not None]
            if valid:
                worst_case_key_rate_bps = float(min(valid))

    if key_rate_threshold_bps is None:
        key_rate_threshold_bps = threshold_bps if threshold_bps is not None else 1000.0

    worst = float(worst_case_key_rate_bps if worst_case_key_rate_bps is not None else 0.0)
    threshold = max(1.0e-12, float(key_rate_threshold_bps))
    ratio = worst / threshold
    y = None if yield_fraction is None else max(0.0, min(1.0, float(yield_fraction)))

    if worst <= 0.0:
        return "CRITICAL"
    if ratio >= 1.0 and (y is None or y >= 0.95):
        return "LOW"
    if ratio >= 0.80 and (y is None or y >= 0.80):
        return "MEDIUM"
    if y is not None and y < 0.20 and ratio < 0.50:
        return "CRITICAL"
    return "HIGH"


def _run_monte_carlo(
    *,
    base_netlist: dict,
    graph_payload: dict[str, Any] | None,
    pdk: Any,
    protocol: str,
    target_distance_km: float,
    wavelength_nm: float,
    n_monte_carlo: int,
    mc_seed: int,
    key_rate_threshold_bps: float,
) -> dict[str, Any]:
    if n_monte_carlo <= 0:
        return {
            "enabled": False,
            "n_samples": 0,
            "sample_count": 0,
            "seed": int(mc_seed),
            "status": "skipped",
            "yield_fraction_above_threshold": None,
            "yield_above_threshold": None,
            "yield_fraction": None,
            "yield": None,
        }

    key_rates: list[float] = []
    failed_samples = 0
    for index in range(n_monte_carlo):
        params = sample_process_parameters(
            pdk,
            seed=int(mc_seed) + int(index),
            sigma_multiplier=1.0,
        )
        case = _evaluate_run(
            base_netlist=base_netlist,
            graph_payload=graph_payload,
            process_params=params,
            pdk=pdk,
            protocol=protocol,
            target_distance_km=target_distance_km,
            wavelength_nm=wavelength_nm,
        )
        key_rate = _to_float(case.get("key_rate_bps"))
        if case.get("status") != "ok" or key_rate is None:
            failed_samples += 1
            continue
        key_rates.append(float(key_rate))

    if not key_rates:
        return {
            "enabled": True,
            "n_samples": int(n_monte_carlo),
            "sample_count": int(n_monte_carlo),
            "seed": int(mc_seed),
            "completed_samples": 0,
            "failed_samples": int(failed_samples),
            "status": "error",
            "yield_fraction_above_threshold": 0.0,
            "yield_above_threshold": 0.0,
            "yield_fraction": 0.0,
            "yield": 0.0,
            "key_rate_mean_bps": None,
            "key_rate_std_bps": None,
            "key_rate_min_bps": None,
            "key_rate_max_bps": None,
            "key_rate_ci95_bps": {"low": None, "high": None},
        }

    n = len(key_rates)
    mean = _mean(key_rates)
    std = _stddev_population(key_rates)
    sem = std / math.sqrt(max(1, n))
    ci_half = 1.96 * sem
    ci_low = mean - ci_half
    ci_high = mean + ci_half
    yield_fraction = sum(1 for value in key_rates if value >= key_rate_threshold_bps) / float(n)

    return {
        "enabled": True,
        "n_samples": int(n_monte_carlo),
        "sample_count": int(n_monte_carlo),
        "seed": int(mc_seed),
        "completed_samples": int(n),
        "failed_samples": int(failed_samples),
        "status": "ok",
        "yield_fraction_above_threshold": float(yield_fraction),
        "yield_above_threshold": float(yield_fraction),
        "yield_fraction": float(yield_fraction),
        "yield": float(yield_fraction),
        "key_rate_mean_bps": float(mean),
        "key_rate_std_bps": float(std),
        "key_rate_min_bps": float(min(key_rates)),
        "key_rate_max_bps": float(max(key_rates)),
        "key_rate_ci95_bps": {"low": float(ci_low), "high": float(ci_high)},
    }


def _evaluate_run(
    *,
    base_netlist: dict,
    graph_payload: dict[str, Any] | None,
    process_params: dict[str, Any],
    pdk: Any,
    protocol: str,
    target_distance_km: float,
    wavelength_nm: float,
) -> dict[str, Any]:
    try:
        perturbed_netlist = perturb_netlist(base_netlist, process_params, pdk=pdk)
        sim_result = simulate_pic_netlist(perturbed_netlist, wavelength_nm=float(wavelength_nm))
        eta_chip = extract_eta_chip(sim_result, wavelength_nm=float(wavelength_nm))
        eta_coupler = pdk_coupler_efficiency(pdk)
        qkd_scenario = build_qkd_scenario_from_pic(
            graph=graph_payload,
            distances_km=[float(target_distance_km)],
            wavelength_nm=float(wavelength_nm),
            protocol=str(protocol),
            eta_chip=float(eta_chip),
            eta_coupler=float(eta_coupler),
        )
        point = compute_point(qkd_scenario, float(target_distance_km))

        return {
            "status": "ok",
            "process_params": dict(process_params),
            "eta_chip": float(eta_chip),
            "eta_coupler": float(eta_coupler),
            "key_rate_bps": float(getattr(point, "key_rate_bps", 0.0)),
            "qber_total": float(getattr(point, "qber_total", 0.0)),
            "fidelity": float(getattr(point, "fidelity", 0.0)),
            "loss_db": float(getattr(point, "loss_db", 0.0)),
            "protocol_name": str(getattr(point, "protocol_name", "")),
        }
    except Exception as exc:
        return {
            "status": "error",
            "process_params": dict(process_params),
            "error": str(exc),
            "key_rate_bps": None,
        }


def _resolve_pdk(*, pdk_name: str | None, pdk_manifest_path: str | Path | None) -> Any:
    if pdk_manifest_path is not None:
        return load_pdk_manifest(Path(pdk_manifest_path).expanduser().resolve())
    return get_pdk(pdk_name)


def _select_corners(pdk: Any, corners: str) -> list[tuple[str, dict[str, Any]]]:
    available = _process_corners(pdk)
    if not available:
        return []

    canonical_map: dict[str, tuple[str, dict[str, Any]]] = {}
    for raw_name, payload in available.items():
        if not isinstance(payload, Mapping):
            continue
        normalized = str(raw_name).strip().upper()
        if not normalized:
            continue
        canonical_map[normalized] = (str(raw_name), dict(payload))
    if not canonical_map:
        return []

    requested = str(corners or "all").strip()
    if requested.lower() == "all":
        names = [name for name in _CANONICAL_CORNERS if name in canonical_map]
        extra = sorted(name for name in canonical_map.keys() if name not in set(names))
        names.extend(extra)
    else:
        names = []
        for item in requested.split(","):
            name = str(item).strip().upper()
            if not name or name in names:
                continue
            if name in canonical_map:
                names.append(name)

    out: list[tuple[str, dict[str, Any]]] = []
    for name in names:
        raw_name, params = canonical_map[name]
        out.append((str(name), dict(params)))
    return out


def _process_corners(pdk: Any) -> dict[str, Any]:
    value: Any = None
    if isinstance(pdk, Mapping):
        value = pdk.get("process_corners")
    else:
        value = getattr(pdk, "process_corners", None)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _sensitivity_coefficients(pdk: Any) -> dict[str, Any]:
    value: Any = None
    if isinstance(pdk, Mapping):
        value = pdk.get("sensitivity_coefficients")
    else:
        value = getattr(pdk, "sensitivity_coefficients", None)
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _sensitivity_candidates(pdk: Any) -> dict[str, dict[str, float | None]]:
    corners = _process_corners(pdk)
    value_lists: dict[str, list[float]] = {}
    tt_values: dict[str, float] = {}
    for corner_name, payload in corners.items():
        if not isinstance(payload, Mapping):
            continue
        flattened = _flatten_numeric(payload)
        for key, value in flattened.items():
            value_lists.setdefault(key, []).append(float(value))
            if str(corner_name).strip().upper() == "TT":
                tt_values[key] = float(value)

    coeffs = _flatten_numeric(_sensitivity_coefficients(pdk))
    candidate_keys = sorted(set(value_lists.keys()).union(coeffs.keys()))
    out: dict[str, dict[str, float | None]] = {}
    for key in candidate_keys:
        values = value_lists.get(key, [])
        if values:
            center = float(tt_values.get(key, _mean(values)))
            sigma = float(_stddev_population(values))
            if sigma <= 0.0:
                sigma = _fallback_sigma(key=key, center=center)
        else:
            center = 0.0
            sigma = _fallback_sigma(key=key, center=0.0)
        out[key] = {
            "center": float(center),
            "sigma": float(sigma),
            "coefficient": float(coeffs[key]) if key in coeffs else None,
        }
    return out


def _flatten_numeric(payload: Mapping[str, Any], *, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    for raw_key in sorted(payload.keys(), key=lambda value: str(value)):
        key = str(raw_key)
        value = payload[raw_key]
        full_key = key if not prefix else f"{prefix}.{key}"
        parsed = _to_float(value)
        if parsed is not None:
            out[full_key] = float(parsed)
            if "." in full_key:
                out[key] = float(parsed)
            continue
        if isinstance(value, Mapping):
            nested = _flatten_numeric(value, prefix=full_key)
            for nested_key, nested_value in nested.items():
                out[nested_key] = float(nested_value)
    return out


def _fallback_sigma(*, key: str, center: float) -> float:
    normalized = str(key).strip().lower()
    if normalized.endswith("_nm"):
        return 1.0
    if "loss" in normalized and "db_per_cm" in normalized:
        return 0.05
    if "coupling_ratio" in normalized:
        return 0.02
    return max(1.0e-6, abs(float(center)) * 0.10)


def _worst_case_rate(*, nominal: dict[str, Any], corners: list[dict[str, Any]]) -> tuple[float, str | None]:
    rows: list[tuple[str, float]] = []
    nominal_rate = _to_float(nominal.get("key_rate_bps"))
    if nominal.get("status") == "ok" and nominal_rate is not None:
        rows.append(("nominal", float(nominal_rate)))
    for row in corners:
        key_rate = _to_float(row.get("key_rate_bps"))
        if row.get("status") == "ok" and key_rate is not None:
            rows.append((str(row.get("corner", "corner")), float(key_rate)))
    if not rows:
        return 0.0, None
    label, value = min(rows, key=lambda item: (item[1], item[0]))
    return float(value), str(label)


def _extract_corner_rows_mapping(payload: Mapping[str, Any] | dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return {}

    out: dict[str, dict[str, Any]] = {}
    evaluated = payload.get("evaluated")
    if isinstance(evaluated, list):
        for row in evaluated:
            if not isinstance(row, Mapping):
                continue
            corner_name = str(row.get("corner", "")).strip().upper()
            if corner_name:
                out[corner_name] = dict(row)

    for raw_key, raw_value in payload.items():
        if not isinstance(raw_value, Mapping):
            continue
        key = str(raw_key).strip().upper()
        if key in {"REQUESTED", "SELECTED", "COUNT", "EVALUATED"}:
            continue
        corner_name = str(raw_value.get("corner", key)).strip().upper() or key
        out[corner_name] = dict(raw_value)

    return out


def _baseline_rate_from_corner_rows(rows: Mapping[str, Mapping[str, Any]]) -> float | None:
    tt = rows.get("TT")
    if isinstance(tt, Mapping):
        tt_rate = _to_float(tt.get("key_rate_bps"))
        if tt_rate is not None:
            return float(tt_rate)

    values = [_to_float(row.get("key_rate_bps")) for row in rows.values()]
    clean = [float(v) for v in values if v is not None]
    if not clean:
        return None
    return float(_mean(clean))


def _normalize_variance_fractions(rows: list[dict[str, Any]]) -> None:
    weights = [max(0.0, float(row.get("sensitivity_abs_bps", 0.0) or 0.0)) for row in rows]
    total = float(sum(weights))
    for row, weight in zip(rows, weights):
        fraction = float(weight / total) if total > 0.0 else 0.0
        row["variance_fraction"] = fraction
        row["fraction"] = fraction
        row["weight"] = fraction


def _validate_schema_if_available(report: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return

    schema_path = pic_corner_sweep_schema_path()
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)


def _to_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return float(parsed)


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _stddev_population(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mu = _mean(values)
    variance = sum((float(value) - mu) ** 2 for value in values) / len(values)
    return float(math.sqrt(max(0.0, variance)))
