from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.calibrate.bayes import fit_emitter_params
from photonstrust.datasets.generate import generate_dataset
from photonstrust.optimize.optimizer import run_optimization
from photonstrust.qkd import compute_point, compute_sweep
from photonstrust.report import build_reliability_card
from photonstrust.scenarios.source_benchmark import run_source_benchmark
from photonstrust.scenarios.teleportation import run_teleportation


def _qkd_scenario() -> dict:
    return {
        "scenario_id": "quality_sweep",
        "band": "c_1550",
        "wavelength_nm": 1550,
        "distances_km": [10.0],
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5.0,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "physics_backend": "analytic",
            "pulse_window_ns": 5.0,
        },
        "channel": {
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5.0,
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
        "uncertainty": {"pde": 0.01},
    }


def test_calibration_outputs_diagnostics():
    result = fit_emitter_params({"g2_0": 0.02}, samples=400)
    diag = result["diagnostics"]

    assert diag["samples"] == 400
    assert diag["effective_sample_size"] > 0
    assert 0.0 <= diag["normalized_weight_entropy"] <= 1.0
    assert 0.0 <= diag["max_weight"] <= 1.0
    assert 0.0 <= diag["ess_ratio"] <= 1.0
    assert diag["r_hat_proxy"] >= 1.0
    assert 0.0 <= diag["ppc_score"] <= 1.0
    assert isinstance(diag["gate_pass"], bool)


def test_calibration_gate_can_be_enforced():
    result = fit_emitter_params({"g2_0": 0.02}, samples=400, enforce_gates=True)
    assert result["diagnostics"]["gate_pass"] is True


def test_calibration_gate_failure_raises_when_enforced():
    with pytest.raises(ValueError):
        fit_emitter_params(
            {"g2_0": 0.02},
            samples=400,
            enforce_gates=True,
            gate_thresholds={
                "min_effective_sample_size_ratio": 0.95,
                "max_r_hat_proxy": 1.0,
                "min_ppc_score": 0.95,
            },
        )


def test_reliability_card_uncertainty_includes_outage_probability(tmp_path):
    scenario = _qkd_scenario()
    sweep = compute_sweep(scenario, include_uncertainty=True)
    card = build_reliability_card(
        scenario,
        sweep["results"],
        sweep["uncertainty"],
        tmp_path,
    )
    uncertainty = card["outputs"]["uncertainty"]
    assert uncertainty is not None
    assert "outage_probability" in uncertainty
    assert 0.0 <= uncertainty["outage_probability"] <= 1.0


def test_reliability_card_includes_trust_extension_fields(tmp_path):
    scenario = _qkd_scenario()
    scenario["evidence_quality_tier"] = "calibrated_lab"
    scenario["benchmark_coverage"] = "metro_qkd_v1"
    scenario["calibration_diagnostics"] = {
        "status": "posterior_validated",
        "gate_pass": True,
        "ess_ratio": 0.45,
        "r_hat_proxy": 1.02,
        "ppc_score": 0.72,
    }
    scenario["reproducibility_artifact_uri"] = "s3://example/artifact/abc123"

    sweep = compute_sweep(scenario, include_uncertainty=False)
    card = build_reliability_card(scenario, sweep["results"], None, tmp_path)

    assert card["evidence_quality_tier"] == "calibrated_lab"
    assert card["benchmark_coverage"] == "metro_qkd_v1"
    assert card["calibration_diagnostics"]["gate_pass"] is True
    assert card["reproducibility_artifact_uri"] == "s3://example/artifact/abc123"


def test_reliability_card_v1_1_includes_security_epsilon_ci_and_model_provenance(tmp_path):
    scenario = _qkd_scenario()
    scenario["reliability_card_version"] = "1.1"
    scenario["uncertainty"] = {"confidence_level": 0.9, "method": "bootstrap"}
    scenario["finite_key"] = {
        "enabled": True,
        "signals_per_block": 1000000,
        "security_epsilon": 1e-10,
        "epsilon_correctness": 5e-11,
        "epsilon_secrecy": 5e-11,
    }

    sweep = compute_sweep(scenario, include_uncertainty=True)
    card = build_reliability_card(scenario, sweep["results"], sweep["uncertainty"], tmp_path)

    assert card["security_assumptions_metadata"]["assume_iid"] is True
    assert card["finite_key_epsilon_ledger"]["enabled"] is True
    assert card["finite_key_epsilon_ledger"]["signals_per_block"] == 1000000
    assert card["finite_key_epsilon_ledger"]["epsilon_total"] == pytest.approx(1e-10)
    assert card["confidence_intervals"]["key_rate_bps"]["confidence_level"] == pytest.approx(0.9)
    assert card["model_provenance"]["protocol_normalized"] == "bbm92"


