from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "build_pic_gate_e_packet.py"
    spec = importlib.util.spec_from_file_location("build_pic_gate_e_packet_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_pic_gate_e_packet_pending_without_ci_history(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    decision_a = {
        "decision": "GO",
        "tapeout_all_passed": True,
        "steps": [{"name": "a", "duration_s": 3.0}, {"name": "b", "duration_s": 2.0}],
    }
    decision_b = {
        "decision": "GO",
        "tapeout_all_passed": True,
        "steps": [{"name": "a", "duration_s": 4.0}, {"name": "b", "duration_s": 2.5}],
    }
    claim_matrix = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_claim_evidence_matrix",
        "claims": [
            {
                "claim_id": "CLM-1",
                "external": True,
                "evidence_paths": ["results/pic_readiness/tapeout_gate_report.json"],
            }
        ],
    }

    decision_a_path = tmp_path / "decision_a.json"
    decision_b_path = tmp_path / "decision_b.json"
    claim_matrix_path = tmp_path / "claim_matrix.json"
    ci_workflow_path = tmp_path / "ci.yml"
    output_path = tmp_path / "gate_e_packet.json"

    _write_json(decision_a_path, decision_a)
    _write_json(decision_b_path, decision_b)
    _write_json(claim_matrix_path, claim_matrix)
    ci_workflow_path.write_text("name: ci\n- run: pre-commit\n- run: pytest -q\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_gate_e_packet.py",
            "--decision-packet",
            str(decision_a_path),
            "--decision-packet",
            str(decision_b_path),
            "--claim-matrix",
            str(claim_matrix_path),
            "--ci-workflow",
            str(ci_workflow_path),
            "--no-run-release-verifiers",
            "--e2-min-runs",
            "2",
            "--output",
            str(output_path),
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert Path(printed["packet"]).exists()
    assert printed["overall"] == "pending"

    packet = json.loads(output_path.read_text(encoding="utf-8"))
    metrics = packet["metrics"]
    assert metrics["e2_time_to_evidence_sla"]["status"] == "pass"
    assert metrics["e4_claim_governance_matrix"]["status"] == "pass"
    assert metrics["e1_ci_stability"]["status"] == "pending_ci_history_required"
    assert packet["status"]["overall"] == "pending"


def test_build_pic_gate_e_packet_uses_synthetic_metrics_preflight(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    decision_a = {
        "decision": "GO",
        "tapeout_all_passed": True,
        "steps": [{"name": "a", "duration_s": 3.0}, {"name": "b", "duration_s": 2.0}],
    }
    decision_b = {
        "decision": "GO",
        "tapeout_all_passed": True,
        "steps": [{"name": "a", "duration_s": 4.0}, {"name": "b", "duration_s": 2.5}],
    }
    claim_matrix = {
        "schema_version": "0.1",
        "kind": "photonstrust.pic_claim_evidence_matrix",
        "claims": [
            {
                "claim_id": "CLM-1",
                "external": True,
                "evidence_paths": ["results/pic_readiness/tapeout_gate_report.json"],
            }
        ],
    }
    ci_history = {
        "schema_version": "0.1",
        "synthetic": True,
        "metrics": {
            "run_count": 12,
            "pass_rate_percent": 98.0,
            "flaky_rate_percent": 2.0,
        },
        "thresholds": {
            "min_pass_rate_percent": 95.0,
            "max_flaky_rate_percent": 3.0,
        },
    }
    triage_metrics = {
        "schema_version": "0.1",
        "synthetic": True,
        "mean_time_to_root_cause_hours": 12.0,
        "target_hours": 24.0,
    }

    decision_a_path = tmp_path / "decision_a.json"
    decision_b_path = tmp_path / "decision_b.json"
    claim_matrix_path = tmp_path / "claim_matrix.json"
    ci_history_path = tmp_path / "ci_history.json"
    triage_path = tmp_path / "triage.json"
    ci_workflow_path = tmp_path / "ci.yml"
    output_path = tmp_path / "gate_e_packet.json"

    _write_json(decision_a_path, decision_a)
    _write_json(decision_b_path, decision_b)
    _write_json(claim_matrix_path, claim_matrix)
    _write_json(ci_history_path, ci_history)
    _write_json(triage_path, triage_metrics)
    ci_workflow_path.write_text("name: ci\n- run: pre-commit\n- run: pytest -q\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_gate_e_packet.py",
            "--decision-packet",
            str(decision_a_path),
            "--decision-packet",
            str(decision_b_path),
            "--claim-matrix",
            str(claim_matrix_path),
            "--ci-history-json",
            str(ci_history_path),
            "--triage-metrics-json",
            str(triage_path),
            "--ci-workflow",
            str(ci_workflow_path),
            "--no-run-release-verifiers",
            "--e2-min-runs",
            "2",
            "--output",
            str(output_path),
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert Path(printed["packet"]).exists()

    packet = json.loads(output_path.read_text(encoding="utf-8"))
    metrics = packet["metrics"]
    assert metrics["e1_ci_stability"]["status"] == "preflight_pass_synthetic"
    assert metrics["e3_failure_triage_quality"]["status"] == "preflight_pass_synthetic"
    assert packet["status"]["overall"] == "pending"
