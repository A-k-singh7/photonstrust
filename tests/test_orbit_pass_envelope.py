from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from photonstrust.orbit import simulate_orbit_pass


def _base_config(samples: list[dict], cases: list[dict] | None = None) -> dict:
    orbit_pass = {"id": "test_orbit_pass", "band": "c_1550", "dt_s": 1.0, "samples": samples}
    if cases is not None:
        orbit_pass["cases"] = cases

    return {
        "orbit_pass": orbit_pass,
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
        },
        "channel": {
            "model": "free_space",
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 0.0,
            "tx_aperture_m": 0.12,
            "rx_aperture_m": 0.30,
            "beam_divergence_urad": 12.0,
            "pointing_jitter_urad": 1.5,
            "atmospheric_extinction_db_per_km": 0.02,
            "turbulence_scintillation_index": 0.12,
            "background_counts_cps": 0.0,
            "background_model": "fixed",
            "background_day_night": "night",
            "background_fov_urad": 100.0,
            "background_filter_bandwidth_nm": 1.0,
            "background_detector_gate_ns": 1.0,
            "background_site_light_pollution": 0.2,
            "elevation_deg": 45.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 100.0,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10.0, "coincidence_window_ps": 200.0},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
    }


def test_orbit_pass_elevation_improves_key_rate_all_else_equal():
    samples = [
        {"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 20.0, "background_counts_cps": 100.0},
        {"t_s": 1.0, "distance_km": 300.0, "elevation_deg": 70.0, "background_counts_cps": 100.0},
    ]
    res = simulate_orbit_pass(_base_config(samples))
    pts = res["cases"][0]["points"]
    low = pts[0]["qkd"]
    high = pts[1]["qkd"]

    assert high["loss_db"] <= low["loss_db"]
    assert high["key_rate_bps"] >= low["key_rate_bps"]


def test_orbit_pass_background_worsens_qber_and_key_rate_all_else_equal():
    samples = [
        {"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 10.0},
        {"t_s": 1.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 5000.0},
    ]
    res = simulate_orbit_pass(_base_config(samples))
    pts = res["cases"][0]["points"]
    low = pts[0]["qkd"]
    high = pts[1]["qkd"]

    assert high["qber_total"] >= low["qber_total"]
    assert high["key_rate_bps"] <= low["key_rate_bps"]


def test_orbit_pass_radiance_proxy_day_higher_than_night() -> None:
    samples = [
        {"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "day_night": "night"},
        {"t_s": 1.0, "distance_km": 300.0, "elevation_deg": 60.0, "day_night": "day"},
    ]
    cfg = _base_config(samples)
    cfg["orbit_pass"]["background_model"] = "radiance_proxy"
    cfg["channel"]["background_model"] = "radiance_proxy"
    cfg["channel"]["background_fov_urad"] = 120.0
    cfg["channel"]["background_filter_bandwidth_nm"] = 1.0
    cfg["channel"]["background_detector_gate_ns"] = 1.0
    cfg["channel"]["background_site_light_pollution"] = 0.2

    res = simulate_orbit_pass(cfg)
    pts = res["cases"][0]["points"]
    night = pts[0]
    day = pts[1]

    assert day["background_counts_cps"] > night["background_counts_cps"]
    assert day["qkd"]["key_rate_bps"] <= night["qkd"]["key_rate_bps"]
    assert day["background_uncertainty_cps"]["sigma"] >= night["background_uncertainty_cps"]["sigma"]


def test_orbit_pass_radiance_proxy_scales_with_optics() -> None:
    samples = [{"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "day_night": "day"}]
    low_cfg = _base_config(samples)
    low_cfg["orbit_pass"]["background_model"] = "radiance_proxy"
    low_cfg["channel"]["background_model"] = "radiance_proxy"
    low_cfg["channel"]["background_fov_urad"] = 80.0
    low_cfg["channel"]["background_filter_bandwidth_nm"] = 0.5

    high_cfg = _base_config(samples)
    high_cfg["orbit_pass"]["background_model"] = "radiance_proxy"
    high_cfg["channel"]["background_model"] = "radiance_proxy"
    high_cfg["channel"]["background_fov_urad"] = 160.0
    high_cfg["channel"]["background_filter_bandwidth_nm"] = 1.5

    low = simulate_orbit_pass(low_cfg)["cases"][0]["points"][0]
    high = simulate_orbit_pass(high_cfg)["cases"][0]["points"][0]

    assert high["background_counts_cps"] > low["background_counts_cps"]


def test_orbit_pass_cases_best_beats_worst_for_same_samples():
    samples = [{"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 2000.0}]
    cases = [
        {
            "id": "best",
            "label": "best",
            "channel_overrides": {
                "atmospheric_extinction_db_per_km": 0.01,
                "pointing_jitter_urad": 1.0,
                "turbulence_scintillation_index": 0.05,
                "background_counts_cps_scale": 0.3,
            },
        },
        {
            "id": "worst",
            "label": "worst",
            "channel_overrides": {
                "atmospheric_extinction_db_per_km": 0.05,
                "pointing_jitter_urad": 3.0,
                "turbulence_scintillation_index": 0.25,
                "background_counts_cps_scale": 2.0,
            },
        },
    ]

    res = simulate_orbit_pass(_base_config(samples, cases=cases))
    by_case = {c["case_id"]: c for c in res["cases"]}
    best_k = by_case["best"]["points"][0]["qkd"]["key_rate_bps"]
    worst_k = by_case["worst"]["points"][0]["qkd"]["key_rate_bps"]
    assert best_k >= worst_k


def test_orbit_pass_availability_scales_expected_total_keys_bits():
    samples = [
        {"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0},
        {"t_s": 1.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0},
    ]
    cfg = _base_config(samples)
    cfg["orbit_pass"]["availability"] = {"clear_fraction": 0.5}
    res = simulate_orbit_pass(cfg)
    s = res["cases"][0]["summary"]
    assert s["expected_total_keys_bits"] == pytest.approx(float(s["total_keys_bits"]) * 0.5)


def test_orbit_pass_results_schema_validation():
    samples = [{"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0}]
    res = simulate_orbit_pass(_base_config(samples))

    schema_path = Path("schemas") / "photonstrust.orbit_pass_results.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=res, schema=schema)


def test_orbit_pass_summary_contains_outage_fields():
    samples = [
        {"t_s": 0.0, "distance_km": 400.0, "elevation_deg": 40.0, "background_counts_cps": 100.0},
        {"t_s": 1.0, "distance_km": 500.0, "elevation_deg": 30.0, "background_counts_cps": 100.0},
    ]
    cfg = _base_config(samples)
    cfg["channel"]["pointing_model"] = "gaussian"
    cfg["channel"]["pointing_sample_count"] = 128
    cfg["channel"]["pointing_seed"] = 7
    cfg["channel"]["turbulence_model"] = "lognormal"
    cfg["channel"]["turbulence_sample_count"] = 128
    cfg["channel"]["turbulence_seed"] = 8
    res = simulate_orbit_pass(cfg)

    summary = res["cases"][0]["summary"]
    assert 0.0 <= summary["avg_channel_outage_probability"] <= 1.0
    assert 0.0 <= summary["max_channel_outage_probability"] <= 1.0


def test_orbit_pass_finite_key_budget_is_pass_duration_sensitive() -> None:
    short_samples = [{"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0}]
    long_samples = [
        {"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0},
        {"t_s": 30.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0},
        {"t_s": 60.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0},
    ]

    short_cfg = _base_config(short_samples)
    short_cfg["orbit_pass"]["dt_s"] = 30.0
    short_cfg["orbit_pass"]["finite_key"] = {
        "detection_probability": 1.0e-4,
        "pass_duty_cycle": 0.6,
        "security_epsilon": 1.0e-10,
        "parameter_estimation_fraction": 0.1,
    }

    long_cfg = _base_config(long_samples)
    long_cfg["orbit_pass"]["dt_s"] = 30.0
    long_cfg["orbit_pass"]["finite_key"] = {
        "detection_probability": 1.0e-4,
        "pass_duty_cycle": 0.6,
        "security_epsilon": 1.0e-10,
        "parameter_estimation_fraction": 0.1,
    }

    short = simulate_orbit_pass(short_cfg)
    long = simulate_orbit_pass(long_cfg)

    short_fk = short["cases"][0]["summary"]["finite_key"]
    long_fk = long["cases"][0]["summary"]["finite_key"]

    assert long_fk["pass_duration_s"] > short_fk["pass_duration_s"]
    assert long_fk["signals_per_pass_budget"] > short_fk["signals_per_pass_budget"]
    assert long_fk["effective_signals_per_block"] >= short_fk["effective_signals_per_block"]


def test_orbit_pass_trust_label_preview_and_certification_modes():
    samples = [{"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0}]

    preview_cfg = _base_config(samples)
    preview_cfg["orbit_pass"]["execution_mode"] = "preview"
    preview = simulate_orbit_pass(preview_cfg)
    assert preview["trust_label"]["mode"] == "preview"
    assert preview["trust_label"]["label"] == "preview"

    cert_cfg = _base_config(samples)
    cert_cfg["orbit_pass"]["execution_mode"] = "certification"
    cert_cfg["channel"]["pointing_model"] = "gaussian"
    cert_cfg["channel"]["pointing_sample_count"] = 128
    cert_cfg["channel"]["pointing_seed"] = 1
    cert_cfg["channel"]["turbulence_model"] = "lognormal"
    cert_cfg["channel"]["turbulence_sample_count"] = 128
    cert_cfg["channel"]["turbulence_seed"] = 2
    cert = simulate_orbit_pass(cert_cfg)
    assert cert["trust_label"]["mode"] == "certification"
    assert cert["trust_label"]["label"] == "certification"
    assert cert["trust_label"]["regime"] == "certification_candidate"


@pytest.mark.parametrize(
    "bad",
    [
        {"orbit_pass": {"id": "x", "band": "c_1550", "dt_s": 0.0, "samples": []}},
        {"orbit_pass": {"id": "", "band": "c_1550", "dt_s": 1.0, "samples": [{"t_s": 0, "distance_km": 1}]}},
        {"orbit_pass": {"id": "x", "band": "", "dt_s": 1.0, "samples": [{"t_s": 0, "distance_km": 1}]}},
    ],
)
def test_orbit_pass_rejects_invalid_minimal_inputs(bad: dict):
    base = _base_config(
        samples=[{"t_s": 0.0, "distance_km": 300.0, "elevation_deg": 60.0, "background_counts_cps": 100.0}]
    )
    bad = {**base, **bad}
    with pytest.raises(ValueError):
        simulate_orbit_pass(bad)
