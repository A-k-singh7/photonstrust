from __future__ import annotations

import json

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.qkd import compute_sweep
from photonstrust.sweep import run_scenarios
from photonstrust.workflow.schema import multifidelity_report_schema_path


def _scenario(mode: str) -> dict:
    return {
        "scenario_id": "multifidelity_case",
        "band": "c_1550",
        "wavelength_nm": 1550.0,
        "distances_km": [10.0, 20.0],
        "execution_mode": mode,
        "preview_uncertainty_samples": 12,
        "preview_detector_sample_scale": 0.2,
        "certification_uncertainty_samples": 36,
        "certification_detector_sample_scale": 1.4,
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
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5.0,
        },
        "detector": {
            "class": "snspd",
            "physics_backend": "stochastic",
            "sample_count": 300,
            "seed": 42,
            "time_bin_ps": 10.0,
            "afterpulse_delay_ns": 50.0,
            "pde": 0.3,
            "dark_counts_cps": 100.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 100.0,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10.0, "coincidence_window_ps": 200.0},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {
            "fiber_loss_db_per_km": 0.02,
            "pde": 0.05,
            "dark_counts": 0.5,
            "jitter": 0.1,
            "g2_0": 0.2,
            "mu": 0.0,
        },
    }


def test_preview_mode_uses_preview_settings():
    sweep = compute_sweep(_scenario("preview"), include_uncertainty=True)
    perf = sweep["performance"]
    assert perf["execution_mode"] == "preview"
    assert perf["uncertainty_samples"] == 12
    assert perf["detector_sample_scale"] == 0.2
    assert sweep["uncertainty"] is not None


def test_certification_mode_uses_certification_settings():
    sweep = compute_sweep(_scenario("certification"), include_uncertainty=True)
    perf = sweep["performance"]
    assert perf["execution_mode"] == "certification"
    assert perf["uncertainty_samples"] == 36
    assert perf["detector_sample_scale"] == 1.4
    assert sweep["uncertainty"] is not None


def test_run_scenarios_writes_schema_valid_multifidelity_report(tmp_path):
    scenario = _scenario("preview")
    out = run_scenarios([scenario], tmp_path, run_id="phase51_w08_multifidelity")

    report_path = tmp_path / "multifidelity_report.json"
    assert report_path.exists()
    assert out.get("multifidelity_report_path") == str(report_path)

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    validate_instance(payload, multifidelity_report_schema_path())
    assert payload["kind"] == "multifidelity.report"
    assert payload["run_id"] == "phase51_w08_multifidelity"
    assert "qiskit:repeater_primitive" in payload["backend_results"]
