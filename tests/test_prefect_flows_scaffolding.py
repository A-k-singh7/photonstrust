from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from photonstrust.ops import prefect_flows


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "run_prefect_flow.py"
    spec = importlib.util.spec_from_file_location("run_prefect_flow_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_nightly_flow_local_mode_success_writes_deterministic_artifact(tmp_path: Path) -> None:
    output_dir = tmp_path / "nightly_local"
    result = prefect_flows.run_nightly_flow(
        flow="satellite",
        output_dir=output_dir,
        config=None,
        mode="local",
    )

    assert result["status"] == "ok"
    assert result["flow_name"] == "nightly_satellite"
    assert result["generated_at"] == "2026-03-02T00:00:00Z"
    artifact_path = Path(result["artifact_paths"]["summary_json"])
    assert artifact_path.exists()
    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert artifact_payload["flow_name"] == "nightly_satellite"
    assert artifact_payload["generated_at"] == "2026-03-02T00:00:00Z"


def test_run_prefect_flow_script_prefect_mode_missing_dependency_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    monkeypatch.setattr(prefect_flows, "PREFECT_AVAILABLE", False)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_prefect_flow.py",
            "--flow",
            "corner",
            "--output-dir",
            str(tmp_path / "prefect_missing"),
            "--mode",
            "prefect",
        ],
    )

    assert module.main() == 2
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["mode"] == "prefect"
    assert "Prefect mode requested but Prefect is not installed" in str(payload["error"])
