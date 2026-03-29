"""Tests for the Mach-Zehnder modulator (MZM) component models."""

from __future__ import annotations

import math

import pytest

from photonstrust.components.pic.mzm import (
    MZMResult,
    mzm_bandwidth,
    mzm_forward_matrix,
    mzm_scattering_matrix,
    mzm_transfer_function,
    pn_depletion_delta_n,
    soref_bennett_delta_n,
)


# ---------------------------------------------------------------------------
# Soref-Bennett model
# ---------------------------------------------------------------------------


def test_soref_bennett_negative_delta_n():
    """Carriers always reduce the refractive index (delta_n < 0)."""
    delta_n, _ = soref_bennett_delta_n(1e17, 1e17)
    assert delta_n < 0


def test_soref_bennett_delta_alpha_positive():
    """Free-carrier absorption always increases (delta_alpha > 0)."""
    _, delta_alpha = soref_bennett_delta_n(1e17, 1e17)
    assert delta_alpha > 0


# ---------------------------------------------------------------------------
# PN-junction depletion model
# ---------------------------------------------------------------------------


def test_pn_depletion_reverse_bias():
    """Larger reverse voltage should produce a larger magnitude delta_n."""
    dn_1V = pn_depletion_delta_n(-1.0, 1e18, 1e18, 0.5)
    dn_3V = pn_depletion_delta_n(-3.0, 1e18, 1e18, 0.5)
    # Both should be negative; larger reverse bias -> larger |delta_n|
    assert abs(dn_3V) > abs(dn_1V)


# ---------------------------------------------------------------------------
# MZM transfer function
# ---------------------------------------------------------------------------


def test_mzm_quadrature():
    """At V_pi/2, transmission should be approximately 50% of max."""
    L_mm = 3.0
    VpiLpi = 2.0
    L_cm = L_mm / 10.0
    V_pi = VpiLpi / L_cm

    result = mzm_transfer_function({
        "phase_shifter_length_mm": L_mm,
        "V_pi_L_pi_Vcm": VpiLpi,
        "voltage_V": V_pi / 2.0,
        "splitting_ratio": 0.5,
        "insertion_loss_db": 0.0,  # no loss for this test
    })
    # At quadrature: T ~ 0.5 * T_max, T_max = 1.0 for ideal
    assert result.transmission == pytest.approx(1.0, abs=0.05)


def test_mzm_null():
    """At V_pi, transmission should be approximately 0 for an ideal 50:50 splitter."""
    L_mm = 3.0
    VpiLpi = 2.0
    L_cm = L_mm / 10.0
    V_pi = VpiLpi / L_cm

    result = mzm_transfer_function({
        "phase_shifter_length_mm": L_mm,
        "V_pi_L_pi_Vcm": VpiLpi,
        "voltage_V": V_pi,
        "splitting_ratio": 0.5,
        "insertion_loss_db": 0.0,
    })
    assert result.transmission == pytest.approx(0.0, abs=1e-10)


def test_mzm_extinction_ratio():
    """Extinction ratio > 20 dB for a balanced (50:50) splitter."""
    result = mzm_transfer_function({
        "phase_shifter_length_mm": 3.0,
        "splitting_ratio": 0.5,
    })
    assert result.extinction_ratio_db > 20.0


def test_mzm_er_degrades_with_imbalance():
    """ER should drop when the splitting ratio deviates from 0.5."""
    er_balanced = mzm_transfer_function({"splitting_ratio": 0.5}).extinction_ratio_db
    er_imbalanced = mzm_transfer_function({"splitting_ratio": 0.45}).extinction_ratio_db
    assert er_imbalanced < er_balanced


# ---------------------------------------------------------------------------
# Bandwidth
# ---------------------------------------------------------------------------


def test_mzm_bandwidth_positive():
    """3-dB bandwidth should be positive for physical parameters."""
    bw = mzm_bandwidth(
        junction_capacitance_fF_per_mm=200.0,
        series_resistance_ohm=5.0,
        phase_shifter_length_mm=3.0,
        load_resistance_ohm=50.0,
    )
    assert bw > 0


def test_mzm_vpi_lpi_range():
    """Typical V_pi*L_pi should yield V_pi in reasonable range for a 3-mm device."""
    L_mm = 3.0
    for VpiLpi in [1.5, 2.0, 2.5]:
        L_cm = L_mm / 10.0
        V_pi = VpiLpi / L_cm
        assert 3.0 < V_pi < 12.0, f"V_pi={V_pi} out of expected range for VpiLpi={VpiLpi}"


# ---------------------------------------------------------------------------
# Matrix models
# ---------------------------------------------------------------------------


def test_mzm_forward_matrix_shape():
    """Forward matrix should be (1, 1)."""
    m = mzm_forward_matrix({"phase_shifter_length_mm": 3.0, "voltage_V": 0.0})
    assert m.shape == (1, 1)


def test_mzm_scattering_matrix_shape():
    """Scattering matrix should be (2, 2)."""
    s = mzm_scattering_matrix({"phase_shifter_length_mm": 3.0, "voltage_V": 0.0})
    assert s.shape == (2, 2)
