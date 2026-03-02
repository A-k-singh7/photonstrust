"""GS-QKD-008 security requirement checks."""

from __future__ import annotations

from typing import Any

from photonstrust.compliance.checkers import (
    float_or_none,
    nearest_row,
    normalize_sweep_rows,
    row_value,
    scenario_distance_bounds,
    scenario_protocol_name,
)
from photonstrust.compliance.types import STATUS_FAIL, STATUS_NOT_ASSESSED, STATUS_PASS, STATUS_WARNING


_PROVEN_PROTOCOLS = {
    "BB84_DECOY",
    "MDI_QKD",
    "TF_QKD",
    "PM_QKD",
}


def check_s1(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 8.3: single-photon gain/yield must be positive."""

    del context, scenario
    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for S1.")

    yields: list[float] = []
    for row in rows:
        y1 = float_or_none(row_value(row, "single_photon_yield_lb", None))
        if y1 is None:
            y1 = float_or_none(row_value(row, "p_pair", None))
        if y1 is not None:
            yields.append(float(y1))

    if not yields:
        return _na("No single_photon_yield_lb/p_pair values available for S1.")

    min_yield = min(yields)
    return {
        "status": STATUS_PASS if min_yield > 0.0 else STATUS_FAIL,
        "computed_value": float(min_yield),
        "threshold": 0.0,
        "unit": "ratio",
        "notes": ["Minimum single-photon gain proxy across sweep rows."],
    }


def check_s2(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 8.4: phase error upper bound must remain below 0.5."""

    rows = normalize_sweep_rows(sweep_result)
    if not rows:
        return _na("No sweep rows available for S2.")

    d_spec = _d_spec_km(context=context, scenario=scenario, rows=rows)
    row = nearest_row(rows, d_spec)
    if row is None:
        return _na("No row found near d_spec_km for S2.")

    e1_ub: float | None = None
    if _has_dict_row_phase_error_input(sweep_result):
        e1_ub = float_or_none(row_value(row, "single_photon_error_ub", None))
    if e1_ub is None:
        e1_ub = _scenario_phase_error_override(scenario)
    if e1_ub is None:
        e1_ub = float_or_none(row_value(row, "single_photon_error_ub", None))
    if e1_ub is None:
        e1_ub = float_or_none(row_value(row, "qber_total", None))
    if e1_ub is None:
        return _na("Nearest row has no single_photon_error_ub/qber_total for S2.")

    threshold = 0.5
    return {
        "status": STATUS_PASS if e1_ub < threshold else STATUS_FAIL,
        "computed_value": float(e1_ub),
        "threshold": threshold,
        "unit": "ratio",
        "notes": [f"distance_km={row_value(row, 'distance_km', None)}"],
    }


def check_s3(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 8.5 proxy: classify multi-photon risk using mu operating point."""

    del sweep_result, context
    mu = _scenario_mu(scenario)
    if mu is None:
        return _na("Scenario does not provide protocol/source mu for S3.")

    if mu < 0.6:
        status = STATUS_PASS
    elif mu < 1.0:
        status = STATUS_WARNING
    else:
        status = STATUS_FAIL

    return {
        "status": status,
        "computed_value": float(mu),
        "threshold": {"pass_lt": 0.6, "warn_lt": 1.0},
        "unit": "mean_photons_per_pulse",
        "notes": ["S3 heuristic from ETSI brief: practical multi-photon risk thresholding by mu."],
    }


def check_s4(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 8.7 statement check: protocol family has known coherent-attack proof."""

    del sweep_result, context
    protocol_name = scenario_protocol_name(scenario).upper()
    if not protocol_name:
        return _na("Scenario does not expose protocol name for S4.")

    if protocol_name in _PROVEN_PROTOCOLS:
        status = STATUS_PASS
        notes = ["Protocol is in the curated coherent-attack proof set from the M2 brief."]
    else:
        status = STATUS_WARNING
        notes = ["Protocol is outside the curated proof set; manual security-proof review recommended."]

    return {
        "status": status,
        "computed_value": protocol_name,
        "threshold": sorted(_PROVEN_PROTOCOLS),
        "unit": "protocol",
        "notes": notes,
    }


def _d_spec_km(*, context: dict[str, Any], scenario: dict[str, Any], rows: list[dict[str, Any]]) -> float:
    from_context = float_or_none(context.get("d_spec_km"))
    if from_context is not None:
        return float(from_context)
    _, d_max = scenario_distance_bounds(scenario, rows)
    return float(d_max)


def _scenario_mu(scenario: dict[str, Any]) -> float | None:
    if not isinstance(scenario, dict):
        return None
    protocol = scenario.get("protocol")
    if isinstance(protocol, dict):
        value = float_or_none(protocol.get("mu"))
        if value is not None:
            return float(value)
    source = scenario.get("source")
    if isinstance(source, dict):
        value = float_or_none(source.get("mu"))
        if value is not None:
            return float(value)
    return None


def _scenario_phase_error_override(scenario: dict[str, Any]) -> float | None:
    protocol = (scenario or {}).get("protocol")
    if not isinstance(protocol, dict):
        return None
    return float_or_none(protocol.get("single_photon_error_ub"))


def _has_dict_row_phase_error_input(sweep_result: Any) -> bool:
    if isinstance(sweep_result, dict):
        rows = sweep_result.get("results")
    elif isinstance(sweep_result, list):
        rows = sweep_result
    else:
        rows = None
    if not isinstance(rows, list):
        return False
    for row in rows:
        if isinstance(row, dict) and float_or_none(row.get("single_photon_error_ub")) is not None:
            return True
    return False


def _na(note: str) -> dict[str, Any]:
    return {
        "status": STATUS_NOT_ASSESSED,
        "computed_value": None,
        "threshold": None,
        "unit": None,
        "notes": [str(note)],
    }
