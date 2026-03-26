"""Tests for underwater QKD channel models."""

from __future__ import annotations

import math

import pytest

from photonstrust.channels.underwater import (
    beer_lambert_transmission,
    jerlov_water_coefficients,
    optimal_wavelength,
    underwater_channel,
)


# ---- Beer-Lambert tests ---------------------------------------------------

def test_beer_lambert_zero_distance():
    T = beer_lambert_transmission(0.0, 0.1)
    assert T == pytest.approx(1.0, rel=1e-6)


def test_beer_lambert_formula():
    """T = exp(-c * d)."""
    c = 0.05  # m^-1
    d = 10.0  # m
    T = beer_lambert_transmission(d, c)
    assert T == pytest.approx(math.exp(-0.5), rel=1e-6)


def test_beer_lambert_decreases_with_distance():
    T1 = beer_lambert_transmission(10.0, 0.1)
    T2 = beer_lambert_transmission(100.0, 0.1)
    assert T1 > T2


def test_beer_lambert_higher_attenuation():
    T_clear = beer_lambert_transmission(10.0, 0.05)
    T_turbid = beer_lambert_transmission(10.0, 0.5)
    assert T_clear > T_turbid


# ---- Jerlov water type tests ----------------------------------------------

def test_jerlov_type_i_clearest():
    """Type I should have lowest attenuation at blue-green."""
    a_I, b_I = jerlov_water_coefficients("I", 470.0)
    a_III, b_III = jerlov_water_coefficients("III", 470.0)
    assert (a_I + b_I) < (a_III + b_III)


def test_jerlov_coastal_more_turbid():
    """Coastal waters (3C) more attenuating than open ocean (IB)."""
    a_ib, b_ib = jerlov_water_coefficients("IB", 520.0)
    a_3c, b_3c = jerlov_water_coefficients("3C", 520.0)
    assert (a_3c + b_3c) > (a_ib + b_ib) * 5  # much higher


def test_jerlov_positive_coefficients():
    for wt in ["I", "IA", "IB", "II", "III", "1C", "3C"]:
        a, b = jerlov_water_coefficients(wt, 520.0)
        assert a > 0, f"{wt}: absorption"
        assert b > 0, f"{wt}: scattering"


def test_jerlov_absorption_dominates():
    """In clear ocean, absorption > scattering."""
    a, b = jerlov_water_coefficients("I", 520.0)
    assert a > b


def test_jerlov_interpolation():
    """Interpolated value between tabulated wavelengths."""
    a, b = jerlov_water_coefficients("I", 485.0)  # between 470 and 500
    a_470, b_470 = jerlov_water_coefficients("I", 470)
    a_500, b_500 = jerlov_water_coefficients("I", 500)
    # Should be between the two endpoints
    assert min(a_470, a_500) <= a <= max(a_470, a_500)


def test_jerlov_alias_normalization():
    """Aliases like '1' -> 'I' should work."""
    a1, b1 = jerlov_water_coefficients("1", 520.0)
    a2, b2 = jerlov_water_coefficients("I", 520.0)
    assert a1 == a2 and b1 == b2


# ---- Underwater channel tests ---------------------------------------------

def test_channel_short_distance():
    r = underwater_channel(10.0, wavelength_nm=520.0, water_type="I")
    assert r.transmission > 0.5  # 10m in clear ocean should be OK


def test_channel_long_distance_low_transmission():
    r = underwater_channel(200.0, wavelength_nm=520.0, water_type="IB")
    assert r.transmission < 0.01  # very low at 200m


def test_channel_loss_db_positive():
    r = underwater_channel(50.0)
    assert r.loss_db > 0


def test_channel_max_qkd_distance():
    r = underwater_channel(10.0, water_type="I")
    assert r.max_qkd_distance_m > 0
    assert r.max_qkd_distance_m < 1000  # underwater QKD limited


def test_channel_wavelength_matters():
    """Blue-green (520nm) should be better than red (700nm) underwater."""
    r_green = underwater_channel(50.0, wavelength_nm=520.0, water_type="I")
    r_red = underwater_channel(50.0, wavelength_nm=700.0, water_type="I")
    assert r_green.transmission > r_red.transmission


def test_channel_water_type_matters():
    r_clear = underwater_channel(50.0, water_type="I")
    r_turbid = underwater_channel(50.0, water_type="3C")
    assert r_clear.transmission > r_turbid.transmission


# ---- Optimal wavelength tests ---------------------------------------------

def test_optimal_wavelength_open_ocean():
    """Open ocean optimal wavelength should be blue-green (450-520 nm)."""
    wl = optimal_wavelength("I")
    assert 400 <= wl <= 520


def test_optimal_wavelength_coastal():
    """Coastal waters shift optimal wavelength toward green."""
    wl_ocean = optimal_wavelength("I")
    wl_coast = optimal_wavelength("3C")
    # Coastal tends to be greener due to CDOM absorption of blue
    assert wl_coast >= wl_ocean


def test_optimal_wavelength_valid():
    for wt in ["I", "IB", "III", "3C"]:
        wl = optimal_wavelength(wt)
        assert 400 <= wl <= 700
