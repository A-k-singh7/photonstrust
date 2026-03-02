"""GS-QKD-004 functional requirement checks."""

from __future__ import annotations

from typing import Any

from photonstrust.compliance.checkers import (
    float_or_none,
    nearest_row,
    normalize_sweep_rows,
    row_value,
    rows_up_to_distance,
    scenario_distance_bounds,
)
from photonstrust.compliance.types import STATUS_FAIL, STATUS_NOT_ASSESSED, STATUS_PASS


def check_f1(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 7.2: key rate at operational distance must meet minimum threshold."""

    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for F1 key-rate assessment.")

    k_min_bps = float(context.get("k_min_bps", 1000.0) or 1000.0)
    d_spec_km = _d_spec_km(context=context, scenario=scenario, rows=rows)
    row = nearest_row(rows, d_spec_km)
    if row is None:
        return _na("No row found near d_spec_km for F1.")

    key_rate = float_or_none(row_value(row, "key_rate_bps", None))
    if key_rate is None:
        return _na("Nearest row has no key_rate_bps for F1.")

    return {
        "status": STATUS_PASS if key_rate >= k_min_bps else STATUS_FAIL,
        "computed_value": float(key_rate),
        "threshold": float(k_min_bps),
        "unit": "bps",
        "notes": [f"distance_km={row_value(row, 'distance_km', None)}"],
    }


def check_f2(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 7.3: QBER must remain <= 11% for d <= d_spec."""

    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for F2 QBER assessment.")

    d_spec_km = _d_spec_km(context=context, scenario=scenario, rows=rows)
    bounded_rows = rows_up_to_distance(rows, d_spec_km)
    qbers = [_qber_ratio(row) for row in bounded_rows]
    qbers = [q for q in qbers if q is not None]
    if not qbers:
        return _na("No qber_total values available in sweep rows for d <= d_spec.")

    qber_max = float(context.get("qber_max", 0.11) or 0.11)
    worst_qber = max(qbers)
    return {
        "status": STATUS_PASS if worst_qber <= qber_max else STATUS_FAIL,
        "computed_value": float(worst_qber),
        "threshold": float(qber_max),
        "unit": "ratio",
        "notes": [f"checked_points={len(qbers)}", f"d_spec_km={d_spec_km:.6g}"],
    }


def check_f3(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 7.4: key rate should stay positive across the operating range."""

    del context
    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for F3 positivity assessment.")

    d_min, d_max = scenario_distance_bounds(scenario, rows)
    in_range_rates: list[tuple[float, float]] = []
    for row in rows:
        distance = float_or_none(row_value(row, "distance_km", None))
        rate = float_or_none(row_value(row, "key_rate_bps", None))
        if distance is None or rate is None:
            continue
        if d_min - 1e-12 <= distance <= d_max + 1e-12:
            in_range_rates.append((distance, rate))

    if not in_range_rates:
        return _na("No numeric key_rate_bps rows in the scenario operating range for F3.")

    min_distance, min_rate = min(in_range_rates, key=lambda item: (item[1], item[0]))
    status = STATUS_PASS if min_rate > 0.0 else STATUS_FAIL
    notes = [f"distance_window_km=[{d_min:.6g},{d_max:.6g}]"]
    if min_rate <= 0.0:
        notes.append(f"key_rate_zero_or_negative_at_km={min_distance:.6g}")
    return {
        "status": status,
        "computed_value": float(min_rate),
        "threshold": 0.0,
        "unit": "bps",
        "notes": notes,
    }


def check_f4(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 7.5: composable epsilon target must be met when finite-key is enabled."""

    rows = normalize_sweep_rows(sweep_result)
    epsilon_target = float(context.get("epsilon_target", 1e-10) or 1e-10)

    scenario_fk = (scenario or {}).get("finite_key")
    scenario_fk_enabled = isinstance(scenario_fk, dict) and bool(scenario_fk.get("enabled", False))
    row_fk_enabled = any(bool(row_value(row, "finite_key_enabled", False)) for row in rows)
    if not (scenario_fk_enabled or row_fk_enabled):
        return _na("finite_key is not enabled; F4 not assessed.")

    eps_values: list[float] = []
    for row in rows:
        epsilon = float_or_none(row_value(row, "finite_key_epsilon", None))
        if epsilon is not None and epsilon > 0.0:
            eps_values.append(float(epsilon))

    if not eps_values:
        return _na("finite_key enabled but no finite_key_epsilon values were produced.")

    worst_eps = max(eps_values)
    return {
        "status": STATUS_PASS if worst_eps <= epsilon_target else STATUS_FAIL,
        "computed_value": float(worst_eps),
        "threshold": float(epsilon_target),
        "unit": "epsilon",
        "notes": ["Worst finite_key_epsilon across assessed sweep points."],
    }


def _qber_ratio(row: dict[str, Any]) -> float | None:
    qber = float_or_none(row_value(row, "qber_total", None))
    if qber is None:
        qber = float_or_none(row_value(row, "qber", None))
    if qber is None:
        return None
    if qber > 1.0:
        return float(qber / 100.0)
    return float(qber)


def _d_spec_km(*, context: dict[str, Any], scenario: dict[str, Any], rows: list[dict[str, Any]]) -> float:
    from_context = float_or_none(context.get("d_spec_km"))
    if from_context is not None:
        return float(from_context)
    _, d_max = scenario_distance_bounds(scenario, rows)
    return float(d_max)


def _na(note: str) -> dict[str, Any]:
    return {
        "status": STATUS_NOT_ASSESSED,
        "computed_value": None,
        "threshold": None,
        "unit": None,
        "notes": [str(note)],
    }
