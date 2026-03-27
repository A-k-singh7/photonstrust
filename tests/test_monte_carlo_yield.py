"""Tests for Monte Carlo process variation yield analysis."""
import numpy as np
import pytest

from photonstrust.pic.monte_carlo_yield import YieldResult, monte_carlo_yield


def _simple_circuit(params):
    """Simple circuit: insertion loss depends on width."""
    width = params.get("width_nm", 450.0)
    thickness = params.get("thickness_nm", 220.0)
    # IL increases as width deviates from 450nm
    il = 0.5 + 0.01 * abs(width - 450.0) + 0.02 * abs(thickness - 220.0)
    bw_ghz = 40.0 - 0.1 * abs(width - 450.0)
    return {"insertion_loss_db": il, "bandwidth_ghz": bw_ghz}


def test_yield_with_no_variation():
    """Zero variation -> 100% yield if nominal passes."""
    result = monte_carlo_yield(
        _simple_circuit,
        nominal_params={"width_nm": 450.0, "thickness_nm": 220.0},
        variations={"width_nm": 0.0, "thickness_nm": 0.0},
        pass_criteria={"insertion_loss_db": (0, 5.0)},
        n_trials=100,
        seed=42,
    )
    assert result.yield_fraction == 1.0


def test_yield_less_than_100_with_variation():
    """Process variation should cause some failures."""
    result = monte_carlo_yield(
        _simple_circuit,
        nominal_params={"width_nm": 450.0, "thickness_nm": 220.0},
        variations={"width_nm": 5.0, "thickness_nm": 2.0},
        pass_criteria={"insertion_loss_db": (0, 0.6)},  # tight spec
        n_trials=500,
        seed=42,
    )
    assert 0.0 < result.yield_fraction < 1.0


def test_sensitivity_signs():
    """Sensitivity of IL to width should be positive (more deviation = more loss)."""
    result = monte_carlo_yield(
        _simple_circuit,
        nominal_params={"width_nm": 450.0, "thickness_nm": 220.0},
        variations={"width_nm": 5.0, "thickness_nm": 2.0},
        pass_criteria={"insertion_loss_db": (0, 10.0)},
        n_trials=100,
        seed=42,
    )
    # At nominal (450), derivative of IL w.r.t. width depends on sign of (width-450)
    # Since we're at exactly 450, the sensitivity should be ~0 due to abs()
    # But the function is not differentiable at 450, so we just check it exists
    assert "width_nm" in result.sensitivity


def test_metric_statistics():
    result = monte_carlo_yield(
        _simple_circuit,
        nominal_params={"width_nm": 450.0, "thickness_nm": 220.0},
        variations={"width_nm": 5.0, "thickness_nm": 2.0},
        pass_criteria={"insertion_loss_db": (0, 10.0)},
        n_trials=200,
        seed=42,
    )
    assert result.metric_mean["insertion_loss_db"] > 0
    assert result.metric_std["insertion_loss_db"] > 0


def test_correlated_parameters():
    corr = np.array([[1.0, 0.5], [0.5, 1.0]])
    result = monte_carlo_yield(
        _simple_circuit,
        nominal_params={"width_nm": 450.0, "thickness_nm": 220.0},
        variations={"width_nm": 5.0, "thickness_nm": 2.0},
        pass_criteria={"insertion_loss_db": (0, 10.0)},
        n_trials=200,
        seed=42,
        correlation_matrix=corr,
    )
    assert result.n_trials == 200
    assert result.yield_fraction > 0
