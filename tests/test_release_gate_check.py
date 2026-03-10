from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "release_gate_check.py"
    spec = importlib.util.spec_from_file_location("release_gate_check_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_gate_check_quick_mode_writes_report(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    report_path = tmp_path / "release_gate_report.json"

    def _ok_run(cmd, *, timeout_s=None):  # noqa: ANN001
        _ = cmd, timeout_s
        return True, "ok"

    monkeypatch.setattr(module, "_run", _ok_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release_gate_check.py",
            "--quick",
            "--output",
            str(report_path),
        ],
    )

    assert module.main() == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["pass"] is True
    names = {row["name"] for row in payload["checks"]}
    assert "lineage_gate" in names
    assert "repro_gate" in names


def test_release_gate_check_returns_nonzero_on_failed_check(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = _load_script_module()
    report_path = tmp_path / "release_gate_report.json"

    def _mixed_run(cmd, *, timeout_s=None):  # noqa: ANN001
        _ = timeout_s
        if "replay_satellite_chain_reports.py" in " ".join(str(part) for part in cmd):
            return False, "failed"
        return True, "ok"

    monkeypatch.setattr(module, "_run", _mixed_run)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "release_gate_check.py",
            "--quick",
            "--output",
            str(report_path),
        ],
    )

    assert module.main() == 1
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["pass"] is False