def test_channel_polarization_penalty_is_optional_and_reduces_key_rate():
    scenario_a = _qkd_scenario()
    scenario_b = _qkd_scenario()
    scenario_b["channel"]["polarization_coherence_length_km"] = 10.0

    a = compute_point(scenario_a, distance_km=50.0)
    b = compute_point(scenario_b, distance_km=50.0)

    # Polarization coherence is modeled as a visibility/misalignment penalty
    # (QBER increase), not an attenuation term.
    assert b.loss_db == pytest.approx(a.loss_db, rel=0.0, abs=0.0)
    assert b.p_pair == pytest.approx(a.p_pair, rel=0.0, abs=0.0)
    assert b.entanglement_rate_hz == pytest.approx(a.entanglement_rate_hz, rel=1e-12, abs=0.0)
    assert b.qber_total >= a.qber_total
    assert b.q_misalignment >= a.q_misalignment

    assert b.key_rate_bps <= a.key_rate_bps


def test_teleportation_outputs_summary_and_outage(tmp_path):
    cfg = {
        "teleportation": {
            "id": "tele_test",
            "distance_km": {"start": 0, "stop": 20, "step": 10},
            "classical_latency_ns": 1000.0,
            "sla": {"min_success_prob": 0.01, "min_fidelity": 0.7},
            "memory": {
                "t1_ms": 50.0,
                "t2_ms": 10.0,
                "retrieval_efficiency": 0.8,
                "store_efficiency": 0.95,
                "physics_backend": "analytic",
            },
            "link_scenario": _qkd_scenario(),
        }
    }
    out = run_teleportation(cfg, tmp_path)
    assert "summary" in out
    assert 0.0 <= out["summary"]["outage_probability"] <= 1.0
    assert all("outage" in row for row in out["results"])

    payload = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert "summary" in payload


def test_optimization_output_includes_sensitivity(tmp_path):
    cfg = {
        "optimization": {
            "id": "opt_quality",
            "type": "repeater_spacing",
            "total_distance_km": [100.0],
            "spacing_km": {"start": 10.0, "stop": 30.0, "step": 10.0},
            "memory": {
                "t2_ms": 10.0,
                "retrieval_efficiency": 0.75,
                "store_efficiency": 0.95,
                "physics_backend": "analytic",
            },
            "link_scenario": _qkd_scenario(),
        }
    }
    out = run_optimization(cfg, tmp_path)
    best = out["best"]["100.0"]
    assert "sensitivity" in best
    assert "local_sensitivity" in best["sensitivity"]


def test_source_benchmark_projection_fields(tmp_path):
    cfg = {
        "source_benchmark": {
            "id": "src_bench_test",
            "distance_km": 20.0,
            "source": {
                "type": "emitter_cavity",
                "physics_backend": "analytic",
                "rep_rate_mhz": 100,
                "collection_efficiency": 0.35,
                "coupling_efficiency": 0.6,
                "radiative_lifetime_ns": 1.0,
                "purcell_factor": 5,
                "dephasing_rate_per_ns": 0.5,
                "g2_0": 0.02,
                "pulse_window_ns": 5.0,
            },
            "link_scenario": _qkd_scenario(),
        }
    }
    result = run_source_benchmark(cfg, tmp_path)

    assert "projected_key_rate_bps" in result
    assert "projected_fidelity" in result
    assert 0.0 <= result["projected_fidelity"] <= 1.0


def test_dataset_entry_uses_config_seed(tmp_path):
    cfg = {
        "scenario": {
            "id": "dataset_seed_case",
            "distance_km": 10,
            "band": "c_1550",
            "wavelength_nm": 1550,
            "seed": 77,
        },
        "source": {
            "type": "emitter_cavity",
            "physics_backend": "analytic",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "pulse_window_ns": 5.0,
        },
        "channel": {"fiber_loss_db_per_km": 0.2, "connector_loss_db": 1.5, "dispersion_ps_per_km": 5},
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
        "uncertainty": {},
    }
    config_path = tmp_path / "config.yml"
    config_path.write_text(
        "\n".join(
            [
                "scenario:",
                "  id: dataset_seed_case",
                "  distance_km: 10",
                "  band: c_1550",
                "  wavelength_nm: 1550",
                "  seed: 77",
                "source:",
                "  type: emitter_cavity",
                "  physics_backend: analytic",
                "  rep_rate_mhz: 100",
                "  collection_efficiency: 0.35",
                "  coupling_efficiency: 0.6",
                "  radiative_lifetime_ns: 1.0",
                "  purcell_factor: 5",
                "  dephasing_rate_per_ns: 0.5",
                "  g2_0: 0.02",
                "  pulse_window_ns: 5.0",
                "channel:",
                "  fiber_loss_db_per_km: 0.2",
                "  connector_loss_db: 1.5",
                "  dispersion_ps_per_km: 5",
                "detector:",
                "  class: snspd",
                "  pde: 0.3",
                "  dark_counts_cps: 100",
                "  jitter_ps_fwhm: 30",
                "  dead_time_ns: 100",
                "  afterpulsing_prob: 0.001",
                "timing:",
                "  sync_drift_ps_rms: 10",
                "  coincidence_window_ps: 200",
                "protocol:",
                "  name: BBM92",
                "  sifting_factor: 0.5",
                "  ec_efficiency: 1.16",
                "uncertainty: {}",
            ]
        ),
        encoding="utf-8",
    )

    output_path = generate_dataset(config_path, tmp_path / "out")
    entry = json.loads(output_path.read_text(encoding="utf-8"))
    assert entry["metadata"]["seed"] == 77
