"""Scenario configuration validation (v0.1).

This module is intentionally lightweight (no pydantic dependency) and provides:
- a small set of physics-meaningful range checks for scenario dicts
- a single aggregated exception type for CLI and batch workflows

The API server has its own schema-validation posture for graph-based workflows.
"""

from __future__ import annotations

from typing import Any, Callable


class ConfigValidationError(ValueError):
    """Raised when one or more scenarios fail validation."""


_Rule = tuple[str, Callable[[float], bool], str]


_RULES: list[_Rule] = [
    ("source.rep_rate_mhz", lambda v: v > 0.0, "must be > 0"),
    ("source.collection_efficiency", lambda v: 0.0 <= v <= 1.0, "must be in [0, 1]"),
    ("source.coupling_efficiency", lambda v: 0.0 <= v <= 1.0, "must be in [0, 1]"),
    ("source.g2_0", lambda v: 0.0 <= v <= 1.0, "must be in [0, 1]"),
    ("source.mu", lambda v: v >= 0.0, "must be >= 0"),
    ("detector.pde", lambda v: 0.0 <= v <= 1.0, "must be in [0, 1]"),
    ("detector.dark_counts_cps", lambda v: v >= 0.0, "must be >= 0"),
    ("detector.jitter_ps_fwhm", lambda v: v >= 0.0, "must be >= 0"),
    ("detector.dead_time_ns", lambda v: v >= 0.0, "must be >= 0"),
    ("detector.afterpulsing_prob", lambda v: 0.0 <= v <= 1.0, "must be in [0, 1]"),
    ("channel.fiber_loss_db_per_km", lambda v: v >= 0.0, "must be >= 0"),
    ("channel.connector_loss_db", lambda v: v >= 0.0, "must be >= 0"),
    ("timing.sync_drift_ps_rms", lambda v: v >= 0.0, "must be >= 0"),
]


def _get_path(obj: Any, path: str) -> Any | None:
    cur: Any = obj
    for part in str(path).split("."):
        if not isinstance(cur, dict):
            return None
        if part not in cur:
            return None
        cur = cur.get(part)
    return cur


def validate_scenario(scenario: dict[str, Any]) -> list[str]:
    """Validate a built scenario dict. Returns a list of error messages (empty = OK)."""

    errors: list[str] = []
    for path, check_fn, msg in _RULES:
        value = _get_path(scenario, path)
        if value is None:
            # Optional field in some scenario types.
            continue
        try:
            v = float(value)
        except Exception:
            errors.append(f"{path} = {value!r}: not a valid number")
            continue
        try:
            ok = bool(check_fn(v))
        except Exception:
            ok = False
        if not ok:
            errors.append(f"{path} = {value!r}: {msg}")
    return errors


def validate_scenarios(scenarios: list[dict[str, Any]]) -> list[str]:
    """Validate a list of scenarios, returning a flat list of labeled errors."""

    out: list[str] = []
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id", "") or "").strip() or "scenario"
        band = str(scenario.get("band", "") or "").strip() or "band"
        for err in validate_scenario(scenario):
            out.append(f"{scenario_id}/{band}: {err}")
    return out


def validate_scenarios_or_raise(scenarios: list[dict[str, Any]]) -> None:
    errors = validate_scenarios(scenarios)
    if not errors:
        return
    bullet_list = "\n".join(f"  - {e}" for e in errors)
    raise ConfigValidationError(f"Invalid scenario configuration:\n{bullet_list}")
