from __future__ import annotations

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.workflow.schema import day10_tapeout_rehearsal_packet_schema_path


def _minimal_day10_tapeout_rehearsal_packet() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.day10_tapeout_rehearsal_packet",
        "generated_at": "2026-02-26T00:00:00Z",
        "mode": "synthetic",
        "strict": True,
        "decision": "GO",
        "reasons": [],
        "inputs": {
            "run_dir": "results/day10/run_pkg",
            "runner_config": None,
            "waiver_file": None,
            "allow_waived_failures": False,
            "require_non_mock_backend": True,
            "run_pic_gate": False,
            "deck_fingerprint": "sha256:day10-rehearsal",
            "timeout_sec": 60.0,
            "fail_stage": "none",
            "smoke_local_backend": False,
            "bootstrap_local_run_dir": False,
            "bootstrap_local_run_dir_used": False,
            "allow_ci": False,
        },
        "artifacts": {
            "foundry_smoke_report_json": "results/day10/foundry_smoke_report.json",
            "tapeout_gate_report_json": "results/day10/tapeout_gate_report.json",
            "foundry_summary_paths": {
                "drc": "results/day10/run_pkg/foundry_drc_sealed_summary.json",
                "lvs": "results/day10/run_pkg/foundry_lvs_sealed_summary.json",
                "pex": "results/day10/run_pkg/foundry_pex_sealed_summary.json",
            },
        },
        "smoke_overall_status": "pass",
        "tapeout_all_passed": True,
        "steps": [
            {
                "name": "foundry_smoke",
                "passed": True,
            }
        ],
    }


def test_day10_tapeout_rehearsal_packet_schema_accepts_minimal_valid_instance() -> None:
    validate_instance(_minimal_day10_tapeout_rehearsal_packet(), day10_tapeout_rehearsal_packet_schema_path())
