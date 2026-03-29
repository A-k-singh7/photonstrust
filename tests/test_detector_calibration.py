"""Tests for detector calibration routines."""
from __future__ import annotations

import numpy as np
import pytest

from photonstrust.calibrate.detector_calibration import (
    SNSPDCalibration,
    InGaAsCalibration,
    DCRCalibration,
    _sigmoid,
    _multi_exp,
    _arrhenius,
    fit_snspd_efficiency_curve,
    fit_ingaas_afterpulsing,
    fit_dcr_temperature,
)


class TestSNSPDSigmoidFit:
    """Test SNSPD efficiency sigmoid curve fitting."""

    def test_snspd_sigmoid_fit_recovery(self):
        """Generate sigmoid data, fit, check params within 10%."""
        # True parameters
        eta_max_true = 0.85
        I_50_true = 12.0  # uA
        k_true = 1.5

        I = np.linspace(5, 20, 50)
        eta = _sigmoid(I, eta_max_true, I_50_true, k_true)
        # Add small noise
        rng = np.random.default_rng(42)
        eta_noisy = eta + rng.normal(0, 0.005, len(eta))
        eta_noisy = np.clip(eta_noisy, 0, 1)

        cal = fit_snspd_efficiency_curve(I, eta_noisy)

        assert abs(cal.eta_max - eta_max_true) / eta_max_true < 0.10
        assert abs(cal.I_50 - I_50_true) / I_50_true < 0.10
        assert abs(cal.k - k_true) / k_true < 0.10
        assert cal.r_squared > 0.95

    def test_snspd_eta_max_bounds(self):
        """eta_max should be between 0 and 1."""
        I = np.linspace(5, 20, 30)
        eta = _sigmoid(I, 0.90, 12.0, 2.0)
        rng = np.random.default_rng(7)
        eta_noisy = eta + rng.normal(0, 0.01, len(eta))
        eta_noisy = np.clip(eta_noisy, 0, 1)

        cal = fit_snspd_efficiency_curve(I, eta_noisy)
        assert 0 <= cal.eta_max <= 1.0


class TestInGaAsAfterpulsing:
    """Test InGaAs APD afterpulsing fit."""

    def test_ingaas_afterpulsing_fit(self):
        """Generate bi-exponential, fit, check R^2 > 0.9."""
        A1, tau1 = 0.05, 1.0  # fast trap
        A2, tau2 = 0.02, 5.0  # slow trap

        t = np.linspace(0.1, 20.0, 100)
        rates = A1 * np.exp(-t / tau1) + A2 * np.exp(-t / tau2)
        rng = np.random.default_rng(99)
        rates_noisy = rates + rng.normal(0, 0.001, len(rates))
        rates_noisy = np.maximum(rates_noisy, 0)

        cal = fit_ingaas_afterpulsing(t, rates_noisy, n_traps=2)

        assert isinstance(cal, InGaAsCalibration)
        assert cal.r_squared > 0.9
        assert len(cal.amplitudes) == 2
        assert len(cal.time_constants_us) == 2
        assert cal.total_afterpulse_prob > 0


class TestDCRArrhenius:
    """Test dark count rate vs temperature Arrhenius fitting."""

    def test_dcr_arrhenius_fit(self):
        """Generate Arrhenius data at 200-300K, fit, check E_a within 20%."""
        E_a_true = 0.35  # eV
        dcr_0_true = 100.0  # Hz at T_0
        T_0 = 200.0  # K

        T = np.linspace(200, 300, 20)
        dcr = _arrhenius(T, dcr_0_true, T_0, E_a_true)
        rng = np.random.default_rng(55)
        # Add multiplicative noise
        dcr_noisy = dcr * (1 + rng.normal(0, 0.02, len(dcr)))
        dcr_noisy = np.maximum(dcr_noisy, 1.0)

        cal = fit_dcr_temperature(T, dcr_noisy)

        assert isinstance(cal, DCRCalibration)
        assert abs(cal.E_a_eV - E_a_true) / E_a_true < 0.20
        assert cal.T_0_K == T_0
        assert cal.r_squared > 0.95
        assert cal.dcr_0 > 0
