from __future__ import annotations

import pytest

from photonstrust.qkd import compute_point
from photonstrust.qkd_protocols.registry import available_protocols, protocol_applicability, protocol_gate_policy, resolve_protocol_module


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
        "protocol": {"name": "BBM92", "sifting_factor": 0.5, "ec_efficiency": 1.16},
    }


def test_protocol_registry_resolution_and_aliases() -> None:
    assert available_protocols() == ("bb84_decoy", "bbm92", "mdi_qkd", "pm_qkd", "tf_qkd")

    assert resolve_protocol_module(None).protocol_id == "bbm92"
    assert resolve_protocol_module("bb84").protocol_id == "bb84_decoy"
    assert resolve_protocol_module("mdi").protocol_id == "mdi_qkd"
    assert resolve_protocol_module("pm").protocol_id == "pm_qkd"
    assert resolve_protocol_module("tf").protocol_id == "tf_qkd"


def test_protocol_applicability_enforces_relay_fiber_constraint() -> None:
    scenario = _base_scenario()
    scenario["channel"]["model"] = "free_space"

    mdi_app = protocol_applicability("mdi_qkd", scenario)
    tf_app = protocol_applicability("tf_qkd", scenario)

    assert mdi_app.status == "fail"
    assert tf_app.status == "fail"
    assert "fiber" in " ".join(mdi_app.reasons).lower()
    assert "fiber" in " ".join(tf_app.reasons).lower()


def test_protocol_gate_policy_routes_plob_by_protocol_family() -> None:
    assert protocol_gate_policy("bbm92")["plob_repeaterless_bound"] == "apply"
    assert protocol_gate_policy("bb84_decoy")["plob_repeaterless_bound"] == "apply"
    assert protocol_gate_policy("mdi_qkd")["plob_repeaterless_bound"] == "skip"
    assert protocol_gate_policy("pm_qkd")["plob_repeaterless_bound"] == "skip"
    assert protocol_gate_policy("tf_qkd")["plob_repeaterless_bound"] == "skip"


def test_compute_point_assigns_explicit_protocol_name_for_relay_variants() -> None:
    scenario = _base_scenario()
    scenario["protocol"] = {
        "name": "TF_QKD",
        "sifting_factor": 1.0,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.0,
        "relay_fraction": 0.5,
        "mu": 0.5,
        "phase_slices": 16,
    }

    res = compute_point(scenario, distance_km=20.0)

    assert res.protocol_name == "tf_qkd"


def test_unknown_protocol_name_still_raises() -> None:
    scenario = _base_scenario()
    scenario["protocol"]["name"] = "unknown_protocol"
    with pytest.raises(ValueError, match="Unsupported QKD protocol name"):
        compute_point(scenario, distance_km=10.0)
