"""Tests for MCMC fitting in bayes module."""
from __future__ import annotations

import numpy as np
import pytest

from photonstrust.calibrate.bayes import mcmc_fit


class TestMCMCParameterRecovery:
    """Test that MCMC recovers known parameters."""

    def test_mcmc_parameter_recovery(self):
        """Fit known observation, check mean within 20% of target."""
        obs = {"alpha": 0.5, "beta": 3.0}
        priors = {"alpha": (0.0, 1.0), "beta": (0.0, 10.0)}

        result = mcmc_fit(obs, priors, n_chains=2, n_samples=2000, seed=42)

        assert "summary" in result
        assert "best" in result
        alpha_mean = result["summary"]["alpha"]["mean"]
        beta_mean = result["summary"]["beta"]["mean"]

        assert abs(alpha_mean - 0.5) / 0.5 < 0.20
        assert abs(beta_mean - 3.0) / 3.0 < 0.20


class TestMCMCConvergence:
    """Test MCMC convergence diagnostics."""

    def test_mcmc_convergence(self):
        """R-hat < 1.1 for all params."""
        obs = {"x": 5.0}
        priors = {"x": (0.0, 10.0)}

        result = mcmc_fit(obs, priors, n_chains=2, n_samples=3000, seed=99)

        for param, rhat in result["r_hat"].items():
            assert rhat < 1.1, f"R-hat for {param} = {rhat} >= 1.1"
        assert result["converged"] is True

    def test_mcmc_multiple_chains(self):
        """n_chains=3 produces valid output."""
        obs = {"p": 0.7}
        priors = {"p": (0.0, 1.0)}

        result = mcmc_fit(obs, priors, n_chains=3, n_samples=1000, seed=12)

        assert result["n_chains"] == 3
        assert result["n_samples_per_chain"] == 1000
        assert "p" in result["summary"]
        assert "p" in result["r_hat"]


class TestMCMCSummary:
    """Test MCMC summary statistics."""

    def test_mcmc_summary_has_intervals(self):
        """p5, p95 exist and p5 < mean < p95."""
        obs = {"val": 2.0}
        priors = {"val": (0.0, 5.0)}

        result = mcmc_fit(obs, priors, n_chains=2, n_samples=2000, seed=77)

        summary = result["summary"]["val"]
        assert "p5" in summary
        assert "p95" in summary
        assert "mean" in summary
        assert "std" in summary
        assert summary["p5"] < summary["mean"] < summary["p95"]

    def test_mcmc_best_is_mean(self):
        """best values should equal the summary means."""
        obs = {"a": 1.0, "b": 2.0}
        priors = {"a": (0.0, 3.0), "b": (0.0, 5.0)}

        result = mcmc_fit(obs, priors, n_chains=2, n_samples=1000, seed=33)

        for p in ["a", "b"]:
            assert result["best"][p] == pytest.approx(
                result["summary"][p]["mean"]
            )
