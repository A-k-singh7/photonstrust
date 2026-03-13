from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


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
        storage_url: str | None = None,
        resume: bool = False,
        tracking_mode: str | None = "local_json",
        tracking_uri: str | None = None,
    ) -> dict:
        observed["config"] = dict(config)
        observed["output_dir"] = Path(output_dir)
        observed["n_trials"] = int(n_trials)
        observed["seed"] = int(seed)
        observed["study_name"] = str(study_name)
        observed["storage_url"] = storage_url
        observed["resume"] = bool(resume)
        observed["tracking_mode"] = tracking_mode
        observed["tracking_uri"] = tracking_uri
        return {
            "kind": "satellite_qkd_chain_optuna_report",
            "study_name": str(study_name),
            "trial_count": int(n_trials),
            "best_value": 1234.5,
            "report_path": str(Path(output_dir) / "satellite_chain_optuna_report.json"),
            "lineage": {
                "storage": {
                    "enabled": bool(storage_url),
                    "resume": bool(resume),
                }
            },
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
        "resume": False,
        "storage_enabled": False,
        "study_name": "cli_unit_study",
        "trial_count": 5,
    }
    assert observed["config_path"] == config_path.resolve()
    assert observed["output_dir"] == output_dir.resolve()
    assert observed["n_trials"] == 5
    assert observed["seed"] == 9
    assert observed["study_name"] == "cli_unit_study"
    assert observed["tracking_mode"] == "local_json"
    assert observed["resume"] is False


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


def test_run_satellite_chain_optuna_script_forwards_storage_and_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    config_path = tmp_path / "scenario.yml"
    config_path.write_text("schema_version: '0.1'\nsatellite_qkd_chain: {}\n", encoding="utf-8")
    seen: dict[str, object] = {}

    def _fake_load_config(path: Path) -> dict:
        _ = path
        return {"schema_version": "0.1", "satellite_qkd_chain": {}}

    def _fake_optimize(config: dict, **kwargs):  # noqa: ANN003
        _ = config
        seen.update(kwargs)
        return {
            "best_value": 1.0,
            "report_path": str(tmp_path / "out" / "satellite_chain_optuna_report.json"),
            "study_name": "resume_study",
            "trial_count": 2,
            "lineage": {"storage": {"enabled": True, "resume": True}},
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
            str(tmp_path / "out"),
            "--storage-url",
            "sqlite:///tmp_optuna.db",
            "--resume",
            "--tracking-mode",
            "none",
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["storage_enabled"] is True
    assert payload["resume"] is True
    assert seen["storage_url"] == "sqlite:///tmp_optuna.db"
    assert seen["resume"] is True
    assert seen["tracking_mode"] is None
