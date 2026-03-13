from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "build_pic_external_data_manifest.py"
    spec = importlib.util.spec_from_file_location("build_pic_external_data_manifest_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_pic_external_data_manifest_detects_requirements(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    gate_b = {
        "metrics": {
            "b5_drift": {"status": "pending_silicon_required"},
        }
    }
    gate_e = {
        "metrics": {
            "e1_ci_stability": {"status": "preflight_pass_synthetic", "synthetic": True},
            "e3_failure_triage_quality": {"status": "preflight_pass_synthetic", "synthetic": True},
        }
    }

    gate_b_path = tmp_path / "gate_b.json"
    gate_e_path = tmp_path / "gate_e.json"
    output = tmp_path / "manifest.json"
    _write_json(gate_b_path, gate_b)
    _write_json(gate_e_path, gate_e)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_external_data_manifest.py",
            "--gate-b",
            str(gate_b_path),
            "--gate-e",
            str(gate_e_path),
            "--rc-id",
            "rc_test",
            "--output",
            str(output),
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert Path(printed["manifest"]).exists()
    assert int(printed["source_candidate_count"]) >= 1
    assert int(printed["integration_plan_count"]) >= 1

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["kind"] == "photonstrust.pic_external_data_manifest"
    assert int(payload["requirement_count"]) >= 6
    ids = {row["id"] for row in payload["requirements"]}
    assert "EXT-B1" in ids and "EXT-E1" in ids and "EXT-E3" in ids

    assert payload["source_policy"]["license_policy"] == "allowlist_only"
    assert set(payload["source_policy"]["allowed_licenses"]) == {"Apache-2.0", "MIT"}
    assert int(payload["source_candidate_count"]) >= 6

    for row in payload["source_candidates"]:
        assert row["license"] in {"Apache-2.0", "MIT"}

    requirement_map = payload["requirement_to_source_ids"]
    assert requirement_map["EXT-B1"]
    assert requirement_map["EXT-E1"]
    assert requirement_map["EXT-B1"][0] == "SRC-GDSFACTORY-CORE"
    assert requirement_map["EXT-E1"][0] == "SRC-APACHE-DEVLAKE"
    assert requirement_map["EXT-E1"][-1] == "SRC-DORA-FOURKEYS"

    for row in payload["requirements"]:
        assert isinstance(row["recommended_source_ids"], list)
        if row["recommended_source_ids"]:
            assert row["primary_source_id"] == row["recommended_source_ids"][0]

    plan_rows = payload["integration_plan"]
    assert int(payload["integration_plan_count"]) == len(plan_rows)
    plan_by_requirement = {row["requirement_id"]: row for row in plan_rows}
    assert plan_by_requirement["EXT-B1"]["owner_role"] == "PIC Modeling Lead"
    assert plan_by_requirement["EXT-E1"]["primary_source_id"] == "SRC-APACHE-DEVLAKE"
