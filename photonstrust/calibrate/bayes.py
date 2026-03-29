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


def mcmc_fit(
    obs: dict,
    priors: dict,
    n_chains: int = 2,
    n_samples: int = 2000,
    seed: int = 42,
) -> dict:
    """Metropolis-Hastings MCMC with R-hat convergence diagnostic.

    Parameters
    ----------
    obs : dict
        Observed data (parameter name -> target value).
    priors : dict
        Prior ranges (parameter name -> (low, high)).
    n_chains : int
        Number of independent chains.
    n_samples : int
        Samples per chain (after burn-in).
    """
    rng = np.random.default_rng(seed)
    param_names = sorted(priors.keys())
    n_params = len(param_names)
    burn_in = n_samples // 4
    total_samples = n_samples + burn_in

    all_chains = []

    for chain_idx in range(n_chains):
        # Initialize from prior
        current = {}
        for p in param_names:
            lo, hi = priors[p]
            current[p] = rng.uniform(lo, hi)

        # Proposal sigma: 5% of prior range
        proposal_sigma = {p: 0.05 * (priors[p][1] - priors[p][0]) for p in param_names}

        def log_likelihood(params):
            ll = 0.0
            for key, target in obs.items():
                if key in params:
                    lo, hi = priors[key]
                    sigma = max(1e-6, 0.05 * abs(target) + 1e-6, 0.10 * (hi - lo))
                    ll -= 0.5 * ((params[key] - target) / sigma) ** 2
            return ll

        chain = []
        current_ll = log_likelihood(current)

        for step in range(total_samples):
            # Propose
            proposed = {}
            for p in param_names:
                lo, hi = priors[p]
                proposed[p] = np.clip(
                    current[p] + rng.normal(0, proposal_sigma[p]),
                    lo, hi,
                )

            proposed_ll = log_likelihood(proposed)
            log_alpha = proposed_ll - current_ll

            if log_alpha > 0 or rng.uniform() < math.exp(min(log_alpha, 0)):
                current = proposed
                current_ll = proposed_ll

            if step >= burn_in:
                chain.append({p: current[p] for p in param_names})

        all_chains.append(chain)

    # Combine chains
    all_samples = {p: [] for p in param_names}
    for chain in all_chains:
        for sample in chain:
            for p in param_names:
                all_samples[p].append(sample[p])

    summary = {}
    for p in param_names:
        vals = np.array(all_samples[p])
        summary[p] = {
            "mean": float(np.mean(vals)),
            "std": float(np.std(vals)),
            "p5": float(np.percentile(vals, 5)),
            "p95": float(np.percentile(vals, 95)),
        }

    # R-hat diagnostic (Gelman-Rubin)
    r_hat = {}
    for p in param_names:
        chain_means = []
        chain_vars = []
        for chain in all_chains:
            vals = np.array([s[p] for s in chain])
            chain_means.append(np.mean(vals))
            chain_vars.append(np.var(vals, ddof=1))

        B = n_samples * np.var(chain_means, ddof=1)  # between-chain variance
        W = np.mean(chain_vars)  # within-chain variance

        var_hat = (1 - 1/n_samples) * W + B / n_samples
        r_hat[p] = float(math.sqrt(var_hat / max(W, 1e-30)))

    best = {p: summary[p]["mean"] for p in param_names}

    return {
        "summary": summary,
        "best": best,
        "r_hat": r_hat,
        "n_chains": n_chains,
        "n_samples_per_chain": n_samples,
        "converged": all(v < 1.1 for v in r_hat.values()),
    }
