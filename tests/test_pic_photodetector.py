"""Tests for the Ge-on-Si waveguide photodetector component models."""

from __future__ import annotations

import math

import pytest

from photonstrust.components.pic.photodetector import (
    PhotodetectorResult,
    ge_bandwidth,
    ge_dark_current,
    ge_dark_current_temperature,
    ge_nep,
    ge_responsivity,
    photodetector_forward_matrix,
    photodetector_response,
    photodetector_scattering_matrix,
)


# ---------------------------------------------------------------------------
# Responsivity
# ---------------------------------------------------------------------------


def test_responsivity_at_1550nm():
    """Responsivity at 1550 nm should be in the 0.8-1.2 A/W range."""
    R = ge_responsivity(1550.0)
    assert 0.8 <= R <= 1.2


def test_responsivity_scales_with_length():
    """Longer absorber should yield higher responsivity (up to saturation)."""
    R_short = ge_responsivity(1550.0, length_um=10.0)
    R_long = ge_responsivity(1550.0, length_um=40.0)
    assert R_long > R_short


# ---------------------------------------------------------------------------
# Dark current
# ---------------------------------------------------------------------------


def test_dark_current_scales_with_area():
    """Larger photodetector area should produce higher dark current."""
    I_small = ge_dark_current(width_um=5.0, length_um=10.0)
    I_large = ge_dark_current(width_um=10.0, length_um=20.0)
    assert I_large > I_small


def test_dark_current_temperature():
    """Dark current should increase with temperature."""
    I_ref = 10.0  # nA at 300 K
    I_350 = ge_dark_current_temperature(I_ref, T_K=350.0)
    assert I_350 > I_ref


# ---------------------------------------------------------------------------
# Bandwidth
# ---------------------------------------------------------------------------


def test_bandwidth_transit_and_rc():
    """Combined bandwidth should be less than min(f_tr, f_RC)."""
    # Compute f_tr and f_RC independently
    from photonstrust.components.pic.photodetector import V_SAT_GE, EPSILON_GE

    w_i = 0.5e-6  # m
    area = 100e-12  # m^2
    R_s, R_l = 10.0, 50.0
    C_par = 10e-15  # F

    f_tr = 0.45 * V_SAT_GE / w_i
    C_j = EPSILON_GE * area / w_i
    f_RC = 1.0 / (2.0 * math.pi * (R_s + R_l) * (C_j + C_par))

    f_combined = ge_bandwidth(
        depletion_width_um=0.5,
        area_um2=100.0,
        R_series_ohm=10.0,
        R_load_ohm=50.0,
        C_parasitic_fF=10.0,
    )
    f_combined_Hz = f_combined * 1e9  # GHz -> Hz
    assert f_combined_Hz < min(f_tr, f_RC)


# ---------------------------------------------------------------------------
# NEP
# ---------------------------------------------------------------------------


def test_nep_positive():
    """NEP should be positive for non-zero dark current."""
    nep = ge_nep(dark_current_A=1e-9, responsivity_A_per_W=1.0)
    assert nep > 0


# ---------------------------------------------------------------------------
# Aggregate response
# ---------------------------------------------------------------------------


def test_photodetector_result():
    """All fields of PhotodetectorResult should be populated with physical values."""
    result = photodetector_response({"wavelength_nm": 1550.0})
    assert result.responsivity_A_per_W > 0
    assert result.dark_current_nA > 0
    assert result.bandwidth_3dB_GHz > 0
    assert result.nep_W_per_rtHz > 0
    assert 0 < result.quantum_efficiency <= 1.0


# ---------------------------------------------------------------------------
# Matrix models
# ---------------------------------------------------------------------------


def test_photodetector_forward_matrix_shape():
    """Forward matrix should be (1, 1)."""
    m = photodetector_forward_matrix({})
    assert m.shape == (1, 1)


def test_photodetector_scattering_matrix_shape():
    """Scattering matrix should be (2, 2)."""
    s = photodetector_scattering_matrix({})
    assert s.shape == (2, 2)
