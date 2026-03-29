"""Tests for the predictive maintenance engine (Feature 12)."""

from __future__ import annotations

from photonstrust.maintenance.degradation import (
    detector_pde_degradation,
    estimate_component_health,
    fiber_loss_increase,
    source_coherence_degradation,
)
from photonstrust.maintenance.predictor import predict_failures
from photonstrust.maintenance.scheduler import optimize_maintenance_schedule


# -- degradation model tests -------------------------------------------------

def test_detector_pde_decays_over_time() -> None:
    """PDE at 100 000 hrs should be lower than initial PDE."""
    initial = 0.9
    aged = detector_pde_degradation(initial, 100_000, detector_class="snspd")
    assert aged < initial


def test_fiber_loss_increases() -> None:
    """Fiber loss at 100 000 hrs should exceed initial loss."""
    initial = 0.2
    aged = fiber_loss_increase(initial, 100_000)
    assert aged > initial


def test_source_g2_increases() -> None:
    """g2 at 100 000 hrs should be worse (higher) than initial."""
    initial = 0.01
    aged = source_coherence_degradation(initial, 100_000, source_type="emitter_cavity")
    assert aged > initial


def test_snspd_more_stable_than_ingaas() -> None:
    """SNSPD has a lower decay rate so its PDE should be higher at the same age."""
    initial = 0.9
    age = 100_000
    snspd = detector_pde_degradation(initial, age, detector_class="snspd")
    ingaas = detector_pde_degradation(initial, age, detector_class="ingaas")
    assert snspd > ingaas


# -- failure prediction tests ------------------------------------------------

def test_failure_prediction_within_horizon() -> None:
    """A component near EOL should generate a failure prediction."""
    # InGaAs detector with lambda=5e-5, at 13 000 hours with initial=0.9, threshold=0.5
    # EOL ~ log(0.9/0.5)/5e-5 ~ 11756 hours => already past EOL
    components = [
        {
            "component_id": "det_1",
            "component_type": "detector",
            "initial_value": 0.9,
            "age_hours": 13_000,
            "threshold": 0.5,
            "detector_class": "ingaas",
        }
    ]
    preds = predict_failures("link_a", components, prediction_horizon_days=365)
    assert len(preds) >= 1
    assert preds[0].urgency == "immediate"


def test_failure_prediction_healthy_component() -> None:
    """A fresh SNSPD component should not generate a failure prediction."""
    components = [
        {
            "component_id": "det_2",
            "component_type": "detector",
            "initial_value": 0.9,
            "age_hours": 100,
            "threshold": 0.5,
            "detector_class": "snspd",
        }
    ]
    preds = predict_failures("link_b", components, prediction_horizon_days=365)
    assert len(preds) == 0


# -- scheduler tests ---------------------------------------------------------

def test_schedule_respects_budget() -> None:
    """With a tiny budget not all actions should be fully costed."""
    components = [
        {
            "component_id": "det_1",
            "component_type": "detector",
            "initial_value": 0.9,
            "age_hours": 13_000,
            "threshold": 0.5,
            "detector_class": "ingaas",
        },
        {
            "component_id": "src_1",
            "component_type": "source",
            "initial_value": 0.01,
            "age_hours": 900_000,
            "threshold": 0.1,
            "source_type": "emitter_cavity",
        },
    ]
    preds = predict_failures("link_c", components, prediction_horizon_days=365)
    schedule = optimize_maintenance_schedule(preds, budget_usd=10.0)
    # With budget of $10, every real action exceeds the budget so all get deferred
    # total_estimated_cost should be 0 since nothing fits
    assert schedule.total_estimated_cost_usd <= 10.0


def test_schedule_ordering_by_urgency() -> None:
    """Immediate-urgency actions should receive priority 1."""
    components = [
        {
            "component_id": "det_1",
            "component_type": "detector",
            "initial_value": 0.9,
            "age_hours": 13_000,
            "threshold": 0.5,
            "detector_class": "ingaas",
        }
    ]
    preds = predict_failures("link_d", components, prediction_horizon_days=365)
    assert len(preds) >= 1
    schedule = optimize_maintenance_schedule(preds)
    # "immediate" maps to priority 1
    assert schedule.actions[0].priority == 1


# -- component health estimation test ----------------------------------------

def test_component_health_estimation() -> None:
    """Performance fraction must be in [0, 1]."""
    for ctype, iv, thresh, kwargs in [
        ("detector", 0.9, 0.5, {"detector_class": "snspd"}),
        ("fiber", 0.2, 0.25, {}),
        ("source", 0.01, 0.1, {"source_type": "spdc"}),
    ]:
        health = estimate_component_health(
            ctype, iv, 50_000, threshold=thresh, **kwargs,
        )
        assert 0.0 <= health.current_performance <= 1.0
        assert health.predicted_eol_hours > 0
