"""Tests for channel calibration routines."""
from __future__ import annotations

import numpy as np
import pytest

from photonstrust.calibrate.channel_calibration import (
    FiberCalibration,
    Cn2Profile,
    fit_fiber_loss,
    fit_cn2_from_scintillation,
)


class TestFiberLoss:
    """Test fiber loss extraction from OTDR traces."""

    def test_fiber_loss_extraction(self):
        """Linear OTDR trace -> loss_db_per_km within 5%."""
        loss_true = 0.2  # dB/km
        intercept_true = 0.0  # dBm

        d = np.linspace(0, 50, 100)
        p = intercept_true - loss_true * d
        rng = np.random.default_rng(10)
        p_noisy = p + rng.normal(0, 0.01, len(p))

        cal = fit_fiber_loss(d, p_noisy)

        assert isinstance(cal, FiberCalibration)
        assert abs(cal.loss_db_per_km - loss_true) / loss_true < 0.05
        assert cal.r_squared > 0.99

    def test_splice_detection(self):
        """Inject splice loss at known position, check detection."""
        loss = 0.2  # dB/km
        d = np.linspace(0, 50, 200)
        p = -loss * d

        # Insert a 1 dB splice at ~25 km
        splice_idx = 100  # corresponds to 25 km
        p[splice_idx:] -= 1.0  # sharp drop

        cal = fit_fiber_loss(d, p, splice_threshold_db=0.3)

        assert len(cal.splice_positions_km) >= 1
        # Check that a splice was detected near 25 km
        detected_near_25 = any(
            abs(pos - 25.0) < 2.0 for pos in cal.splice_positions_km
        )
        assert detected_near_25

    def test_fiber_r_squared(self):
        """Perfect linear data -> R^2 approximately 1.0."""
        d = np.linspace(0, 100, 50)
        p = 0.0 - 0.18 * d  # perfect line

        cal = fit_fiber_loss(d, p)

        assert abs(cal.r_squared - 1.0) < 1e-10
        assert abs(cal.loss_db_per_km - 0.18) < 1e-10


class TestCn2Inversion:
    """Test atmospheric turbulence Cn2 inversion."""

    def test_cn2_inversion(self):
        """Compute cn2 from known sigma_I2, check positive."""
        result = fit_cn2_from_scintillation(
            sigma_I2=0.1,
            aperture_m=0.3,
            zenith_deg=0.0,
            wavelength_m=785e-9,
            altitude_km=500.0,
        )

        assert isinstance(result, Cn2Profile)
        assert result.effective_cn2 > 0
        assert result.rytov_variance > 0
        assert 0 < result.aperture_averaging_factor <= 1.0

    def test_cn2_zenith_dependence(self):
        """Cn2 should change with zenith angle."""
        r0 = fit_cn2_from_scintillation(sigma_I2=0.1, zenith_deg=0.0)
        r45 = fit_cn2_from_scintillation(sigma_I2=0.1, zenith_deg=45.0)

        # Different zenith should give different effective Cn2
        assert r0.effective_cn2 != r45.effective_cn2
