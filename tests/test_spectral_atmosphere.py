"""Tests for spectral atmosphere models."""

from __future__ import annotations

import math

import pytest

from photonstrust.channels.spectral_atmosphere import (
    atmospheric_transmission,
    mie_scattering_coefficient,
    molecular_absorption_coefficient,
    qkd_window_comparison,
    rayleigh_scattering_coefficient,
)


# ---- Rayleigh scattering tests --------------------------------------------

def test_rayleigh_lambda_4_scaling():
    """Rayleigh scattering scales as lambda^-4."""
    a1 = rayleigh_scattering_coefficient(500.0)
    a2 = rayleigh_scattering_coefficient(1000.0)
    ratio = a1 / a2
    expected = (1000.0 / 500.0) ** 4  # = 16
    assert ratio == pytest.approx(expected, rel=0.01)


def test_rayleigh_shorter_wavelength_more_scattering():
    a_blue = rayleigh_scattering_coefficient(450.0)
    a_red = rayleigh_scattering_coefficient(700.0)
    a_ir = rayleigh_scattering_coefficient(1550.0)
    assert a_blue > a_red > a_ir


def test_rayleigh_positive():
    a = rayleigh_scattering_coefficient(550.0)
    assert a > 0


def test_rayleigh_density_correction():
    """Lower pressure = less scattering."""
    a_sealevel = rayleigh_scattering_coefficient(550.0, pressure_hPa=1013.25)
    a_altitude = rayleigh_scattering_coefficient(550.0, pressure_hPa=500.0)
    assert a_altitude < a_sealevel


# ---- Mie scattering tests -------------------------------------------------

def test_mie_clear_vs_hazy():
    """Lower visibility = more Mie scattering."""
    a_clear = mie_scattering_coefficient(550.0, visibility_km=23.0)
    a_hazy = mie_scattering_coefficient(550.0, visibility_km=5.0)
    assert a_hazy > a_clear


def test_mie_formula_clear():
    """At V=23 km, alpha_M = 3.912/23 * (lambda/550)^(-1.3) at 550nm."""
    a = mie_scattering_coefficient(550.0, visibility_km=23.0)
    expected = 3.912 / 23.0  # at 550nm, (550/550)^(-q) = 1
    assert a == pytest.approx(expected, rel=0.01)


def test_mie_wavelength_dependence():
    """Mie scattering is stronger at shorter wavelengths."""
    a_blue = mie_scattering_coefficient(450.0, visibility_km=23.0)
    a_ir = mie_scattering_coefficient(1550.0, visibility_km=23.0)
    assert a_blue > a_ir


def test_mie_fog():
    """Fog (V < 1 km) should give high attenuation."""
    a = mie_scattering_coefficient(550.0, visibility_km=0.5)
    assert a > 5.0  # > 5 km^-1


# ---- Molecular absorption tests -------------------------------------------

def test_molecular_1550_low_absorption():
    """1550 nm is in a transmission window (low absorption)."""
    a = molecular_absorption_coefficient(1550.0)
    assert a < 0.1  # very low


def test_molecular_1380_high_absorption():
    """1380 nm is in a strong water absorption band."""
    a = molecular_absorption_coefficient(1380.0, humidity_relative=0.8)
    assert a > 1.0


def test_molecular_humidity_scaling():
    """Higher humidity increases water band absorption."""
    a_dry = molecular_absorption_coefficient(940.0, humidity_relative=0.1)
    a_wet = molecular_absorption_coefficient(940.0, humidity_relative=0.9)
    assert a_wet > a_dry


# ---- Total transmission tests ----------------------------------------------

def test_transmission_zero_distance():
    r = atmospheric_transmission(550.0, 0.0)
    assert r.transmission == pytest.approx(1.0, rel=1e-6)


def test_transmission_decreases_with_distance():
    r1 = atmospheric_transmission(550.0, 1.0)
    r10 = atmospheric_transmission(550.0, 10.0)
    assert r1.transmission > r10.transmission


def test_transmission_components_multiply():
    """Total = Rayleigh * Mie * Molecular."""
    r = atmospheric_transmission(550.0, 5.0)
    product = r.transmission_rayleigh * r.transmission_mie * r.transmission_molecular
    assert r.transmission == pytest.approx(product, rel=1e-6)


def test_transmission_ir_better_than_visible():
    """1550 nm should have better transmission than 550 nm."""
    r_vis = atmospheric_transmission(550.0, 10.0)
    r_ir = atmospheric_transmission(1550.0, 10.0)
    assert r_ir.transmission > r_vis.transmission


def test_transmission_diagnostics():
    r = atmospheric_transmission(780.0, 5.0, visibility_km=10.0)
    assert r.diagnostics["visibility_km"] == 10.0
    assert r.extinction_coefficient_per_km > 0
    assert r.optical_depth > 0


# ---- QKD window comparison tests ------------------------------------------

def test_qkd_windows():
    windows = qkd_window_comparison(1.0, 23.0)
    assert "780nm" in windows
    assert "850nm" in windows
    assert "1310nm" in windows
    assert "1550nm" in windows
    # All should have positive transmission at 1 km
    for name, r in windows.items():
        assert r.transmission > 0.5, f"{name}: transmission too low"
