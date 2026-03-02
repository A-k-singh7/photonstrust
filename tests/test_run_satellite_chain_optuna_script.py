from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "run_satellite_chain_optuna.py"
    spec = importlib.util.spec_from_file_location("run_satellite_chain_optuna_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_satellite_chain_optuna_script_main_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    config_path = tmp_path / "scenario.yml"
    config_path.write_text("schema_version: '0.1'\nsatellite_qkd_chain: {}\n", encoding="utf-8")
    output_dir = tmp_path / "optuna_out"
    observed: dict[str, object] = {}

    def _fake_load_config(path: Path) -> dict:
        observed["config_path"] = Path(path)
        return {"schema_version": "0.1", "satellite_qkd_chain": {}}

    def _fake_optimize(
        config: dict,
        *,
        output_dir: Path,
        n_trials: int,
        seed: int,
        study_name: str = "satellite_chain_optuna",
    ) -> dict:
        observed["config"] = dict(config)
        observed["output_dir"] = Path(output_dir)
        observed["n_trials"] = int(n_trials)
        observed["seed"] = int(seed)
        observed["study_name"] = str(study_name)
        return {
            "kind": "satellite_qkd_chain_optuna_report",
            "study_name": str(study_name),
            "trial_count": int(n_trials),
            "best_value": 1234.5,
            "report_path": str(Path(output_dir) / "satellite_chain_optuna_report.json"),
        }

    monkeypatch.setattr(module, "load_config", _fake_load_config)
    monkeypatch.setattr(module, "optimize_satellite_chain_config", _fake_optimize)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_satellite_chain_optuna.py",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--n-trials",
            "5",
            "--seed",
            "9",
            "--study-name",
            "cli_unit_study",
        ],
    )

    assert module.main() == 0
    stdout = capsys.readouterr().out.strip()
    payload = json.loads(stdout)

    assert payload == {
        "best_value": 1234.5,
        "report_path": str(output_dir.resolve() / "satellite_chain_optuna_report.json"),
        "study_name": "cli_unit_study",
        "trial_count": 5,
    }
    assert observed["config_path"] == config_path.resolve()
    assert observed["output_dir"] == output_dir.resolve()
    assert observed["n_trials"] == 5
    assert observed["seed"] == 9
    assert observed["study_name"] == "cli_unit_study"


def test_run_satellite_chain_optuna_script_main_failure_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    config_path = tmp_path / "bad.yml"
    config_path.write_text("schema_version: '0.1'\n", encoding="utf-8")

    def _fail_load_config(path: Path) -> dict:
        _ = path
        raise ValueError("broken config")

    monkeypatch.setattr(module, "load_config", _fail_load_config)
    monkeypatch.setattr(sys, "argv", ["run_satellite_chain_optuna.py", str(config_path)])

    assert module.main() == 2
    stdout = capsys.readouterr().out.strip()
    payload = json.loads(stdout)
    assert payload["ok"] is False
    assert str(payload["error"]).startswith("satellite_chain_optuna_failed: broken config")
