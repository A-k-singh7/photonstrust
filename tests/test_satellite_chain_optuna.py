from __future__ import annotations

import builtins
import json
from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
from typing import Any

import pytest

import photonstrust.pipeline.satellite_chain_optuna as optuna_mod


def _base_config() -> dict:
    return {
        "schema_version": "0.1",
        "satellite_qkd_chain": {
            "id": "optuna_unit",
            "atmosphere": {},
            "ground_station": {},
        },
    }


def _build_fake_optuna_module() -> ModuleType:
    module: Any = ModuleType("optuna")

    class _TPESampler:
        def __init__(self, *, seed: int) -> None:
            self.seed = int(seed)

    class _Samplers:
        TPESampler = _TPESampler

    class _Trial:
        def __init__(self, number: int) -> None:
            self.number = int(number)
            self.params: dict[str, float] = {}

        def suggest_float(self, name: str, low: float, high: float) -> float:
            ratio = min(1.0, 0.2 * float(self.number + 1))
            value = float(low) + (float(high) - float(low)) * ratio
            self.params[str(name)] = float(value)
            return float(value)

    class _Study:
        def __init__(self, *, direction: str, sampler: object, study_name: str) -> None:
            self.direction = str(direction)
            self.sampler = sampler
            self.study_name = str(study_name)
            self.trials: list[SimpleNamespace] = []
            self.best_value: float = 0.0
            self.best_params: dict[str, float] = {}

        def optimize(self, objective, n_trials: int) -> None:
            for number in range(int(n_trials)):
                trial = _Trial(number)
                value = float(objective(trial))
                self.trials.append(
                    SimpleNamespace(number=int(number), value=float(value), params=dict(trial.params))
                )

            if self.trials:
                best = max(self.trials, key=lambda row: float(row.value))
                self.best_value = float(best.value)
                self.best_params = dict(best.params)

    def _create_study(*, direction: str, sampler: object, study_name: str) -> _Study:
        return _Study(direction=direction, sampler=sampler, study_name=study_name)

    module.samplers = _Samplers()
    module.create_study = _create_study
    return module


def test_optimize_satellite_chain_config_with_fake_optuna_writes_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_optuna = _build_fake_optuna_module()
    monkeypatch.setitem(sys.modules, "optuna", fake_optuna)

    def _fake_run_satellite_chain(config: dict, *, output_dir: Path) -> dict:
        _ = output_dir
        sat_raw = config.get("satellite_qkd_chain") if isinstance(config, dict) else None
        sat_cfg = sat_raw if isinstance(sat_raw, dict) else {}
        atmosphere_raw = sat_cfg.get("atmosphere")
        atmosphere = atmosphere_raw if isinstance(atmosphere_raw, dict) else {}
        ground_raw = sat_cfg.get("ground_station")
        ground = ground_raw if isinstance(ground_raw, dict) else {}
        detector = float(ground.get("detector_pde", 0.0) or 0.0)
        coupling = float(ground.get("fibre_coupling_efficiency", 0.0) or 0.0)
        jitter = float(atmosphere.get("pointing_jitter_urad", 0.0) or 0.0)
        annual_bits = max(0.0, detector * 1_000_000.0 + coupling * 100_000.0 - jitter * 1_000.0)
        return {"certificate": {"annual_estimate": {"key_bits_per_year": annual_bits}}}

    monkeypatch.setattr(optuna_mod, "run_satellite_chain", _fake_run_satellite_chain)

    payload = optuna_mod.optimize_satellite_chain_config(
        _base_config(),
        output_dir=tmp_path,
        n_trials=3,
        seed=7,
        study_name="unit_optuna",
    )

    assert payload["kind"] == "satellite_qkd_chain_optuna_report"
    assert payload["study_name"] == "unit_optuna"
    assert payload["trial_count"] == 3
    assert isinstance(payload["best_params"], dict)
    assert len(payload["trials"]) == 3
    assert len(payload["top_trials"]) == 3
    assert payload["lineage"]["seed"] == 7
    assert payload["lineage"]["objective_config_hash"]
    assert payload["lineage"]["study_metadata"]["direction"] == "maximize"
    assert payload["lineage"]["storage"]["enabled"] is False
    assert payload["lineage"]["replay_fingerprint"]
    assert all("seed" in row for row in payload["top_trials"])
    assert all("trial_lineage" in row for row in payload["top_trials"])
    values = [float(row["value"]) for row in payload["top_trials"]]
    assert values == sorted(values, reverse=True)

    report_path = Path(str(payload["report_path"]))
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["kind"] == "satellite_qkd_chain_optuna_report"
    assert report["trial_count"] == 3
    assert report["study_name"] == "unit_optuna"
    assert "report_path" not in report


def test_optimize_satellite_chain_config_without_optuna_raises_runtime_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "optuna", raising=False)
    real_import = builtins.__import__

    def _fake_import(name: str, globals=None, locals=None, fromlist=(), level: int = 0):  # noqa: ANN001
        if name == "optuna":
            raise ImportError("optuna missing for test")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    with pytest.raises(RuntimeError, match="optuna is required"):
        optuna_mod.optimize_satellite_chain_config(_base_config(), output_dir=tmp_path)


def test_optimize_satellite_chain_config_resume_requires_storage(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="resume=true requires storage_url"):
        optuna_mod.optimize_satellite_chain_config(
            _base_config(),
            output_dir=tmp_path,
            resume=True,
        )
