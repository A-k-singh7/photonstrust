"""Tests for experimental validation routines."""
from __future__ import annotations

import numpy as np
import pytest

from photonstrust.calibrate.experimental_validation import (
    ValidationResult,
    PUBLISHED_EXPERIMENTS,
    validate_against_experiment,
)


class TestBB84Validation:
    """Test validation against BB84 published data."""

    def test_bb84_perfect_match(self):
        """Exact published rates -> chi_squared ~ 0, pass_within_3x=True."""
        exp = PUBLISHED_EXPERIMENTS["bb84_gobby_2004"]
        sim_rates = list(exp["key_rates_bps"])

        result = validate_against_experiment("bb84_gobby_2004", sim_rates)

        assert isinstance(result, ValidationResult)
        assert result.chi_squared < 1e-10
        assert result.pass_within_3x is True
        assert result.n_points == len(exp["key_rates_bps"])
        assert result.max_residual_ratio == pytest.approx(1.0)

    def test_bb84_within_3x(self):
        """Rates within factor of 3 -> pass_within_3x=True."""
        exp = PUBLISHED_EXPERIMENTS["bb84_gobby_2004"]
        # Multiply each rate by a factor between 0.5 and 2.0
        sim_rates = [r * 2.0 for r in exp["key_rates_bps"]]

        result = validate_against_experiment("bb84_gobby_2004", sim_rates)

        assert result.pass_within_3x is True
        assert result.max_residual_ratio <= 3.0

    def test_bb84_fails_if_far(self):
        """Rates 10x off -> pass_within_3x=False."""
        exp = PUBLISHED_EXPERIMENTS["bb84_gobby_2004"]
        sim_rates = [r * 10.0 for r in exp["key_rates_bps"]]

        result = validate_against_experiment("bb84_gobby_2004", sim_rates)

        assert result.pass_within_3x is False
        assert result.max_residual_ratio >= 10.0


class TestErrorHandling:
    """Test error handling in validation."""

    def test_unknown_experiment_raises(self):
        """Bad name -> ValueError."""
        with pytest.raises(ValueError, match="Unknown experiment"):
            validate_against_experiment("nonexistent_experiment", [1, 2, 3])

    def test_length_mismatch_raises(self):
        """Wrong number of simulated rates -> ValueError."""
        with pytest.raises(ValueError, match="Length mismatch"):
            validate_against_experiment("bb84_gobby_2004", [1.0, 2.0])


class TestCustomData:
    """Test custom published data support."""

    def test_custom_data(self):
        """Pass custom published_data dict."""
        custom = {
            "distances_km": [0, 10, 20],
            "key_rates_bps": [1000, 500, 100],
        }
        sim_rates = [1000, 500, 100]

        result = validate_against_experiment(
            "my_custom", sim_rates, published_data=custom
        )

        assert result.experiment_name == "my_custom"
        assert result.pass_within_3x is True
        assert result.chi_squared < 1e-10

    def test_custom_data_with_offset(self):
        """Custom data where sim is off by 2x still passes 3x check."""
        custom = {
            "distances_km": [0, 50],
            "key_rates_bps": [1000, 100],
        }
        sim_rates = [2000, 200]

        result = validate_against_experiment(
            "custom_offset", sim_rates, published_data=custom
        )

        assert result.pass_within_3x is True
