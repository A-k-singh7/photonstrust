from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate


def _schema() -> dict:
    schema_path = Path("schemas") / "photonstrust.pic_signoff_ladder.v0.schema.json"
    return json.loads(schema_path.read_text(encoding="utf-8"))


def test_pic_signoff_ladder_schema_minimal_instance() -> None:
    ladder = {
        "schema_version": "0.1",
        "generated_at": "2026-02-26T00:00:00Z",
        "kind": "pic.signoff_ladder",
        "run_id": "deadbeef",
        "inputs": {
            "chip_assembly_run_id": "abcdef12",
            "chip_assembly_hash": "a" * 64,
            "policy_hash": "b" * 64,
        },
        "ladder": [
            {
                "level": 1,
                "stage": "chip_assembly",
                "status": "pass",
            }
        ],
        "final_decision": {
            "decision": "GO",
            "reasons": ["All required signoff gates passed."],
        },
        "provenance": {
            "photonstrust_version": "test",
            "python": "3.12",
            "platform": "test",
        },
    }

    validate(instance=ladder, schema=_schema())
