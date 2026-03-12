from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "build_pic_readiness_scorecard.py"
    spec = importlib.util.spec_from_file_location("build_pic_readiness_scorecard_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_pic_readiness_scorecard_pending_with_preflight_inputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    run_dir = tmp_path / "run_pkg"
    run_dir.mkdir(parents=True, exist_ok=True)
    for name in [
        "foundry_drc_sealed_summary.json",
        "foundry_lvs_sealed_summary.json",
        "foundry_pex_sealed_summary.json",
        "foundry_approval_sealed_summary.json",
    ]:
        (run_dir / name).write_text("{}", encoding="utf-8")

    tapeout = {
        "all_passed": True,
        "checks": [
            {"name": "required_artifacts", "passed": True},
            {
                "name": "foundry_signoff",
                "passed": True,
                "details": {
                    "summaries": [
                        {"path": str(run_dir / "foundry_drc_sealed_summary.json"), "execution_backend": "local_rules"},
                        {"path": str(run_dir / "foundry_lvs_sealed_summary.json"), "execution_backend": "local_lvs"},
                        {"path": str(run_dir / "foundry_pex_sealed_summary.json"), "execution_backend": "local_pex"},
                        {"path": str(run_dir / "foundry_approval_sealed_summary.json"), "execution_backend": "local_rules"},
                    ]
                },
            },
        ],
    }
    gate_b = {
        "overall_gate_b_status": "pending",
        "metrics": {
            "b1_insertion_loss": {"status": "preflight_pass_synthetic"},
            "b2_resonance_alignment": {"status": "preflight_pass_synthetic"},
            "b3_crosstalk": {"status": "preflight_pass_synthetic"},
            "b4_delay_rc": {"status": "preflight_pass_synthetic"},
            "b5_drift": {"status": "pending_silicon_required"},
        },
    }
    gate_cd5 = {
        "status": {"gate_c": "pass"},
        "d5_reproducibility": {"status": "pass"},
        "gate_c": {
            "c1_monte_carlo_yield": {"status": "pass"},
            "c2_multi_corner_closure": {"status": "pass"},
            "c3_perturbation_robustness": {"status": "pass"},
            "c4_netlist_layout_replay": {"status": "pass"},
            "c5_repeatability": {"status": "pass"},
        },
    }
    gate_e = {
        "status": {"overall": "pending"},
        "metrics": {
            "e1_ci_stability": {"status": "preflight_pass_synthetic"},
            "e2_time_to_evidence_sla": {"status": "pass"},
            "e3_failure_triage_quality": {"status": "preflight_pass_synthetic"},
            "e4_claim_governance_matrix": {"status": "pass"},
            "e5_change_control_audit": {"status": "pass"},
        },
    }

    tapeout_path = tmp_path / "tapeout.json"
    gate_b_path = tmp_path / "gate_b.json"
    gate_cd5_path = tmp_path / "gate_cd5.json"
    gate_e_path = tmp_path / "gate_e.json"
    output_path = tmp_path / "scorecard.json"

    _write_json(tapeout_path, tapeout)
    _write_json(gate_b_path, gate_b)
    _write_json(gate_cd5_path, gate_cd5)
    _write_json(gate_e_path, gate_e)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_readiness_scorecard.py",
            "--tapeout-gate",
            str(tapeout_path),
            "--gate-b",
            str(gate_b_path),
            "--gate-cd5",
            str(gate_cd5_path),
            "--gate-e",
            str(gate_e_path),
            "--output",
            str(output_path),
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())
    assert Path(printed["scorecard"]).exists()
    assert printed["declaration_95_allowed"] is False
    assert printed["hold"] is False

    packet = json.loads(output_path.read_text(encoding="utf-8"))
    assert packet["score"]["weighted_score_percent"] > 0.0
    assert packet["gates"]["A"]["status"] == "pass"
    assert packet["gates"]["B"]["status"] == "pending"
    assert packet["score"]["declaration_95_allowed"] is False
