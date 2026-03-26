"""Tests for InGaAs APD detector models."""

from __future__ import annotations

import math

import pytest

from photonstrust.physics.detector_ingaas import (
    INGAAS_APD_PRESETS,
    K_B_EV,
    ingaas_afterpulse_probability,
    ingaas_dcr_temperature,
    ingaas_efficiency_vs_bias,
    ingaas_gated_detection,
)


# ---- Afterpulse tests -----------------------------------------------------

def test_afterpulse_at_zero_holdoff():
    """At t=0, afterpulse probability equals P_AP0."""
    p = ingaas_afterpulse_probability(0.0, p_ap0=0.05)
    assert p == pytest.approx(0.05, rel=1e-6)


def test_afterpulse_decays_with_holdoff():
    p1 = ingaas_afterpulse_probability(5.0, p_ap0=0.05, trap_lifetime_us=5.0)
    p2 = ingaas_afterpulse_probability(20.0, p_ap0=0.05, trap_lifetime_us=5.0)
    assert p1 > p2


def test_afterpulse_exponential_formula():
    """p_AP = P_AP0 * exp(-t/tau)."""
    t = 10.0
    tau = 5.0
    p0 = 0.05
    expected = p0 * math.exp(-t / tau)
    p = ingaas_afterpulse_probability(t, p_ap0=p0, trap_lifetime_us=tau)
    assert p == pytest.approx(expected, rel=1e-6)


def test_afterpulse_long_holdoff_negligible():
    """Very long hold-off should reduce afterpulse to near zero."""
    p = ingaas_afterpulse_probability(100.0, p_ap0=0.1, trap_lifetime_us=5.0)
    assert p < 1e-6


# ---- DCR temperature tests ------------------------------------------------

def test_dcr_at_reference_temperature():
    """DCR at reference temp should equal reference value."""
    dcr = ingaas_dcr_temperature(223.0, dcr_ref=2000.0, temp_ref_K=223.0)
    assert dcr == pytest.approx(2000.0, rel=1e-4)


def test_dcr_increases_with_temperature():
    dcr_cold = ingaas_dcr_temperature(200.0, dcr_ref=2000.0, temp_ref_K=223.0)
    dcr_hot = ingaas_dcr_temperature(250.0, dcr_ref=2000.0, temp_ref_K=223.0)
    assert dcr_hot > dcr_cold


def test_dcr_arrhenius_scaling():
    """Verify Arrhenius formula: DCR(T) = DCR_ref * exp(E_a/k_B * (1/T_ref - 1/T))."""
    T = 250.0
    T_ref = 223.0
    E_a = 0.22
    dcr_ref = 2000.0
    expected = dcr_ref * math.exp((E_a / K_B_EV) * (1.0 / T_ref - 1.0 / T))
    dcr = ingaas_dcr_temperature(T, dcr_ref=dcr_ref, temp_ref_K=T_ref, activation_energy_eV=E_a)
    assert dcr == pytest.approx(expected, rel=1e-4)


def test_dcr_cooling_reduces_noise():
    """Cooling detector reduces dark counts."""
    dcr_warm = ingaas_dcr_temperature(273.0)  # 0 C
    dcr_cold = ingaas_dcr_temperature(193.0)  # -80 C
    assert dcr_cold < dcr_warm


# ---- Efficiency vs bias tests ---------------------------------------------

def test_efficiency_zero_bias():
    """Zero excess bias should give zero efficiency."""
    eta = ingaas_efficiency_vs_bias(0.0)
    assert eta == pytest.approx(0.0, abs=1e-6)


def test_efficiency_increases_with_bias():
    eta1 = ingaas_efficiency_vs_bias(1.0)
    eta2 = ingaas_efficiency_vs_bias(3.0)
    assert eta2 > eta1


def test_efficiency_saturates():
    """High bias should approach eta_max."""
    eta = ingaas_efficiency_vs_bias(20.0, eta_max=0.30)
    assert eta > 0.29


# ---- Gated detection tests ------------------------------------------------

def test_gated_signal_click():
    """Signal with mu=1, eta=0.25 should give p_click ~ 22%."""
    r = ingaas_gated_detection(
        1.0, detection_efficiency=0.25,
        dark_count_rate_cps=0.0, afterpulse_probability=0.0,
    )
    expected = 1.0 - math.exp(-1.0 * 0.25)
    assert r.p_click == pytest.approx(expected, rel=1e-4)


def test_gated_dark_count():
    r = ingaas_gated_detection(
        0.0, detection_efficiency=0.25,
        dark_count_rate_cps=1000.0, gate_width_ns=2.5,
        afterpulse_probability=0.0,
    )
    expected_dark = 1000.0 * 2.5e-9
    assert r.p_dark == pytest.approx(expected_dark, rel=0.01)
    assert r.p_click == pytest.approx(0.0, abs=1e-10)


def test_gated_total_click():
    """Total click should combine signal, dark, and afterpulse."""
    r = ingaas_gated_detection(
        0.5, detection_efficiency=0.25,
        dark_count_rate_cps=2000.0, gate_width_ns=2.5,
        afterpulse_probability=0.05, hold_off_us=10.0,
    )
    assert r.p_total_click > r.p_click
    assert 0 < r.p_total_click < 1


def test_gated_qber_contribution():
    """QBER from noise should be ~ 0.5 * noise / total."""
    r = ingaas_gated_detection(
        0.0, detection_efficiency=0.25,
        dark_count_rate_cps=1e6, gate_width_ns=2.5,
        afterpulse_probability=0.0,
    )
    # No signal, only dark counts: QBER = 0.5
    assert r.qber_contribution == pytest.approx(0.5, abs=0.01)


def test_gated_max_rate_holdoff():
    """Max rate limited by hold-off."""
    r = ingaas_gated_detection(0.5, hold_off_us=10.0)
    assert r.max_rate_cps == pytest.approx(1.0 / 10e-6, rel=1e-6)  # 100 kHz


# ---- Presets tests --------------------------------------------------------

def test_presets_exist():
    assert "id230" in INGAAS_APD_PRESETS
    assert "id210" in INGAAS_APD_PRESETS
    assert "high_rate_spad" in INGAAS_APD_PRESETS


def test_presets_valid():
    for name, profile in INGAAS_APD_PRESETS.items():
        assert 0 < profile.detection_efficiency <= 1, f"{name}: DE"
        assert profile.dark_count_rate_cps >= 0, f"{name}: DCR"
        assert profile.operating_temp_K > 0, f"{name}: temp"
        assert profile.gate_width_ns > 0, f"{name}: gate width"
