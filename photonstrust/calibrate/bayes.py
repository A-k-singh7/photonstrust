"""Lightweight Bayesian calibration via sampling."""

from __future__ import annotations

import math

import numpy as np

from photonstrust.calibrate.priors import (
    DEFAULT_DETECTOR_PRIORS,
    DEFAULT_EMITTER_PRIORS,
    DEFAULT_MEMORY_PRIORS,
)

DEFAULT_GATE_THRESHOLDS = {
    "min_effective_sample_size_ratio": 0.005,
    "max_r_hat_proxy": 1.10,
    "min_ppc_score": 0.20,
}


def fit_emitter_params(
    obs: dict,
    priors: dict | None = None,
    samples: int = 2000,
    enforce_gates: bool = False,
    gate_thresholds: dict | None = None,
) -> dict:
    priors = priors or DEFAULT_EMITTER_PRIORS
    return _fit(
        obs,
        priors,
        samples,
        enforce_gates=enforce_gates,
        gate_thresholds=gate_thresholds,
    )


def fit_detector_params(
    obs: dict,
    priors: dict | None = None,
    samples: int = 2000,
    enforce_gates: bool = False,
    gate_thresholds: dict | None = None,
) -> dict:
    priors = priors or DEFAULT_DETECTOR_PRIORS
    return _fit(
        obs,
        priors,
        samples,
        enforce_gates=enforce_gates,
        gate_thresholds=gate_thresholds,
    )


def fit_memory_params(
    obs: dict,
    priors: dict | None = None,
    samples: int = 2000,
    enforce_gates: bool = False,
    gate_thresholds: dict | None = None,
) -> dict:
    priors = priors or DEFAULT_MEMORY_PRIORS
    return _fit(
        obs,
        priors,
        samples,
        enforce_gates=enforce_gates,
        gate_thresholds=gate_thresholds,
    )


def _fit(
    obs: dict,
    priors: dict,
    samples: int,
    enforce_gates: bool,
    gate_thresholds: dict | None,
) -> dict:
    seed = 123
    rng = np.random.default_rng(seed)
    draws = {key: rng.uniform(low, high, samples) for key, (low, high) in priors.items()}

    weights = np.ones(samples)
    for key, target in obs.items():
        if key not in draws:
            continue
        low, high = priors[key]
        sigma = max(1e-6, 0.05 * abs(target) + 1e-6, 0.10 * (high - low))
        weights *= _gaussian_likelihood(draws[key], target, sigma)

    weights_sum = weights.sum()
    if weights_sum <= 0:
        weights = np.ones(samples) / samples
    else:
        weights = weights / weights_sum

    summary = {}
    for key, values in draws.items():
        mean = float(np.sum(values * weights))
        var = float(np.sum(weights * (values - mean) ** 2))
        summary[key] = {
            "mean": mean,
            "std": math.sqrt(var),
            "p5": float(np.quantile(values, 0.05)),
            "p95": float(np.quantile(values, 0.95)),
        }

    best_idx = int(np.argmax(weights))
    best = {key: float(values[best_idx]) for key, values in draws.items()}
    ess = float(1.0 / np.sum(weights**2))
    entropy = float(-np.sum(weights * np.log(np.maximum(weights, 1e-300))))
    max_entropy = math.log(max(samples, 2))
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    max_weight = float(np.max(weights))

    gate_diag = _gate_diagnostics(
        samples=samples,
        effective_sample_size=ess,
        normalized_weight_entropy=normalized_entropy,
        max_weight=max_weight,
        gate_thresholds=gate_thresholds,
    )

    if enforce_gates and not gate_diag["gate_pass"]:
        failures = ", ".join(gate_diag["gate_failures"]) or "unknown"
        raise ValueError(f"Calibration diagnostics gate failed: {failures}")

    diagnostics = {
        "seed": seed,
        "samples": samples,
        "effective_sample_size": ess,
        "weight_entropy": entropy,
        "normalized_weight_entropy": normalized_entropy,
        "max_weight": max_weight,
        **gate_diag,
    }

    return {
        "summary": summary,
        "best": best,
        "weights": weights.tolist(),
        "diagnostics": diagnostics,
    }


def _gate_diagnostics(
    samples: int,
    effective_sample_size: float,
    normalized_weight_entropy: float,
    max_weight: float,
    gate_thresholds: dict | None,
) -> dict:
    thresholds = {**DEFAULT_GATE_THRESHOLDS, **(gate_thresholds or {})}
    ess_ratio = effective_sample_size / max(samples, 1)
    uniform_weight = 1.0 / max(samples, 1)
    concentration = max(0.0, max_weight - uniform_weight) / max(uniform_weight, 1e-12)
    r_hat_proxy = 1.0 + 0.1 * min(1.0, concentration)
    ppc_score = normalized_weight_entropy

    failures = []
    if ess_ratio < thresholds["min_effective_sample_size_ratio"]:
        failures.append("ess_ratio")
    if r_hat_proxy > thresholds["max_r_hat_proxy"]:
        failures.append("r_hat_proxy")
    if ppc_score < thresholds["min_ppc_score"]:
        failures.append("ppc_score")

    gate_pass = len(failures) == 0
    return {
        "ess_ratio": ess_ratio,
        "r_hat_proxy": r_hat_proxy,
        "ppc_score": ppc_score,
        "gate_pass": gate_pass,
        "gate_failures": failures,
        "gate_thresholds": thresholds,
    }


def _gaussian_likelihood(values, target, sigma):
    return np.exp(-0.5 * ((values - target) / sigma) ** 2)
