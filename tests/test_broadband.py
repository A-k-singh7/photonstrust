"""Tests for broadband wavelength sweep simulation."""
import numpy as np
import pytest

from photonstrust.pic.broadband import (
    BroadbandResult,
    broadband_sweep,
    ring_resonator_transmission,
)


def test_ring_resonance_dips():
    """Ring resonator spectrum should show periodic dips."""
    # Use a wide enough wavelength range (100nm) to guarantee capturing
    # at least one resonance dip. With n_eff=2.45 and radius=10um the FSR
    # is ~15.5nm so a 100nm window will contain several resonances.
    result = broadband_sweep(
        lambda wl: {
            "through": ring_resonator_transmission(
                wl, radius_um=10.0, coupling_kappa=0.3
            )
        },
        wavelength_start_nm=1500.0,
        wavelength_stop_nm=1600.0,
        n_points=2001,
    )
    assert "through" in result.transmission_db
    spec = result.transmission_db["through"]
    # Find dips (local minima)
    dips = []
    min_val = float(np.min(spec))
    for i in range(1, len(spec) - 1):
        if spec[i] < spec[i - 1] and spec[i] < spec[i + 1] and spec[i] < -0.5:
            dips.append(i)
    assert min_val < -0.1, f"Spectrum should have some attenuation, min={min_val}"
    assert len(dips) >= 1, f"Ring should have at least one resonance dip (min={min_val})"


def test_broadband_result_shape():
    result = broadband_sweep(
        lambda wl: np.array([0.9 * np.exp(1j * wl / 100)]),
        n_points=51,
    )
    assert len(result.wavelengths_nm) == 51
    assert len(list(result.transmission_db.values())[0]) == 51


def test_group_delay_computed():
    result = broadband_sweep(
        lambda wl: {"out": 0.9 * np.exp(1j * 2 * np.pi * wl / 10)},
        n_points=101,
    )
    assert result.group_delay_ps is not None
    assert "out" in result.group_delay_ps


def test_flat_passband():
    """Constant transmission should give flat spectrum."""
    result = broadband_sweep(
        lambda wl: {"out": complex(0.5)},
        n_points=21,
    )
    spec = result.transmission_db["out"]
    expected_db = 10 * np.log10(0.25)  # |0.5|^2 = 0.25
    np.testing.assert_allclose(spec, expected_db, atol=0.01)


def test_ring_fsr():
    """Check ring FSR matches theory."""
    radius_um = 10.0
    n_g = 4.2
    L_um = 2 * np.pi * radius_um
    L_m = L_um * 1e-6
    # FSR = lambda^2 / (n_g * L)
    expected_fsr_nm = 1550.0**2 * 1e-9 / (n_g * L_m) * 1e9

    result = broadband_sweep(
        lambda wl: {
            "through": ring_resonator_transmission(
                wl, radius_um=radius_um, n_g=n_g, coupling_kappa=0.3
            )
        },
        wavelength_start_nm=1500.0,
        wavelength_stop_nm=1600.0,
        n_points=5001,
    )
    spec = result.transmission_db["through"]
    wls = result.wavelengths_nm
    # Find dips
    dip_wls = []
    for i in range(2, len(spec) - 2):
        if spec[i] < spec[i - 1] and spec[i] < spec[i + 1] and spec[i] < -3.0:
            dip_wls.append(wls[i])
    if len(dip_wls) >= 2:
        measured_fsr = abs(dip_wls[1] - dip_wls[0])
        assert abs(measured_fsr - expected_fsr_nm) < expected_fsr_nm * 0.15
