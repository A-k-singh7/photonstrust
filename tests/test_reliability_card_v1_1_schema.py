from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from photonstrust.qkd import compute_point
from photonstrust.report import build_reliability_card


def test_reliability_card_v1_1_schema_minimal() -> None:
    scenario = {
        "scenario_id": "test_schema_v1_1",
        "band": "c_1550",
        "wavelength_nm": 1550,
        "distances_km": [10.0],
        "reliability_card_version": "1.1",
        "evidence_quality_tier": "simulated_only",
        "benchmark_coverage": "internal_demo",
        "calibration_diagnostics": {"status": "not_calibrated", "gate_pass": False},
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
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16, "misalignment_prob": 0.0},
        "finite_key": {"enabled": False},
        "uncertainty": {},
    }

    result = compute_point(scenario, distance_km=10)
    card = build_reliability_card(scenario, [result], None, Path("."))

    schema_path = Path("schemas") / "photonstrust.reliability_card.v1_1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=card, schema=schema)

    assert "security_assumptions_metadata" in card
    assert "finite_key_epsilon_ledger" in card
    assert "confidence_intervals" in card
    assert "model_provenance" in card
    assert card["confidence_intervals"]["key_rate_bps"]["confidence_level"] == 0.95
