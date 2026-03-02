"""Optuna-based parameter search for satellite-chain scenarios."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from photonstrust.pipeline.satellite_chain import run_satellite_chain


def optimize_satellite_chain_config(
    config: dict[str, Any],
    *,
    output_dir: Path | str,
    n_trials: int = 20,
    seed: int = 42,
    study_name: str = "satellite_chain_optuna",
) -> dict[str, Any]:
    """Run Optuna optimization for a single satellite-chain config template."""

    try:
        import optuna
    except Exception as exc:
        raise RuntimeError("optuna is required. Install with `.[optuna]`.") from exc

    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    sat_cfg = config.get("satellite_qkd_chain")
    if not isinstance(sat_cfg, dict):
        raise ValueError("config.satellite_qkd_chain is required")

    out_root = Path(output_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    n = max(1, int(n_trials))

    sampler = optuna.samplers.TPESampler(seed=int(seed))
    study = optuna.create_study(direction="maximize", sampler=sampler, study_name=str(study_name))

    def _objective(trial) -> float:
        candidate = _suggest_candidate_config(config, trial)
        trial_dir = out_root / f"trial_{trial.number:04d}"
        result = run_satellite_chain(candidate, output_dir=trial_dir)
        cert = result.get("certificate") if isinstance(result.get("certificate"), dict) else {}
        annual = cert.get("annual_estimate") if isinstance(cert.get("annual_estimate"), dict) else {}
        annual_bits = float(annual.get("key_bits_per_year", 0.0) or 0.0)
        if annual_bits <= 0.0:
            annual_bits = float(result.get("key_bits_accumulated", 0.0) or 0.0)
        return float(annual_bits)

    study.optimize(_objective, n_trials=n)

    top_trials = []
    for trial in sorted(study.trials, key=lambda row: float(row.value or 0.0), reverse=True)[:5]:
        top_trials.append(
            {
                "trial": int(trial.number),
                "value": float(trial.value or 0.0),
                "params": dict(trial.params),
            }
        )

    payload = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_optuna_report",
        "study_name": str(study_name),
        "trial_count": int(len(study.trials)),
        "best_value": float(study.best_value),
        "best_params": dict(study.best_params),
        "top_trials": top_trials,
    }

    report_path = out_root / "satellite_chain_optuna_report.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload


def _suggest_candidate_config(config: dict[str, Any], trial: Any) -> dict[str, Any]:
    candidate = copy.deepcopy(config)
    sat = candidate.setdefault("satellite_qkd_chain", {})
    atmosphere = sat.setdefault("atmosphere", {})
    ground = sat.setdefault("ground_station", {})

    atmosphere["extinction_db_per_km"] = trial.suggest_float("extinction_db_per_km", 0.01, 0.20)
    atmosphere["pointing_jitter_urad"] = trial.suggest_float("pointing_jitter_urad", 0.5, 5.0)
    atmosphere["turbulence_scintillation_index"] = trial.suggest_float("turbulence_scintillation_index", 0.05, 0.40)
    ground["fibre_coupling_efficiency"] = trial.suggest_float("fibre_coupling_efficiency", 0.20, 0.90)
    ground["detector_pde"] = trial.suggest_float("detector_pde", 0.10, 0.95)
    return candidate

