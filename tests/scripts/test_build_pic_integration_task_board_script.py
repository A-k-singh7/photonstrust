from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "build_pic_integration_task_board.py"
    spec = importlib.util.spec_from_file_location("build_pic_integration_task_board_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_pic_integration_task_board_from_integration_plan(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    existing_expected_path = tmp_path / "existing_bundle.json"
    existing_expected_path.write_text("{}\n", encoding="utf-8")

    manifest = {
        "kind": "photonstrust.pic_external_data_manifest",
        "integration_plan": [
            {
                "execution_order": 2,
                "requirement_id": "EXT-B2",
                "area": "GateB",
                "owner_role": "PIC Device Characterization Lead",
                "definition_of_done": "B2 pass with measured resonance data.",
                "expected_path": "datasets/measurements/private/rc_next/b2_resonance/measurement_bundle.json",
                "primary_source_id": "SRC-GDSFACTORY-CORE",
                "ranked_sources": [
                    {
                        "source_id": "SRC-GDSFACTORY-CORE",
                        "repository": "gdsfactory/gdsfactory",
                        "license": "MIT",
                        "maintenance_status": "active",
                    }
                ],
            },
            {
                "execution_order": 1,
                "requirement_id": "EXT-B1",
                "area": "GateB",
                "owner_role": "PIC Modeling Lead",
                "definition_of_done": "B1 pass with measured insertion-loss data.",
                "expected_path": str(existing_expected_path),
                "primary_source_id": "SRC-GDSFACTORY-CORE",
                "ranked_sources": [
                    {
                        "source_id": "SRC-GDSFACTORY-CORE",
                        "repository": "gdsfactory/gdsfactory",
                        "license": "MIT",
                        "maintenance_status": "active",
                    },
                    {
                        "source_id": "SRC-GDSFACTORY-GPLUGINS",
                        "repository": "gdsfactory/gplugins",
                        "license": "MIT",
                        "maintenance_status": "active",
                    },
                ],
            },
        ],
    }

    manifest_path = tmp_path / "manifest.json"
    output_json = tmp_path / "task_board.json"
    output_csv = tmp_path / "task_board.csv"
    _write_json(manifest_path, manifest)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_integration_task_board.py",
            "--manifest",
            str(manifest_path),
            "--output-json",
            str(output_json),
            "--output-csv",
            str(output_csv),
            "--default-status",
            "in_progress",
            "--start-date",
            "2026-03-10",
            "--target-step-days",
            "3",
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert Path(printed["task_board_json"]).exists()
    assert Path(printed["task_board_csv"]).exists()
    assert int(printed["task_count"]) == 2
    assert int(printed["blocked_task_count"]) == 1

    task_board = json.loads(output_json.read_text(encoding="utf-8"))
    assert task_board["kind"] == "photonstrust.pic_integration_task_board"
    assert task_board["task_count"] == 2
    assert task_board["owner_count"] == 2
    assert task_board["blocked_task_count"] == 1
    assert task_board["tasks"][0]["requirement_id"] == "EXT-B1"
    assert task_board["tasks"][1]["requirement_id"] == "EXT-B2"
    assert task_board["tasks"][0]["target_date_utc"] == "2026-03-10"
    assert task_board["tasks"][1]["target_date_utc"] == "2026-03-13"
    assert task_board["tasks"][0]["blocker_summary"] == "clear"
    assert task_board["tasks"][1]["blocker_summary"] == "dependency+missing_expected_path"
    assert task_board["tasks"][1]["dependency_blocker_task_id"] == "TASK-01-EXT-B1"

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["requirement_id"] == "EXT-B1"
    assert rows[0]["owner_role"] == "PIC Modeling Lead"
    assert rows[1]["blocker_summary"] == "dependency+missing_expected_path"


def test_build_pic_integration_task_board_fallback_without_integration_plan(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()

    manifest = {
        "kind": "photonstrust.pic_external_data_manifest",
        "requirements": [
            {
                "id": "EXT-Z1",
                "area": "GateZ",
                "description": "Provide a real dataset for Z1.",
                "expected_path": "datasets/private/z1/measurement_bundle.json",
                "recommended_source_ids": ["SRC-Z"],
            }
        ],
        "requirement_to_source_ids": {
            "EXT-Z1": ["SRC-Z"],
        },
        "source_candidates": [
            {
                "source_id": "SRC-Z",
                "repository": "example/z",
                "license": "MIT",
            }
        ],
    }

    manifest_path = tmp_path / "manifest_fallback.json"
    output_json = tmp_path / "task_board_fallback.json"
    output_csv = tmp_path / "task_board_fallback.csv"
    _write_json(manifest_path, manifest)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_integration_task_board.py",
            "--manifest",
            str(manifest_path),
            "--output-json",
            str(output_json),
            "--output-csv",
            str(output_csv),
        ],
    )

    assert module.main() == 0
    task_board = json.loads(output_json.read_text(encoding="utf-8"))
    assert task_board["task_count"] == 1
    assert task_board["tasks"][0]["owner_role"] == "TBD"
    assert task_board["tasks"][0]["primary_source_id"] == "SRC-Z"
    assert task_board["tasks"][0]["blocker_summary"] == "missing_expected_path"
