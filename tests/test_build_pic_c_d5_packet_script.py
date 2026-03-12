from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "build_pic_c_d5_packet.py"
    spec = importlib.util.spec_from_file_location("build_pic_c_d5_packet_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_build_pic_c_d5_packet_passes_with_consistent_inputs(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    corner_report = {
        "monte_carlo": {"yield_fraction_above_threshold": 1.0, "completed_samples": 20},
        "risk_assessment": {"worst_case_key_rate_bps": 90.0},
        "nominal": {"key_rate_bps": 100.0},
        "corners": {
            "selected": ["SS", "TT", "FF"],
            "evaluated": [
                {"corner": "SS", "status": "ok"},
                {"corner": "TT", "status": "ok"},
                {"corner": "FF", "status": "ok"},
            ],
        },
    }
    tapeout_gate = {
        "all_passed": True,
        "checks": [{"name": "foundry_signoff", "passed": True}],
    }
    decision_a = {"decision": "GO", "tapeout_all_passed": True, "smoke_overall_status": "pass"}
    decision_b = {"decision": "GO", "tapeout_all_passed": True, "smoke_overall_status": "pass"}

    corner_path = tmp_path / "corner.json"
    gate_path = tmp_path / "gate.json"
    decision_a_path = tmp_path / "decision_a.json"
    decision_b_path = tmp_path / "decision_b.json"
    output_path = tmp_path / "packet.json"

    _write_json(corner_path, corner_report)
    _write_json(gate_path, tapeout_gate)
    _write_json(decision_a_path, decision_a)
    _write_json(decision_b_path, decision_b)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_pic_c_d5_packet.py",
            "--corner-report",
            str(corner_path),
            "--no-run-corner-demo",
            "--tapeout-gate-report",
            str(gate_path),
            "--decision-packet",
            str(decision_a_path),
            "--decision-packet",
            str(decision_b_path),
            "--output",
            str(output_path),
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert Path(payload["packet"]).exists()
    assert payload["overall"] == "pass"

    packet = json.loads(output_path.read_text(encoding="utf-8"))
    assert packet["status"]["gate_c"] == "pass"
    assert packet["status"]["d5"] == "pass"
    assert packet["status"]["overall"] == "pass"
