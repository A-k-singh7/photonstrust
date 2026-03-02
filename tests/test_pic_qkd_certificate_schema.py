from __future__ import annotations

import copy

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.workflow.schema import pic_qkd_certificate_schema_path


def _minimal_certificate_payload() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_qkd_certificate",
        "generated_at": "2026-03-02T00:00:00Z",
        "decision": "GO",
        "graph_id": "schema_minimal_graph",
        "inputs": {
            "graph_path": None,
            "pdk": "generic_silicon_photonics",
            "pdk_version": "0",
            "protocol": "BB84_DECOY",
            "wavelength_nm": 1550.0,
            "target_distance_km": 50.0,
            "distances_km": [0.0, 50.0],
            "dry_run": True,
            "output_dir": None,
            "signing_key": None,
        },
        "hashes": {
            "graph_hash": "a" * 64,
            "compiled_netlist_hash": "b" * 64,
            "assembly_report_hash": "c" * 64,
            "signoff_report_hash": "d" * 64,
            "simulation_result_hash": None,
            "qkd_sweep_hash": None,
            "certificate_payload_hash": "e" * 64,
        },
        "provenance": {
            "photonstrust_version": "0.1.0",
            "python": "3.12.0",
            "platform": "unit-test",
        },
        "steps": [
            {"name": "compile_graph", "status": "pass"},
            {"name": "assemble_pic_chip", "status": "pass"},
        ],
        "artifacts": {"certificate_path": None},
        "signoff": {
            "decision": "GO",
            "run_id": "abcdef123456",
            "reasons": [],
        },
        "signoff_report": {},
        "drc_summary": {},
        "lvs_summary": {},
        "pex_summary": {},
        "foundry_approval_summary": {},
        "simulation_result": None,
        "qkd_scenario": None,
        "qkd_sweep": None,
        "target_distance_summary": None,
        "signature": None,
    }


def test_pic_qkd_certificate_schema_accepts_minimal_payload() -> None:
    validate_instance(_minimal_certificate_payload(), pic_qkd_certificate_schema_path())


def test_pic_qkd_certificate_schema_accepts_full_payload() -> None:
    payload = copy.deepcopy(_minimal_certificate_payload())
    payload["decision"] = "HOLD"
    payload["inputs"]["dry_run"] = False
    payload["inputs"]["output_dir"] = "results/certify"
    payload["hashes"]["simulation_result_hash"] = "f" * 64
    payload["hashes"]["qkd_sweep_hash"] = "0" * 64
    payload["artifacts"]["certificate_path"] = "results/certify/certificate.json"
    payload["signoff"]["decision"] = "HOLD"
    payload["signoff"]["reasons"] = ["drc failed"]
    payload["simulation_result"] = {"chain_solver": {"eta_total": 0.7}}
    payload["qkd_scenario"] = {"protocol": {"name": "BB84_DECOY"}}
    payload["qkd_sweep"] = {"results": [{"distance_km": 50.0, "key_rate_bps": 1.0}]}
    payload["target_distance_summary"] = {
        "status": "ok",
        "target_distance_km": 50.0,
        "nearest_distance_km": 50.0,
        "key_rate_bps": 1.0,
        "qber_total": 0.01,
        "fidelity": 0.99,
        "loss_db": 5.0,
        "protocol_name": "bb84_decoy",
    }
    payload["signature"] = {
        "algorithm": "ed25519",
        "key_path": "results/keys/private.pem",
        "signature_b64": "YQ==",
        "message_sha256": "1" * 64,
    }
    validate_instance(payload, pic_qkd_certificate_schema_path())
