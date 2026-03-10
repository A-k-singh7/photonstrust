from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "run_protocol_engine_parity.py"
    spec = importlib.util.spec_from_file_location("run_protocol_engine_parity_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_protocol_engine_parity_script_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()

    monkeypatch.setattr(
        module,
        "run_protocol_engine_parity",
        lambda **kwargs: {
            "primitive": kwargs["primitive"],
            "baseline_engine": kwargs["baseline_engine_id"],
            "baseline_available": True,
            "violations": [],
            "engine_results": [],
            "summary": {"violations_total": 0, "status_counts": {"ok": 2}},
        },
    )
    explicit_json = tmp_path / "explicit" / "parity.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_protocol_engine_parity.py",
            "--output-dir",
            str(tmp_path / "out"),
            "--json-artifact",
            str(explicit_json),
        ],
    )

    assert module.main() == 0
    summary = json.loads(capsys.readouterr().out.strip())
    report_payload = json.loads(Path(summary["report_path"]).read_text(encoding="utf-8"))

    assert summary["ok"] is True
    assert report_payload["status"] == "ok"
    assert explicit_json.exists()


def test_run_protocol_engine_parity_script_strict_fails_on_baseline_or_violation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()

    monkeypatch.setattr(
        module,
        "run_protocol_engine_parity",
        lambda **kwargs: {
            "primitive": kwargs["primitive"],
            "baseline_engine": kwargs["baseline_engine_id"],
            "baseline_available": False,
            "violations": [{"metric": "success_probability"}],
            "engine_results": [],
            "summary": {"violations_total": 1, "status_counts": {"unavailable": 1}},
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_protocol_engine_parity.py",
            "--strict",
            "--output-dir",
            str(tmp_path / "strict_out"),
        ],
    )

    assert module.main() == 1
    summary = json.loads(capsys.readouterr().out.strip())
    assert summary["ok"] is False
    assert summary["strict_mode"] is True
    assert summary["baseline_available"] is False
    assert summary["violations_total"] == 1
