"""Cross-engine parity harness for protocol primitives."""

from __future__ import annotations

from typing import Any, Mapping

from photonstrust.protocols.engines.base import ProtocolEngineUnavailableError
from photonstrust.protocols.engines.registry import get_protocol_engine


DEFAULT_THRESHOLD_POLICY: dict[str, dict[str, float]] = {
    "swap_bsm_equal_bits": {
        "success_probability": 1.0e-9,
    }
}


def run_protocol_engine_parity(
    *,
    primitive: str = "swap_bsm_equal_bits",
    engine_ids: list[str] | tuple[str, ...] | None = None,
    baseline_engine_id: str = "qiskit",
    threshold_policy: Mapping[str, Mapping[str, float]] | None = None,
    seed: int | None = None,
) -> dict[str, Any]:
    normalized_primitive = str(primitive or "").strip().lower()
    requested = _normalize_engine_ids(engine_ids)
    baseline = str(baseline_engine_id or "qiskit").strip().lower() or "qiskit"
    if baseline not in requested:
        requested.append(baseline)

    policy = _normalize_threshold_policy(threshold_policy)
    per_engine: list[dict[str, Any]] = []
    by_engine: dict[str, dict[str, Any]] = {}

    for engine_id in requested:
        row = _evaluate_engine(engine_id=engine_id, primitive=normalized_primitive, seed=seed)
        per_engine.append(row)
        by_engine[engine_id] = row

    baseline_row = by_engine.get(baseline)
    baseline_metrics = baseline_row.get("metrics") if isinstance(baseline_row, dict) else None
    baseline_ready = bool(
        isinstance(baseline_metrics, dict) and baseline_row is not None and baseline_row.get("status") == "ok"
    )

    violations: list[dict[str, Any]] = []
    for row in per_engine:
        if row.get("status") != "ok":
            row["delta_abs_vs_baseline"] = {}
            continue
        if row.get("engine_id") == baseline or not baseline_ready:
            row["delta_abs_vs_baseline"] = {}
            continue
        deltas = _compute_deltas(
            primitive=normalized_primitive,
            baseline_metrics=baseline_metrics,
            candidate_metrics=row.get("metrics"),
            threshold_policy=policy,
            candidate_engine_id=str(row.get("engine_id")),
            baseline_engine_id=baseline,
        )
        row["delta_abs_vs_baseline"] = deltas["delta_abs"]
        violations.extend(deltas["violations"])

    status_counts = {
        "ok": sum(1 for row in per_engine if row.get("status") == "ok"),
        "unavailable": sum(1 for row in per_engine if row.get("status") == "unavailable"),
        "error": sum(1 for row in per_engine if row.get("status") == "error"),
    }

    report = {
        "kind": "protocol_engine_parity",
        "primitive": normalized_primitive,
        "baseline_engine": baseline,
        "baseline_available": bool(baseline_ready),
        "engines_requested": requested,
        "threshold_policy": policy,
        "engine_results": per_engine,
        "violations": violations,
        "summary": {
            "engines_total": len(per_engine),
            "status_counts": status_counts,
            "violations_total": len(violations),
        },
    }
    return report


def _normalize_engine_ids(engine_ids: list[str] | tuple[str, ...] | None) -> list[str]:
    if not engine_ids:
        return ["qiskit", "analytic"]
    ordered: list[str] = []
    for item in engine_ids:
        key = str(item or "").strip().lower()
        if not key or key in ordered:
            continue
        ordered.append(key)
    return ordered or ["qiskit", "analytic"]


def _normalize_threshold_policy(
    threshold_policy: Mapping[str, Mapping[str, float]] | None,
) -> dict[str, dict[str, float]]:
    source = DEFAULT_THRESHOLD_POLICY if threshold_policy is None else threshold_policy
    normalized: dict[str, dict[str, float]] = {}
    for primitive, metric_limits in dict(source).items():
        primitive_key = str(primitive or "").strip().lower()
        if not primitive_key:
            continue
        normalized[primitive_key] = {}
        for metric_name, raw_limit in dict(metric_limits).items():
            metric_key = str(metric_name or "").strip().lower()
            if not metric_key:
                continue
            normalized[primitive_key][metric_key] = float(raw_limit)
    return normalized


def _evaluate_engine(*, engine_id: str, primitive: str, seed: int | None) -> dict[str, Any]:
    try:
        engine = get_protocol_engine(engine_id)
    except Exception as exc:
        return {
            "engine_id": engine_id,
            "status": "error",
            "available": False,
            "error": str(exc),
            "metrics": {},
            "metadata": {},
            "provenance": {},
        }

    available, reason = engine.availability()
    if not available:
        return {
            "engine_id": engine.engine_id,
            "status": "unavailable",
            "available": False,
            "error": str(reason or "dependency unavailable"),
            "metrics": {},
            "metadata": {},
            "provenance": engine.provenance(),
        }

    try:
        result = engine.run_primitive(primitive, seed=seed)
    except ProtocolEngineUnavailableError as exc:
        return {
            "engine_id": engine.engine_id,
            "status": "unavailable",
            "available": False,
            "error": str(exc),
            "metrics": {},
            "metadata": {},
            "provenance": engine.provenance(),
        }
    except Exception as exc:
        return {
            "engine_id": engine.engine_id,
            "status": "error",
            "available": True,
            "error": str(exc),
            "metrics": {},
            "metadata": {},
            "provenance": engine.provenance(),
        }

    return {
        "engine_id": engine.engine_id,
        "status": "ok",
        "available": True,
        "error": None,
        "metrics": {str(k): float(v) for k, v in dict(result.metrics).items()},
        "metadata": dict(result.metadata),
        "provenance": engine.provenance(),
    }


def _compute_deltas(
    *,
    primitive: str,
    baseline_metrics: Any,
    candidate_metrics: Any,
    threshold_policy: Mapping[str, Mapping[str, float]],
    candidate_engine_id: str,
    baseline_engine_id: str,
) -> dict[str, Any]:
    baseline_map = dict(baseline_metrics or {})
    candidate_map = dict(candidate_metrics or {})
    metric_names = sorted(set(baseline_map.keys()) & set(candidate_map.keys()))

    deltas: dict[str, float] = {}
    violations: list[dict[str, Any]] = []
    primitive_policy = dict(threshold_policy.get(primitive, {}))

    for metric in metric_names:
        baseline_value = float(baseline_map[metric])
        candidate_value = float(candidate_map[metric])
        delta_abs = abs(candidate_value - baseline_value)
        deltas[str(metric)] = float(delta_abs)

        threshold_abs = float(primitive_policy.get(str(metric), 0.0))
        if delta_abs > threshold_abs:
            violations.append(
                {
                    "primitive": primitive,
                    "metric": str(metric),
                    "candidate_engine": candidate_engine_id,
                    "baseline_engine": baseline_engine_id,
                    "baseline_value": baseline_value,
                    "candidate_value": candidate_value,
                    "delta_abs": float(delta_abs),
                    "threshold_abs": float(threshold_abs),
                }
            )

    return {
        "delta_abs": deltas,
        "violations": violations,
    }
