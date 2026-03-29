"""Monte Carlo process variation and yield analysis for PIC circuits."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class YieldResult:
    """Result of a Monte Carlo yield analysis."""

    n_trials: int
    n_passed: int
    yield_fraction: float
    metric_mean: dict[str, float]
    metric_std: dict[str, float]
    sensitivity: dict[str, dict[str, float]]  # param -> metric -> dMetric/dParam
    parameter_variations: dict[str, float]  # param -> sigma used


def monte_carlo_yield(
    circuit_fn,  # callable(params_dict) -> dict of metrics
    nominal_params: dict[str, float],
    variations: dict[str, float],  # param_name -> sigma (1-std)
    pass_criteria: dict[str, tuple[float, float]],  # metric -> (min, max)
    n_trials: int = 1000,
    seed: int = 42,
    correlation_matrix: np.ndarray | None = None,
) -> YieldResult:
    """Monte Carlo process variation yield analysis.

    Parameters
    ----------
    circuit_fn : callable
        Takes a dict of parameters, returns dict of metrics.
    nominal_params : dict
        Nominal parameter values.
    variations : dict
        Standard deviation for each parameter.
    pass_criteria : dict
        For each metric, (min_val, max_val) that constitutes pass.
    n_trials : int
        Number of Monte Carlo trials.
    seed : int
        Random seed for reproducibility.
    correlation_matrix : np.ndarray or None
        Correlation between parameters (Cholesky decomposition applied).
        If None, parameters are independent.
    """
    rng = np.random.default_rng(seed)
    param_names = sorted(variations.keys())
    n_params = len(param_names)

    # Generate correlated random samples
    if correlation_matrix is not None and n_params > 1:
        L = np.linalg.cholesky(correlation_matrix)
        z = rng.standard_normal((n_trials, n_params))
        correlated = z @ L.T
    else:
        correlated = rng.standard_normal((n_trials, n_params))

    # Scale to actual variations
    sigmas = np.array([variations[p] for p in param_names])
    nominals = np.array([nominal_params[p] for p in param_names])
    samples = nominals + correlated * sigmas

    # Run trials
    all_metrics: dict[str, list[float]] = {}
    n_passed = 0

    for trial in range(n_trials):
        trial_params = dict(nominal_params)
        for i, p in enumerate(param_names):
            trial_params[p] = float(samples[trial, i])

        metrics = circuit_fn(trial_params)

        # Check pass criteria
        passed = True
        for metric_name, (lo, hi) in pass_criteria.items():
            val = metrics.get(metric_name, 0.0)
            if val < lo or val > hi:
                passed = False
                break
        if passed:
            n_passed += 1

        for k, v in metrics.items():
            all_metrics.setdefault(k, []).append(float(v))

    # Compute statistics
    metric_mean = {k: float(np.mean(v)) for k, v in all_metrics.items()}
    metric_std = {k: float(np.std(v)) for k, v in all_metrics.items()}

    # Compute sensitivity via finite difference (central difference at nominal)
    sensitivity: dict[str, dict[str, float]] = {}
    for p in param_names:
        delta = variations[p] * 0.01  # 1% of sigma
        if abs(delta) < 1e-15:
            sensitivity[p] = {k: 0.0 for k in all_metrics}
            continue

        params_plus = dict(nominal_params)
        params_plus[p] = nominal_params[p] + delta
        params_minus = dict(nominal_params)
        params_minus[p] = nominal_params[p] - delta

        m_plus = circuit_fn(params_plus)
        m_minus = circuit_fn(params_minus)

        sensitivity[p] = {}
        for k in all_metrics:
            sensitivity[p][k] = (m_plus.get(k, 0.0) - m_minus.get(k, 0.0)) / (
                2 * delta
            )

    return YieldResult(
        n_trials=n_trials,
        n_passed=n_passed,
        yield_fraction=n_passed / n_trials if n_trials > 0 else 0.0,
        metric_mean=metric_mean,
        metric_std=metric_std,
        sensitivity=sensitivity,
        parameter_variations={p: variations[p] for p in param_names},
    )
