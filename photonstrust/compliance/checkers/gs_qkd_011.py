"""GS-QKD-011 component requirement checks."""

from __future__ import annotations

import math
from typing import Any

from photonstrust.compliance.checkers import float_or_none, normalize_sweep_rows, row_value
from photonstrust.compliance.types import STATUS_FAIL, STATUS_NOT_ASSESSED, STATUS_PASS, STATUS_WARNING


def check_c1(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 6.2.1: estimate source contribution to QBER."""

    del context
    source = (scenario or {}).get("source")
    protocol = (scenario or {}).get("protocol")
    source_type = ""
    if isinstance(source, dict):
        source_type = str(source.get("type", "")).strip().lower()

    if source_type == "spdc":
        mu = None
        if isinstance(source, dict):
            mu = float_or_none(source.get("mu"))
        if mu is None and isinstance(protocol, dict):
            mu = float_or_none(protocol.get("mu"))
        if mu is None:
            return _na("SPDC source type detected but no mu value found for C1.")
        contribution = float(mu) / 2.0
        if mu < 0.02:
            status = STATUS_PASS
        elif mu < 0.10:
            status = STATUS_WARNING
        else:
            status = STATUS_FAIL
        notes = ["SPDC heuristic from M2 brief: source_qber ~= mu/2."]
    else:
        misalignment = None
        if isinstance(protocol, dict):
            misalignment = float_or_none(protocol.get("misalignment_prob"))
        if misalignment is None:
            rows = normalize_sweep_rows(sweep_result)
            nearest = rows[0] if rows else None
            misalignment = (
                float_or_none(row_value(nearest, "q_misalignment", None))
                if nearest is not None
                else None
            )
        if misalignment is None:
            return _na("No misalignment/source contribution signal available for C1.")
        contribution = float(misalignment)
        if contribution < 0.01:
            status = STATUS_PASS
        elif contribution < 0.03:
            status = STATUS_WARNING
        else:
            status = STATUS_FAIL
        notes = ["WCP-style heuristic from M2 brief: source_qber ~= misalignment_prob."]

    return {
        "status": status,
        "computed_value": float(contribution),
        "threshold": {"pass_lt": 0.01, "warn_lt": 0.03},
        "unit": "ratio",
        "notes": notes,
    }


def check_c2(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 6.3.1: detector dark count rate <= 1e4 cps."""

    del sweep_result, context
    detector = (scenario or {}).get("detector")
    if not isinstance(detector, dict):
        return _na("Scenario is missing detector settings for C2.")

    dcr = float_or_none(detector.get("dark_counts_cps"))
    if dcr is None:
        return _na("detector.dark_counts_cps is missing for C2.")

    threshold = 1.0e4
    return {
        "status": STATUS_PASS if dcr <= threshold else STATUS_FAIL,
        "computed_value": float(dcr),
        "threshold": threshold,
        "unit": "cps",
        "notes": ["Detector dark count threshold from M2 brief."],
    }


def check_c3(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 6.3.2: detector PDE >= 10% (warning band 7-10%)."""

    del sweep_result, context
    detector = (scenario or {}).get("detector")
    if not isinstance(detector, dict):
        return _na("Scenario is missing detector settings for C3.")

    pde = float_or_none(detector.get("pde"))
    if pde is None:
        return _na("detector.pde is missing for C3.")

    if pde >= 0.10:
        status = STATUS_PASS
    elif pde >= 0.07:
        status = STATUS_WARNING
    else:
        status = STATUS_FAIL

    return {
        "status": status,
        "computed_value": float(pde),
        "threshold": {"pass_ge": 0.10, "warn_ge": 0.07},
        "unit": "ratio",
        "notes": ["Detector efficiency thresholding from M2 brief."],
    }


def check_c4(sweep_result: Any, scenario: dict[str, Any], *, context: dict[str, Any]) -> dict[str, Any]:
    """Clause 6.3.3: jitter-induced key-rate penalty should remain below threshold."""

    del sweep_result, context
    detector = (scenario or {}).get("detector")
    timing = (scenario or {}).get("timing")
    if not isinstance(detector, dict):
        return _na("Scenario is missing detector settings for C4.")

    jitter_fwhm_ps = float_or_none(detector.get("jitter_ps_fwhm"))
    if jitter_fwhm_ps is None:
        return _na("detector.jitter_ps_fwhm is missing for C4.")
    if jitter_fwhm_ps <= 0.0:
        penalty = 0.0
    else:
        sigma_ps = jitter_fwhm_ps / 2.355
        if sigma_ps <= 0.0:
            penalty = 0.0
        else:
            default_window_ps = max(200.0, 6.0 * sigma_ps)
            window_ps = (
                float_or_none(timing.get("coincidence_window_ps"))
                if isinstance(timing, dict)
                else None
            )
            if window_ps is None or window_ps <= 0.0:
                window_ps = default_window_ps

            # Detection fraction in a finite window under Gaussian timing spread.
            argument = float(window_ps) / (2.0 * math.sqrt(2.0) * sigma_ps)
            detection_fraction = max(0.0, min(1.0, math.erf(argument)))
            penalty = 1.0 - detection_fraction

    if penalty < 0.10:
        status = STATUS_PASS
    elif penalty < 0.20:
        status = STATUS_WARNING
    else:
        status = STATUS_FAIL

    return {
        "status": status,
        "computed_value": float(penalty),
        "threshold": {"pass_lt": 0.10, "warn_lt": 0.20},
        "unit": "fractional_penalty",
        "notes": ["Penalty model: 1 - erf(Tw / (2*sqrt(2)*sigma_jitter))."],
    }


def _na(note: str) -> dict[str, Any]:
    return {
        "status": STATUS_NOT_ASSESSED,
        "computed_value": None,
        "threshold": None,
        "unit": None,
        "notes": [str(note)],
    }
