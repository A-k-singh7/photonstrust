from __future__ import annotations

import pytest

from photonstrust.physics.emitter import get_emitter_stats
from photonstrust.qkd import compute_point


def _base_source() -> dict:
    return {
        "type": "emitter_cavity",
        "physics_backend": "analytic",
        "seed": 123,
        "radiative_lifetime_ns": 1.0,
        "purcell_factor": 5.0,
        "dephasing_rate_per_ns": 0.5,
        "drive_strength": 0.05,
        "pulse_window_ns": 5.0,
        "g2_0": 0.02,
    }


def _base_scenario() -> dict:
    return {
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "physics_backend": "analytic",
            "pulse_window_ns": 5.0,
        },
        "channel": {
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"sifting_factor": 0.5, "ec_efficiency": 1.16},
    }


def test_emitter_analytic_is_deterministic_with_fixed_seed():
    source = _base_source()
    stats_a = get_emitter_stats(source)
    stats_b = get_emitter_stats(source)

    assert stats_a == stats_b
    assert stats_a["seed"] == 123
    assert stats_a["backend"] == "analytic"
    assert "diagnostics" in stats_a


def test_emitter_emission_probability_increases_with_purcell_factor():
    source_low = _base_source()
    source_high = _base_source()
    source_low["purcell_factor"] = 1.0
    source_high["purcell_factor"] = 8.0

    low = get_emitter_stats(source_low)
    high = get_emitter_stats(source_high)

    assert high["emission_prob"] > low["emission_prob"]


def test_emitter_invalid_inputs_are_stabilized_and_reported():
    source = _base_source()
    source["radiative_lifetime_ns"] = 0.0
    source["g2_0"] = 1.5
    source["pulse_window_ns"] = -10.0

    with pytest.warns(UserWarning) as warns:
        stats = get_emitter_stats(source)
    diag = stats["diagnostics"]

    assert len(warns) >= 3
    assert 0.0 <= stats["g2_0"] <= 1.0
    assert 0.0 <= stats["emission_prob"] <= 1.0
    assert diag["lifetime_ns"] > 0.0
    assert diag["pulse_window_ns"] > 0.0


def test_compute_point_does_not_mutate_source_g2(monkeypatch):
    scenario = _base_scenario()
    original_g2 = scenario["source"]["g2_0"]

    def fake_emitter_stats(_source: dict) -> dict:
        return {
            "g2_0": 0.9,
            "p_multi": 0.1,
            "emission_prob": 0.7,
            "backend": "mock",
            "diagnostics": {},
        }

    monkeypatch.setattr("photonstrust.qkd.get_emitter_stats", fake_emitter_stats)
    compute_point(scenario, distance_km=10)

    assert scenario["source"]["g2_0"] == original_g2


def test_emitter_transient_mode_reports_spectral_diagnostics():
    source = _base_source()
    source["emission_mode"] = "transient"
    source["drive_strength"] = 0.12
    stats = get_emitter_stats(source)
    diag = stats["diagnostics"]

    assert stats["emission_mode"] == "transient"
    assert diag["emission_mode"] == "transient"
    assert 0.0 <= diag["spectral_purity"] <= 1.0
    assert 0.0 <= diag["mode_overlap"] <= 1.0
    assert diag["linewidth_mhz"] >= 0.0


def test_emitter_transient_emission_increases_with_drive_strength():
    source_low = _base_source()
    source_low["emission_mode"] = "transient"
    source_low["drive_strength"] = 0.01

    source_high = _base_source()
    source_high["emission_mode"] = "transient"
    source_high["drive_strength"] = 0.20

    low = get_emitter_stats(source_low)
    high = get_emitter_stats(source_high)
    assert high["emission_prob"] >= low["emission_prob"]
