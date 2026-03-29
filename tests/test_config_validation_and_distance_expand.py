from __future__ import annotations

import pytest

from photonstrust.config import _expand_distance
from photonstrust.validation import ConfigValidationError, validate_scenario, validate_scenarios_or_raise


def test_expand_distance_includes_stop_without_drift() -> None:
    distances = _expand_distance({"start": 0.0, "stop": 1.0, "step": 0.1})
    assert len(distances) == 11
    assert distances[0] == 0.0
    assert distances[-1] == 1.0


def test_expand_distance_rejects_non_positive_step() -> None:
    with pytest.raises(ValueError, match="step must be > 0"):
        _expand_distance({"start": 0.0, "stop": 1.0, "step": 0.0})


def test_validate_scenario_flags_out_of_range_values() -> None:
    scenario = {
        "scenario_id": "s1",
        "band": "c_1550",
        "source": {"rep_rate_mhz": 100, "collection_efficiency": 0.5, "coupling_efficiency": 0.5},
        "channel": {"fiber_loss_db_per_km": 0.2, "connector_loss_db": 1.5},
        "detector": {
            "pde": 1.2,
            "dark_counts_cps": -1.0,
            "jitter_ps_fwhm": 50.0,
            "dead_time_ns": 0.0,
            "afterpulsing_prob": 0.01,
        },
        "timing": {"sync_drift_ps_rms": 10.0},
    }
    errors = validate_scenario(scenario)
    assert any(e.startswith("detector.pde") for e in errors)
    assert any(e.startswith("detector.dark_counts_cps") for e in errors)


def test_validate_scenarios_or_raise_aggregates_errors() -> None:
    scenario = {
        "scenario_id": "s1",
        "band": "c_1550",
        "source": {"rep_rate_mhz": 0, "collection_efficiency": 0.5, "coupling_efficiency": 0.5},
    }
    with pytest.raises(ConfigValidationError, match="Invalid scenario configuration"):
        validate_scenarios_or_raise([scenario])
