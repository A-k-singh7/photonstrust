from __future__ import annotations

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.workflow.schema import pic_tapeout_gate_schema_path


def _minimal_pic_tapeout_gate_report() -> dict:
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_tapeout_gate",
        "generated_at": "2026-02-26T00:00:00Z",
        "run_dir": "results/day10/run_pkg",
        "required_artifacts": [
            "inputs/graph.json",
        ],
        "checks": [
            {
                "name": "required_artifacts",
                "passed": True,
            }
        ],
        "all_passed": True,
    }


def test_pic_tapeout_gate_schema_accepts_minimal_valid_instance() -> None:
    validate_instance(_minimal_pic_tapeout_gate_report(), pic_tapeout_gate_schema_path())
