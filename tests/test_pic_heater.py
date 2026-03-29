"""Tests for the thermo-optic heater component model."""

from __future__ import annotations

import math

import pytest

from photonstrust.components.pic.heater import (
    heater_forward_matrix,
    heater_P_pi,
    heater_phase_shift,
    heater_thermal_bandwidth,
    heater_thermal_crosstalk,
)


def test_heater_pi_shift():
    """At P_pi power the accumulated phase must equal pi."""
    length_um = 200.0
    R_th = 0.5  # K/mW
    P_pi = heater_P_pi(length_um, thermal_resistance_K_per_mW=R_th)
    delta_T = P_pi * R_th
    phi = heater_phase_shift(delta_T, length_um)
    assert phi == pytest.approx(math.pi, rel=1e-10)


def test_heater_phase_proportional_to_length():
    """Phase shift scales linearly with heater length."""
    delta_T = 10.0
    phi1 = heater_phase_shift(delta_T, length_um=100.0)
    phi2 = heater_phase_shift(delta_T, length_um=200.0)
    assert phi2 == pytest.approx(2.0 * phi1, rel=1e-12)


def test_heater_phase_proportional_to_delta_T():
    """Phase shift scales linearly with temperature change."""
    length_um = 150.0
    phi1 = heater_phase_shift(5.0, length_um)
    phi2 = heater_phase_shift(15.0, length_um)
    assert phi2 == pytest.approx(3.0 * phi1, rel=1e-12)


def test_heater_si_vs_sin_efficiency():
    """Si needs less power than SiN for a pi shift (higher dn/dT)."""
    length_um = 200.0
    P_pi_si = heater_P_pi(length_um, material="Si")
    P_pi_sin = heater_P_pi(length_um, material="SiN")
    assert P_pi_si < P_pi_sin


def test_heater_thermal_crosstalk_decays():
    """Neighbour temperature decreases with distance."""
    delta_T = 50.0
    t1 = heater_thermal_crosstalk(delta_T, distance_um=20.0)
    t2 = heater_thermal_crosstalk(delta_T, distance_um=80.0)
    assert t1 > t2 > 0.0


def test_heater_thermal_bandwidth():
    """Thermal bandwidth is positive and in the kHz range."""
    bw = heater_thermal_bandwidth()
    assert bw > 0.0
    # Typical MEMS/heater bandwidths are 1-1000 kHz
    assert 0.1 < bw < 10_000.0


def test_heater_P_pi_typical_range():
    """P_pi for SOI heaters (L=100-300 um) should be in a physically sensible range."""
    for L in (100.0, 200.0, 300.0):
        P = heater_P_pi(L, thermal_resistance_K_per_mW=0.5, material="Si")
        assert 10.0 < P < 100.0, f"P_pi={P:.1f} mW outside expected range for L={L} um"
