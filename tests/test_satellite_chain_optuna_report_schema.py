from __future__ import annotations

from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys
from typing import Any

import photonstrust.pipeline.satellite_chain_optuna as optuna_mod
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.workflow.schema import satellite_qkd_chain_optuna_report_schema_path


def _base_config() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "satellite_qkd_chain": {
            "id": "optuna_schema_unit",
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
            value = float(low) + (float(high) - float(low)) * 0.5
            self.params[str(name)] = float(value)
            return float(value)

    class _Study:
        def __init__(self, *, direction: str, sampler: object, study_name: str) -> None:
            _ = direction, sampler, study_name

        def optimize(self, objective, n_trials: int) -> None:
            for number in range(int(n_trials)):
                trial = _Trial(number)
                objective(trial)

    def _create_study(*, direction: str, sampler: object, study_name: str) -> _Study:
        return _Study(direction=direction, sampler=sampler, study_name=study_name)

    module.__version__ = "test-optuna"
    module.samplers = _Samplers()
    module.create_study = _create_study
    return module


def test_optuna_report_validates_against_schema(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fake_optuna = _build_fake_optuna_module()
    monkeypatch.setitem(sys.modules, "optuna", fake_optuna)

    def _fake_run_satellite_chain(config: dict, *, output_dir: Path) -> dict:
        _ = config, output_dir
        return {
            "certificate": {
                "run_id": "run123",
                "annual_estimate": {"key_bits_per_year": 42.0},
            },
            "output_path": str(tmp_path / "trial.json"),
            "key_bits_accumulated": 42.0,
        }

    monkeypatch.setattr(optuna_mod, "run_satellite_chain", _fake_run_satellite_chain)

    payload = optuna_mod.optimize_satellite_chain_config(
        _base_config(),
        output_dir=tmp_path,
        n_trials=2,
        seed=11,
        tracking_mode=None,
    )
    validate_instance(payload, satellite_qkd_chain_optuna_report_schema_path())
