"""Checker helpers for ETSI QKD compliance evaluation."""

from __future__ import annotations

from typing import Any


_BASE_ROW_FIELDS = (
    "distance_km",
    "key_rate_bps",
    "qber_total",
    "qber",
    "loss_db",
    "finite_key_enabled",
    "finite_key_epsilon",
    "single_photon_yield_lb",
    "single_photon_error_ub",
    "q_misalignment",
    "protocol_name",
)


def float_or_none(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed != parsed:  # NaN
        return None
    return parsed


def bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def row_value(row: dict[str, Any], key: str, default: Any = None) -> Any:
    return row.get(key, default) if isinstance(row, dict) else default


def normalize_sweep_rows(sweep_result: Any) -> list[dict[str, Any]]:
    rows = _extract_rows(sweep_result)
    out: list[dict[str, Any]] = []
    for row in rows:
        normalized = _coerce_row(row)
        if normalized is not None:
            out.append(normalized)

    out.sort(
        key=lambda r: (
            _sort_distance(r),
            _sort_key_rate(r),
            _sort_qber(r),
        )
    )
    return out


def nearest_row(rows: list[dict[str, Any]], distance_km: float | None) -> dict[str, Any] | None:
    if not rows:
        return None
    if distance_km is None:
        return rows[-1]
    target = float(distance_km)

    def _key(row: dict[str, Any]) -> tuple[float, float]:
        distance = float_or_none(row_value(row, "distance_km", None))
        if distance is None:
            return (1.0e30, 1.0e30)
        return (abs(distance - target), distance)

    return min(rows, key=_key)


def rows_up_to_distance(rows: list[dict[str, Any]], distance_km: float | None) -> list[dict[str, Any]]:
    if distance_km is None:
        return list(rows)
    limit = float(distance_km)
    selected = []
    for row in rows:
        distance = float_or_none(row_value(row, "distance_km", None))
        if distance is None:
            continue
        if distance <= limit:
            selected.append(row)
    return selected


def scenario_protocol_name(scenario: dict[str, Any]) -> str:
    if not isinstance(scenario, dict):
        return ""
    raw = scenario.get("protocol")
    if isinstance(raw, dict):
        name = raw.get("name")
        if name is not None:
            return str(name).strip()
    if isinstance(raw, str):
        return raw.strip()
    return ""


def scenario_distance_bounds(
    scenario: dict[str, Any],
    rows: list[dict[str, Any]],
) -> tuple[float, float]:
    distances = _scenario_distances(scenario)
    if not distances:
        row_distances = [
            float_or_none(row_value(row, "distance_km", None))
            for row in rows
        ]
        distances = [d for d in row_distances if d is not None]

    if not distances:
        return (0.0, 50.0)
    return (float(min(distances)), float(max(distances)))


def _extract_rows(sweep_result: Any) -> list[Any]:
    if isinstance(sweep_result, dict):
        raw = sweep_result.get("results")
        return raw if isinstance(raw, list) else []
    if isinstance(sweep_result, list):
        return sweep_result
    return []


def _coerce_row(row: Any) -> dict[str, Any] | None:
    if isinstance(row, dict):
        return dict(row)

    row_dict = getattr(row, "__dict__", None)
    if isinstance(row_dict, dict):
        return dict(row_dict)

    payload: dict[str, Any] = {}
    has_value = False
    for key in _BASE_ROW_FIELDS:
        value = getattr(row, key, None)
        if value is not None:
            has_value = True
        payload[key] = value
    if has_value:
        return payload
    return None


def _sort_distance(row: dict[str, Any]) -> float:
    distance = float_or_none(row_value(row, "distance_km", None))
    return distance if distance is not None else 1.0e30


def _sort_key_rate(row: dict[str, Any]) -> float:
    key_rate = float_or_none(row_value(row, "key_rate_bps", None))
    return key_rate if key_rate is not None else 0.0


def _sort_qber(row: dict[str, Any]) -> float:
    qber = float_or_none(row_value(row, "qber_total", None))
    if qber is None:
        qber = float_or_none(row_value(row, "qber", None))
    return qber if qber is not None else 0.0


def _scenario_distances(scenario: dict[str, Any]) -> list[float]:
    if not isinstance(scenario, dict):
        return []
    out: list[float] = []
    direct = float_or_none(scenario.get("distance_km"))
    if direct is not None:
        out.append(float(direct))
    raw = scenario.get("distances_km")
    if isinstance(raw, list):
        for value in raw:
            parsed = float_or_none(value)
            if parsed is not None:
                out.append(float(parsed))
    return out
