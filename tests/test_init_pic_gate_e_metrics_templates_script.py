from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "init_pic_gate_e_metrics_templates.py"
    spec = importlib.util.spec_from_file_location("init_pic_gate_e_metrics_templates_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_init_pic_gate_e_metrics_templates_writes_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    out_dir = tmp_path / "governance"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "init_pic_gate_e_metrics_templates.py",
            "--output-dir",
            str(out_dir),
            "--release-candidate",
            "rc_test",
            "--force",
        ],
    )

    assert module.main() == 0
    printed = json.loads(capsys.readouterr().out.strip())

    manifest_path = Path(printed["manifest"])
    ci_path = Path(printed["ci_history_metrics"])
    triage_path = Path(printed["triage_metrics"])
    assert manifest_path.exists()
    assert ci_path.exists()
    assert triage_path.exists()

    ci_payload = json.loads(ci_path.read_text(encoding="utf-8"))
    triage_payload = json.loads(triage_path.read_text(encoding="utf-8"))
    assert ci_payload["synthetic"] is True
    assert triage_payload["synthetic"] is True
    assert float(ci_payload["metrics"]["pass_rate_percent"]) > 0.0
    assert float(triage_payload["mean_time_to_root_cause_hours"]) > 0.0
