"""GS-QKD-002 use-case compliance check."""

from __future__ import annotations

from typing import Any

from photonstrust.compliance.checkers import float_or_none, nearest_row, normalize_sweep_rows, row_value, scenario_protocol_name
from photonstrust.compliance.types import STATUS_FAIL, STATUS_NOT_ASSESSED, STATUS_PASS, STATUS_WARNING


_USE_CASES: dict[str, dict[str, Any]] = {
    "UC-1": {"max_distance_km": 100.0, "protocol_hint": "BB84"},
    "UC-2": {"max_distance_km": 1000.0, "protocol_hint": "BB84"},
    "UC-3": {"max_distance_km": None, "protocol_hint": None},
    "UC-4": {"max_distance_km": 20.0, "protocol_hint": None},
    "UC-5": {"max_distance_km": 5.0, "protocol_hint": None},
}


def check_use_case(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Use-case gate: distance envelope + minimum key rate under claimed use-case."""

    use_case_id = str(context.get("use_case_id", "") or "").strip().upper()
    if not use_case_id:
        return _na("use_case_id was not provided in context.")
    uc = _USE_CASES.get(use_case_id)
    if uc is None:
        return {
            "status": STATUS_WARNING,
            "computed_value": use_case_id,
            "threshold": sorted(_USE_CASES),
            "unit": "use_case_id",
            "notes": ["Unrecognized use_case_id; check skipped to warning."],
        }

    scenario_declared = _scenario_use_case_id(scenario).upper()
    if scenario_declared and scenario_declared != use_case_id:
        return {
            "status": STATUS_FAIL,
            "computed_value": scenario_declared,
            "threshold": use_case_id,
            "unit": "use_case_id",
            "notes": ["Scenario-declared use_case_id does not match requested context."],
        }

    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for GS-QKD-002 use-case evaluation.")

    d_spec = _resolve_distance_spec(context=context, scenario=scenario, rows=rows)
    max_distance = uc.get("max_distance_km")
    if max_distance is not None and d_spec > float(max_distance):
        return {
            "status": STATUS_FAIL,
            "computed_value": float(d_spec),
            "threshold": float(max_distance),
            "unit": "km",
            "notes": [f"{use_case_id} distance envelope exceeded."],
        }

    protocol_hint = uc.get("protocol_hint")
    protocol_name = scenario_protocol_name(scenario).upper()
    if protocol_hint and protocol_hint not in protocol_name:
        return {
            "status": STATUS_WARNING,
            "computed_value": protocol_name or None,
            "threshold": protocol_hint,
            "unit": "protocol",
            "notes": ["Protocol does not match the use-case protocol hint from GS-QKD-002 table."],
        }

    k_min_bps = float(context.get("k_min_bps", 1000.0) or 1000.0)
    row = nearest_row(rows, d_spec)
    if row is None:
        return _na("No row found near d_spec_km for use-case key-rate gate.")

    key_rate = float_or_none(row_value(row, "key_rate_bps", None))
    if key_rate is None:
        return _na("Nearest row has no key_rate_bps for use-case gate.")

    return {
        "status": STATUS_PASS if key_rate >= k_min_bps else STATUS_FAIL,
        "computed_value": float(key_rate),
        "threshold": float(k_min_bps),
        "unit": "bps",
        "notes": [f"distance_km={row_value(row, 'distance_km', None)}", f"use_case_id={use_case_id}"],
    }


def _resolve_distance_spec(*, context: dict[str, Any], scenario: dict[str, Any], rows: list[dict[str, Any]]) -> float:
    from_context = float_or_none(context.get("d_spec_km"))
    if from_context is not None:
        return float(from_context)

    direct = float_or_none((scenario or {}).get("distance_km"))
    if direct is not None:
        return float(direct)

    distances = (scenario or {}).get("distances_km")
    if isinstance(distances, list):
        parsed = [float_or_none(value) for value in distances]
        parsed = [d for d in parsed if d is not None]
        if parsed:
            return float(max(parsed))

    row_distances = [float_or_none(row_value(row, "distance_km", None)) for row in rows]
    row_distances = [d for d in row_distances if d is not None]
    if row_distances:
        return float(max(row_distances))
    return 50.0


def _scenario_use_case_id(scenario: dict[str, Any]) -> str:
    if not isinstance(scenario, dict):
        return ""
    direct = str(scenario.get("use_case_id", "") or "").strip()
    if direct:
        return direct
    metadata = scenario.get("metadata")
    if isinstance(metadata, dict):
        nested = str(metadata.get("use_case_id", "") or "").strip()
        if nested:
            return nested
    return ""


def _na(note: str) -> dict[str, Any]:
    return {
        "status": STATUS_NOT_ASSESSED,
        "computed_value": None,
        "threshold": None,
        "unit": None,
        "notes": [str(note)],
    }
