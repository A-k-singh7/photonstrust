"""Tests for the arrayed waveguide grating (AWG) component models."""

from __future__ import annotations

import math

import pytest

from photonstrust.components.pic.awg import (
    AWGResult,
    awg_adjacent_crosstalk_db,
    awg_background_crosstalk_db,
    awg_channel_response,
    awg_channel_spacing,
    awg_diffraction_order,
    awg_forward_matrix,
    awg_fsr,
    awg_gaussian_passband,
    awg_insertion_loss_db,
    awg_scattering_matrix,
)


# ---------------------------------------------------------------------------
# FSR
# ---------------------------------------------------------------------------


def test_awg_fsr_formula():
    """FSR should match lambda^2 / (n_g * delta_L) with consistent units."""
    lam_nm = 1550.0
    n_g = 4.2
    dL_um = 50.0
    dL_nm = dL_um * 1e3  # um -> nm

    expected = lam_nm ** 2 / (n_g * dL_nm)
    result = awg_fsr(lam_nm, n_g, dL_um)
    assert result == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Diffraction order
# ---------------------------------------------------------------------------


def test_awg_diffraction_order():
    """Diffraction order should be a positive integer."""
    m = awg_diffraction_order(1550.0, 2.44, 50.0)
    assert m > 0
    assert isinstance(m, int)


# ---------------------------------------------------------------------------
# Channel spacing
# ---------------------------------------------------------------------------


def test_awg_channel_spacing():
    """Channel spacing = FSR / N_ch."""
    fsr = 12.8
    n_ch = 8
    spacing = awg_channel_spacing(fsr, n_ch)
    assert spacing == pytest.approx(fsr / n_ch, rel=1e-10)


# ---------------------------------------------------------------------------
# Gaussian passband
# ---------------------------------------------------------------------------


def test_awg_gaussian_passband_peak():
    """Peak transmission at channel center should equal peak_transmission."""
    T = awg_gaussian_passband(1550.0, 1550.0, 0.5, peak_transmission=0.9)
    assert T == pytest.approx(0.9, rel=1e-10)


def test_awg_gaussian_passband_3dB():
    """At +/- passband_3dB/2 from center, transmission should be half of peak."""
    pb = 0.5  # nm
    center = 1550.0
    T_half = awg_gaussian_passband(center + pb / 2.0, center, pb, peak_transmission=1.0)
    assert T_half == pytest.approx(0.5, rel=1e-6)


# ---------------------------------------------------------------------------
# Crosstalk
# ---------------------------------------------------------------------------


def test_awg_adjacent_crosstalk():
    """Adjacent-channel crosstalk should be < -20 dB for typical parameters."""
    xt = awg_adjacent_crosstalk_db(channel_spacing_nm=1.6, passband_3dB_nm=0.5)
    assert xt < -20.0


def test_awg_background_crosstalk():
    """Background crosstalk should be negative and worsen with more WGs."""
    xt_20 = awg_background_crosstalk_db(20, phase_error_rms_rad=0.05)
    xt_60 = awg_background_crosstalk_db(60, phase_error_rms_rad=0.05)
    # Both should be negative (crosstalk is below signal level)
    assert xt_20 < 0
    assert xt_60 < 0
    # More waveguides with same phase error -> more scattered power -> worse XT
    # (less negative = closer to 0 = worse crosstalk)
    assert xt_60 > xt_20


# ---------------------------------------------------------------------------
# Insertion loss
# ---------------------------------------------------------------------------


def test_awg_insertion_loss():
    """IL should be in expected range 1.5-4 dB for typical parameters."""
    il = awg_insertion_loss_db(
        propagation_loss_db_per_cm=2.0,
        avg_path_length_cm=0.5,
        fpr_loss_db=0.5,
        coupling_loss_db=0.3,
    )
    # IL = 2*0.5 + 2.0*0.5 + 0.3 = 2.3
    assert 1.5 <= il <= 4.0


# ---------------------------------------------------------------------------
# Aggregate response
# ---------------------------------------------------------------------------


def test_awg_channel_response_fields():
    """AWGResult should have all fields populated with physical values."""
    result = awg_channel_response({
        "n_channels": 8,
        "center_wavelength_nm": 1550.0,
        "channel_spacing_nm": 1.6,
    })
    assert result.n_channels == 8
    assert result.fsr_nm > 0
    assert result.diffraction_order > 0
    assert result.adjacent_crosstalk_db < 0


# ---------------------------------------------------------------------------
# Matrix models
# ---------------------------------------------------------------------------


def test_awg_forward_matrix_shape():
    """Forward matrix should be (N_ch, 1)."""
    m = awg_forward_matrix({"n_channels": 8}, wavelength_nm=1550.0)
    assert m.shape == (8, 1)


def test_awg_scattering_matrix_shape():
    """Scattering matrix should be (N_ch+1, N_ch+1)."""
    s = awg_scattering_matrix({"n_channels": 8}, wavelength_nm=1550.0)
    assert s.shape == (9, 9)
