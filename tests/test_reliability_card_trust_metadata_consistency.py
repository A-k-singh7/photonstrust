from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from jsonschema import validate

from photonstrust.qkd import compute_point
from photonstrust.report import build_reliability_card


@pytest.fixture
def _base_scenario() -> dict:
    return {
        "scenario_id": "trust_metadata_consistency",
        "band": "c_1550",
        "wavelength_nm": 1550,
        "distances_km": [25.0],
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
        "finite_key": {"enabled": False},
        "uncertainty": {},
    }


def _scenario_for_protocol(base: dict, protocol_name: str, version: str) -> dict:
    scenario = copy.deepcopy(base)
    scenario["scenario_id"] = f"trust_{protocol_name.lower()}_{version.replace('.', '_')}"
    scenario["reliability_card_version"] = version

    proto = {
        "name": protocol_name,
        "sifting_factor": 0.5,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
    }
    if protocol_name == "BB84":
        proto.update({"mu": 0.5, "nu": 0.1, "omega": 0.0})
    elif protocol_name == "MDI_QKD":
        proto.update({"sifting_factor": 1.0, "relay_fraction": 0.5, "mu": 0.4, "nu": 0.1, "omega": 0.0})
    elif protocol_name in {"PM_QKD", "TF_QKD"}:
        proto.update({"sifting_factor": 1.0, "relay_fraction": 0.5, "mu": 0.5, "phase_slices": 16})
    scenario["protocol"] = proto
    return scenario


@pytest.mark.parametrize("protocol_name", ["BB84", "BBM92", "MDI_QKD", "PM_QKD", "TF_QKD"])
def test_trust_metadata_fields_present_for_all_protocols_v1_0(_base_scenario: dict, protocol_name: str, tmp_path: Path) -> None:
    scenario = _scenario_for_protocol(_base_scenario, protocol_name, version="1.0")
    result = compute_point(scenario, distance_km=25.0)
    card = build_reliability_card(scenario, [result], None, tmp_path)

    assert "security_assumptions_metadata" in card
    assert "finite_key_epsilon_ledger" in card
    assert "confidence_intervals" in card
    assert "model_provenance" in card
    assert card["model_provenance"]["protocol_normalized"] in {"bb84_decoy", "bbm92", "mdi_qkd", "pm_qkd", "tf_qkd"}
    assert card["safe_use_label"]["label"] in {"qualitative", "security_target_ready", "engineering_grade"}

    sec = card["security_assumptions_metadata"]
    if protocol_name in {"BB84", "MDI_QKD"}:
        assert sec["decoy_state_assumption"] is True
    else:
        assert sec["decoy_state_assumption"] is False


@pytest.mark.parametrize("protocol_name", ["BB84", "BBM92", "MDI_QKD", "PM_QKD", "TF_QKD"])
def test_trust_metadata_fields_present_for_all_protocols_v1_1(_base_scenario: dict, protocol_name: str, tmp_path: Path) -> None:
    scenario = _scenario_for_protocol(_base_scenario, protocol_name, version="1.1")
    result = compute_point(scenario, distance_km=25.0)
    card = build_reliability_card(scenario, [result], None, tmp_path)

    schema_path = Path("schemas") / "photonstrust.reliability_card.v1_1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=card, schema=schema)

    assert card["security_assumptions_metadata"]["security_model"]
    assert "enabled" in card["finite_key_epsilon_ledger"]
    assert "key_rate_bps" in card["confidence_intervals"]
    assert card["model_provenance"]["protocol_normalized"] in {"bb84_decoy", "bbm92", "mdi_qkd", "pm_qkd", "tf_qkd"}
    assert card["safe_use_label"]["label"] in {"qualitative", "security_target_ready", "engineering_grade"}
    assert card["safe_use_label"]["label"] not in {"PM_QKD", "TF_QKD"}
