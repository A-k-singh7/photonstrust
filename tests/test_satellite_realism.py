from __future__ import annotations

from photonstrust.satellite.pass_budget import (
    compute_pass_key_budget,
    enforce_finite_key_for_pass,
    gamma_gamma_params_from_rytov,
    sample_gamma_gamma,
)
from photonstrust.satellite.background import estimate_background_counts_cps
from photonstrust.satellite.extinction import (
    get_atmosphere_profiles,
    lookup_extinction_db_per_km,
)
from photonstrust.satellite.types import AtmosphereProfile, PassKeyBudget


# ---- Gamma-Gamma scintillation tests ----------------------------------------

def test_gamma_gamma_params_from_rytov_weak():
    params = gamma_gamma_params_from_rytov(0.1)
    assert params.alpha > 10
    assert params.beta > 10
    assert params.regime == "weak"


def test_gamma_gamma_params_from_rytov_strong():
    params = gamma_gamma_params_from_rytov(5.0)
    assert params.alpha < 10  # smaller than weak-turbulence alpha (>10)
    assert params.beta < 2    # small-scale saturates first
    assert params.regime == "strong"


def test_gamma_gamma_samples_mean_near_unity():
    params = gamma_gamma_params_from_rytov(1.0)
    samples = sample_gamma_gamma(params.alpha, params.beta, 10000, seed=42)
    mean = float(samples.mean())
    assert abs(mean - 1.0) < 0.05, f"Mean {mean} not within 5% of 1.0"


def test_gamma_gamma_outage_increases_with_rytov():
    threshold = 0.3
    params_weak = gamma_gamma_params_from_rytov(0.1)
    params_strong = gamma_gamma_params_from_rytov(5.0)
    samples_weak = sample_gamma_gamma(
        params_weak.alpha, params_weak.beta, 10000, seed=99
    )
    samples_strong = sample_gamma_gamma(
        params_strong.alpha, params_strong.beta, 10000, seed=99
    )
    outage_weak = float((samples_weak < threshold).mean())
    outage_strong = float((samples_strong < threshold).mean())
    assert outage_strong > outage_weak


# ---- Background estimation tests -------------------------------------------

def test_background_day_vs_night():
    common = dict(
        wavelength_nm=810.0,
        fov_urad=100.0,
        rx_aperture_m=0.3,
        filter_bandwidth_nm=1.0,
        detector_efficiency=0.5,
    )
    day = estimate_background_counts_cps(day_night="day", **common)
    night = estimate_background_counts_cps(day_night="night", **common)
    assert day.counts_cps > 100 * night.counts_cps


def test_background_estimate_physics_units():
    est = estimate_background_counts_cps(
        wavelength_nm=1550.0,
        day_night="night",
        fov_urad=50.0,
        rx_aperture_m=0.2,
        filter_bandwidth_nm=0.5,
        detector_efficiency=0.3,
    )
    assert est.counts_cps > 0
    assert est.spectral_radiance_w_m2_sr_nm > 0
    assert est.fov_sr > 0
    assert est.rx_area_m2 > 0
    assert est.photon_energy_j > 0


# ---- Extinction lookup tests ------------------------------------------------

def test_extinction_lookup_known_wavelengths():
    p1550 = lookup_extinction_db_per_km(1550.0)
    p785 = lookup_extinction_db_per_km(785.0)
    assert abs(p1550.extinction_db_per_km - 0.015) < 1e-9
    assert abs(p785.extinction_db_per_km - 0.07) < 1e-9


def test_extinction_lookup_interpolation():
    # 800 nm is between 785 (0.07) and 810 (0.06)
    profile = lookup_extinction_db_per_km(800.0)
    assert 0.06 < profile.extinction_db_per_km < 0.07


# ---- Pass key budget tests --------------------------------------------------

def test_pass_key_accumulation_monotonic():
    rates = [100.0, 200.0, 150.0, 300.0, 50.0]
    times = [0.0, 1.0, 2.0, 3.0, 4.0]
    budget = compute_pass_key_budget(
        time_steps_s=times, key_rates_bps=rates, dt_s=1.0
    )
    for i in range(1, len(budget.cumulative_key_bits)):
        assert budget.cumulative_key_bits[i] >= budget.cumulative_key_bits[i - 1]


def test_finite_key_enforced_for_orbit_pass():
    result = enforce_finite_key_for_pass(scenario_kind="orbit_pass")
    assert result["enforced"] is True


def test_finite_key_not_enforced_for_fiber():
    result = enforce_finite_key_for_pass(
        scenario_kind="fiber", pass_duration_s=3600.0
    )
    assert result["enforced"] is False


# ---- Serialization tests ----------------------------------------------------

def test_pass_budget_serialization():
    budget = compute_pass_key_budget(
        time_steps_s=[0.0, 1.0, 2.0],
        key_rates_bps=[100.0, 200.0, 300.0],
        dt_s=1.0,
    )
    d = budget.as_dict()
    assert isinstance(d, dict)
    assert "total_key_bits" in d
    assert d["total_key_bits"] == budget.total_key_bits
    assert isinstance(d["cumulative_key_bits"], list)


def test_atmosphere_profile_serialization():
    profile = lookup_extinction_db_per_km(850.0)
    d = profile.as_dict()
    assert isinstance(d, dict)
    assert "wavelength_nm" in d
    assert d["wavelength_nm"] == 850.0
    assert d["extinction_db_per_km"] == 0.05
    assert d["condition"] == "clear"
