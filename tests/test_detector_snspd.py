"""Tests for SNSPD detector models."""

from __future__ import annotations

import pytest

from photonstrust.physics.detector_snspd import (
    SNSPD_MATERIAL_PRESETS,
    snspd_count_rate_saturation,
    snspd_dark_count_rate,
    snspd_recovery_time,
    snspd_timing_jitter,
    snspd_wavelength_efficiency,
)


# ---- Count rate saturation tests -------------------------------------------

def test_low_rate_no_saturation():
    """At low input rates, output ~ input * eta."""
    r = snspd_count_rate_saturation(1e3, detection_efficiency=0.9, recovery_time_ns=40.0)
    # 1 kHz << 1/40ns = 25 MHz, so negligible saturation
    assert abs(r.output_rate_cps - 1e3 * 0.9) / (1e3 * 0.9) < 0.01
    assert r.saturation_fraction < 0.01


def test_high_rate_saturation():
    """At high input rates, output approaches 1/tau."""
    r = snspd_count_rate_saturation(1e10, detection_efficiency=0.93, recovery_time_ns=40.0)
    max_rate = 1.0 / (40e-9)  # 25 MHz
    assert r.output_rate_cps < max_rate
    assert r.saturation_fraction > 0.9
    assert r.saturated_efficiency < r.detection_efficiency


def test_saturation_formula():
    """CR_out = CR_in * eta / (1 + CR_in * eta * tau)."""
    cr_in = 1e7
    eta = 0.93
    tau = 40e-9
    expected = cr_in * eta / (1 + cr_in * eta * tau)
    r = snspd_count_rate_saturation(cr_in, detection_efficiency=eta, recovery_time_ns=40.0)
    assert abs(r.output_rate_cps - expected) < 1.0


def test_zero_input_rate():
    r = snspd_count_rate_saturation(0.0)
    assert r.output_rate_cps == 0.0
    assert r.saturated_efficiency == r.detection_efficiency


def test_max_count_rate():
    r = snspd_count_rate_saturation(1e6, recovery_time_ns=100.0)
    assert r.max_count_rate_cps == pytest.approx(1e7, rel=0.01)  # 1/100ns


# ---- Recovery time tests --------------------------------------------------

def test_recovery_time_lr():
    """tau = L_k / R_load."""
    tau = snspd_recovery_time(800.0, 50.0)  # 800 nH / 50 Ohm = 16 ns
    assert tau == pytest.approx(16.0, rel=1e-6)


def test_recovery_time_high_inductance():
    tau = snspd_recovery_time(2000.0, 50.0)  # WSi-like
    assert tau == pytest.approx(40.0, rel=1e-6)


# ---- Wavelength efficiency tests ------------------------------------------

def test_efficiency_below_cutoff():
    """Efficiency should be near peak below cutoff."""
    eta = snspd_wavelength_efficiency(1550.0, cutoff_wavelength_nm=2000.0)
    assert eta > 0.8 * 0.93  # close to peak


def test_efficiency_above_cutoff():
    """Efficiency drops above cutoff wavelength."""
    eta_below = snspd_wavelength_efficiency(1550.0, cutoff_wavelength_nm=2000.0)
    eta_above = snspd_wavelength_efficiency(3000.0, cutoff_wavelength_nm=2000.0)
    assert eta_above < eta_below


def test_efficiency_at_cutoff():
    """At cutoff wavelength, efficiency is ~50% of peak."""
    eta = snspd_wavelength_efficiency(2000.0, peak_efficiency=1.0, cutoff_wavelength_nm=2000.0)
    assert abs(eta - 0.5) < 0.01


# ---- Timing jitter tests --------------------------------------------------

def test_jitter_at_optimal_bias():
    j = snspd_timing_jitter(0.95, jitter_at_optimal_ps=68.0)
    assert j == pytest.approx(68.0, rel=0.01)


def test_jitter_increases_at_low_bias():
    j_high = snspd_timing_jitter(0.95)
    j_low = snspd_timing_jitter(0.5)
    assert j_low > j_high


# ---- Dark count rate tests ------------------------------------------------

def test_dcr_at_operating_temp():
    dcr = snspd_dark_count_rate(1.8, dcr_at_operating=100.0, operating_temp_K=1.8)
    assert dcr == pytest.approx(100.0, rel=0.01)


def test_dcr_increases_with_temperature():
    dcr_cold = snspd_dark_count_rate(1.5, dcr_at_operating=100.0, operating_temp_K=1.8)
    dcr_warm = snspd_dark_count_rate(3.0, dcr_at_operating=100.0, operating_temp_K=1.8)
    assert dcr_warm > dcr_cold


# ---- Material presets tests -----------------------------------------------

def test_presets_exist():
    assert "NbN" in SNSPD_MATERIAL_PRESETS
    assert "WSi" in SNSPD_MATERIAL_PRESETS
    assert "MoSi" in SNSPD_MATERIAL_PRESETS


def test_presets_valid_parameters():
    for name, profile in SNSPD_MATERIAL_PRESETS.items():
        assert 0 < profile.system_detection_efficiency <= 1, f"{name}: SDE"
        assert profile.dark_count_rate_cps >= 0, f"{name}: DCR"
        assert profile.timing_jitter_ps > 0, f"{name}: jitter"
        assert profile.recovery_time_ns > 0, f"{name}: recovery"
        assert profile.operating_temp_K > 0, f"{name}: temp"
        assert profile.critical_temp_K > profile.operating_temp_K, f"{name}: Tc > T_op"


def test_nbn_preset_matches_published():
    nbn = SNSPD_MATERIAL_PRESETS["NbN"]
    assert nbn.system_detection_efficiency == pytest.approx(0.93, abs=0.01)
    assert nbn.timing_jitter_ps == pytest.approx(68.0, abs=5.0)
