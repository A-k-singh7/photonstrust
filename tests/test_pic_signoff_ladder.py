from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate


def _schema() -> dict:
    schema_path = Path("schemas") / "photonstrust.pic_signoff_ladder.v0.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _minimal_valid_instance() -> dict:
    return {
        "schema_version": "0.1",
        "generated_at": "2026-02-26T00:00:00Z",
        "kind": "pic.signoff_ladder",
        "run_id": "deadbeef",
        "inputs": {
            "chip_assembly_run_id": "abcdef12",
            "chip_assembly_hash": "a" * 64,
            "policy_hash": "b" * 64,
            "multi_stage_enabled": True,
        },
        "ladder": [
            {
                "level": 1,
                "stage": "chip_assembly",
                "status": "pass",
                "run_id": "abcdef12",
                "reason": "chip_assembly status=pass",
                "evidence_hashes": ["a" * 64],
                "failure_rule_ids": [],
                "waived_rule_ids": [],
                "prev_stage_hash": "a" * 64,
                "stage_hash": "c" * 64,
            },
            {
                "level": 2,
                "stage": "drc",
                "status": "pass",
                "run_id": "d" * 12,
                "reason": "drc status=pass",
                "evidence_hashes": ["d" * 64],
                "failure_rule_ids": [],
                "waived_rule_ids": [],
                "prev_stage_hash": "c" * 64,
                "stage_hash": "e" * 64,
            },
            {
                "level": 3,
                "stage": "lvs",
                "status": "pass",
                "run_id": "e" * 12,
                "reason": "lvs status=pass",
                "evidence_hashes": ["f" * 64],
                "failure_rule_ids": [],
                "waived_rule_ids": [],
                "prev_stage_hash": "e" * 64,
                "stage_hash": "1" * 64,
            },
            {
                "level": 4,
                "stage": "pex",
                "status": "pass",
                "run_id": "f" * 12,
                "reason": "pex status=pass",
                "evidence_hashes": ["2" * 64],
                "failure_rule_ids": [],
                "waived_rule_ids": [],
                "prev_stage_hash": "1" * 64,
                "stage_hash": "3" * 64,
            },
            {
                "level": 5,
                "stage": "foundry_approval",
                "status": "pass",
                "run_id": "1" * 12,
                "reason": "foundry_approval status=go",
                "evidence_hashes": ["4" * 64],
                "failure_rule_ids": [],
                "waived_rule_ids": [],
                "prev_stage_hash": "3" * 64,
                "stage_hash": "5" * 64,
            },
        ],
        "final_decision": {
            "decision": "GO",
            "reasons": ["All required signoff gates passed."],
        },
        "evidence_chain_root": "5" * 64,
        "provenance": {
            "photonstrust_version": "test",
            "python": "3.12",
            "platform": "test",
        },
    }


def test_pic_signoff_ladder_schema_minimal_instance() -> None:
    validate(instance=_minimal_valid_instance(), schema=_schema())


def test_pic_signoff_ladder_schema_rejects_wrong_stage_order() -> None:
    payload = deepcopy(_minimal_valid_instance())
    payload["ladder"][1]["stage"] = "lvs"

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=_schema())


def test_pic_signoff_ladder_schema_rejects_missing_stage_hash() -> None:
    payload = deepcopy(_minimal_valid_instance())
    payload["ladder"][3].pop("stage_hash")

    with pytest.raises(ValidationError):
        validate(instance=payload, schema=_schema())
