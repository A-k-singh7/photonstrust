"""Optuna-based parameter search for satellite-chain scenarios."""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.ops.tracking import start_tracking_session
from photonstrust.pipeline.satellite_chain import run_satellite_chain
from photonstrust.utils import hash_dict
from photonstrust.workflow.schema import satellite_qkd_chain_optuna_report_schema_path


def optimize_satellite_chain_config(
    config: dict[str, Any],
    *,
    output_dir: Path | str,
    n_trials: int = 20,
    seed: int = 42,
    study_name: str = "satellite_chain_optuna",
    storage_url: str | None = None,
    resume: bool = False,
    tracking_mode: str | None = "local_json",
    tracking_uri: str | None = None,
) -> dict[str, Any]:
    """Run Optuna optimization for a single satellite-chain config template."""

    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    sat_cfg = config.get("satellite_qkd_chain")
    if not isinstance(sat_cfg, dict):
        raise ValueError("config.satellite_qkd_chain is required")

    if bool(resume) and not str(storage_url or "").strip():
        raise ValueError("resume=true requires storage_url")

    try:
        optuna: Any = importlib.import_module("optuna")
    except Exception as exc:
        raise RuntimeError("optuna is required. Install with `.[optuna]`.") from exc

    out_root = Path(output_dir).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    n = max(1, int(n_trials))
    base_seed = int(seed)
    storage_text = str(storage_url).strip() if storage_url is not None else ""
    storage_value = storage_text if storage_text else None

    sampler = optuna.samplers.TPESampler(seed=base_seed)
    study = _create_study(
        optuna=optuna,
        sampler=sampler,
        study_name=str(study_name),
        storage_url=storage_value,
        resume=bool(resume),
    )

    tracker = _start_tracker(
        tracking_mode=tracking_mode,
        output_dir=out_root,
        tracking_uri=tracking_uri,
        run_id=("optuna_" + hashlib.sha256(f"{study_name}:{base_seed}".encode("utf-8")).hexdigest()[:12]),
    )
    if tracker is not None:
        tracker.log_params(
            {
                "study_name": str(study_name),
                "seed": int(base_seed),
                "n_trials": int(n),
                "storage_enabled": bool(storage_value),
                "resume": bool(resume),
            }
        )

    trial_records: list[dict[str, Any]] = []
    if hasattr(study, "ask") and hasattr(study, "tell"):
        _run_with_ask_tell(
            study=study,
            config=config,
            out_root=out_root,
            base_seed=base_seed,
            n_trials=n,
            trial_records=trial_records,
            tracker=tracker,
        )
    else:
        _run_with_optimize(
            study=study,
            config=config,
            out_root=out_root,
            base_seed=base_seed,
            n_trials=n,
            trial_records=trial_records,
            tracker=tracker,
        )

    if not trial_records:
        if tracker is not None:
            tracker.finalize(status="failed")
        raise RuntimeError("optuna produced zero completed trials")

    sorted_trials = sorted(
        trial_records,
        key=lambda row: (-float(row.get("value", 0.0) or 0.0), int(row.get("trial", 0) or 0)),
    )
    best_trial = sorted_trials[0]
    best_value = float(best_trial.get("value", 0.0) or 0.0)
    best_params_raw = best_trial.get("params")
    best_params = dict(best_params_raw) if isinstance(best_params_raw, dict) else {}

    top_trials = []
    trials_payload: list[dict[str, Any]] = []
    for trial in sorted_trials:
        row = {
            "trial": int(trial.get("trial", 0) or 0),
            "value": float(trial.get("value", 0.0) or 0.0),
            "params": dict(trial.get("params") or {}),
            "seed": int(trial.get("seed", 0) or 0),
            "state": str(trial.get("state") or "COMPLETE"),
            "trial_lineage": dict(trial.get("trial_lineage") or {}),
        }
        trials_payload.append(row)
    top_trials = list(trials_payload[:5])

    payload: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_optuna_report",
        "generated_at": _now_iso(),
        "study_name": str(study_name),
        "trial_count": int(len(trial_records)),
        "best_value": float(best_value),
        "best_params": best_params,
        "trials": trials_payload,
        "top_trials": top_trials,
        "lineage": {
            "seed": int(base_seed),
            "seed_source": "optimize_satellite_chain_config.seed",
            "seed_strategy": "trial_seed = base_seed + trial_number",
            "objective_config_hash": hash_dict(config),
            "study_metadata": {
                "direction": "maximize",
                "sampler": str(type(sampler).__name__),
                "optuna_version": str(getattr(optuna, "__version__", "unknown")),
            },
            "storage": {
                "enabled": bool(storage_value),
                "storage_url": str(storage_value or ""),
                "resume": bool(resume),
            },
            "backend_metadata": {
                "optimizer": "optuna",
                "python_version": str(sys.version.split()[0]),
            },
            "replay_fingerprint": _replay_fingerprint(sorted_trials),
        },
    }

    if tracker is not None:
        payload["lineage"]["tracking"] = {
            "mode": str(tracker.mode),
            "run_id": str(tracker.run_id),
            "tracking_uri": str(tracker.tracking_uri or ""),
        }

    _validate_optuna_report_schema_if_available(payload)

    report_path = out_root / "satellite_chain_optuna_report.json"
    report_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    if tracker is not None:
        tracker.log_metrics(
            {
                "best_value": float(best_value),
                "trial_count": float(len(trial_records)),
            },
            step=0,
        )
        tracker.log_artifact(report_path, name="satellite_chain_optuna_report.json")
        tracker.finalize(status="finished")

    payload["report_path"] = str(report_path)
    return payload


def _run_with_ask_tell(
    *,
    study: Any,
    config: dict[str, Any],
    out_root: Path,
    base_seed: int,
    n_trials: int,
    trial_records: list[dict[str, Any]],
    tracker: Any,
) -> None:
    for _ in range(int(n_trials)):
        trial = study.ask()
        trial_row = _evaluate_trial(
            trial=trial,
            config=config,
            out_root=out_root,
            base_seed=base_seed,
        )
        study.tell(trial, float(trial_row["value"]))
        trial_records.append(trial_row)
        if tracker is not None:
            tracker.log_metrics(
                {
                    "trial_value": float(trial_row["value"]),
                },
                step=int(trial_row["trial"]),
            )


def _run_with_optimize(
    *,
    study: Any,
    config: dict[str, Any],
    out_root: Path,
    base_seed: int,
    n_trials: int,
    trial_records: list[dict[str, Any]],
    tracker: Any,
) -> None:
    def _objective(trial: Any) -> float:
        trial_row = _evaluate_trial(
            trial=trial,
            config=config,
            out_root=out_root,
            base_seed=base_seed,
        )
        trial_records.append(trial_row)
        if tracker is not None:
            tracker.log_metrics(
                {
                    "trial_value": float(trial_row["value"]),
                },
                step=int(trial_row["trial"]),
            )
        return float(trial_row["value"])

    study.optimize(_objective, n_trials=int(n_trials))


def _evaluate_trial(
    *,
    trial: Any,
    config: dict[str, Any],
    out_root: Path,
    base_seed: int,
) -> dict[str, Any]:
    trial_number = int(getattr(trial, "number", 0) or 0)
    trial_seed = _trial_seed(base_seed=int(base_seed), trial_number=trial_number)
    candidate = _suggest_candidate_config(config, trial)
    candidate = _inject_runtime_seed(candidate, seed=trial_seed)
    trial_dir = out_root / f"trial_{trial_number:04d}"
    result = run_satellite_chain(candidate, output_dir=trial_dir)

    cert_raw = result.get("certificate")
    cert = cert_raw if isinstance(cert_raw, dict) else {}
    annual_raw = cert.get("annual_estimate")
    annual = annual_raw if isinstance(annual_raw, dict) else {}
    annual_bits = float(annual.get("key_bits_per_year", 0.0) or 0.0)
    if annual_bits <= 0.0:
        annual_bits = float(result.get("key_bits_accumulated", 0.0) or 0.0)
    if not math.isfinite(annual_bits):
        raise RuntimeError(f"trial {trial_number} produced non-finite objective value")

    params_raw = getattr(trial, "params", {})
    params = dict(params_raw) if isinstance(params_raw, dict) else {}
    trial_lineage = {
        "trial_id": int(getattr(trial, "_trial_id", trial_number) or trial_number),
        "candidate_config_hash": hash_dict(candidate),
        "result_run_id": str(cert.get("run_id") or ""),
        "result_output_path": str(result.get("output_path") or ""),
    }

    if hasattr(trial, "set_user_attr"):
        trial.set_user_attr("trial_seed", int(trial_seed))
        trial.set_user_attr("trial_output_dir", str(trial_dir))
        trial.set_user_attr("trial_lineage", dict(trial_lineage))

    return {
        "trial": int(trial_number),
        "value": float(annual_bits),
        "params": params,
        "seed": int(trial_seed),
        "state": "COMPLETE",
        "trial_lineage": trial_lineage,
    }


def _create_study(
    *,
    optuna: Any,
    sampler: Any,
    study_name: str,
    storage_url: str | None,
    resume: bool,
) -> Any:
    kwargs: dict[str, Any] = {
        "direction": "maximize",
        "sampler": sampler,
        "study_name": str(study_name),
    }
    if storage_url is not None:
        kwargs["storage"] = str(storage_url)
    if bool(resume):
        kwargs["load_if_exists"] = True

    try:
        return optuna.create_study(**kwargs)
    except TypeError as exc:
        if storage_url is not None or bool(resume):
            raise RuntimeError(
                "configured optuna storage/resume is unsupported by installed optuna version"
            ) from exc
        return optuna.create_study(
            direction="maximize",
            sampler=sampler,
            study_name=str(study_name),
        )


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


def _inject_runtime_seed(config: dict[str, Any], *, seed: int) -> dict[str, Any]:
    payload = copy.deepcopy(config)
    sat_raw = payload.get("satellite_qkd_chain")
    if isinstance(sat_raw, dict):
        sat = sat_raw
    else:
        sat = {}
        payload["satellite_qkd_chain"] = sat

    runtime_raw = sat.get("runtime")
    if isinstance(runtime_raw, dict):
        runtime = runtime_raw
    else:
        runtime = {}
        sat["runtime"] = runtime

    runtime["rng_seed"] = int(seed)
    return payload


def _trial_seed(*, base_seed: int, trial_number: int) -> int:
    return int(base_seed) + int(trial_number)


def _replay_fingerprint(trials: list[dict[str, Any]]) -> str:
    rows = [
        {
            "trial": int(row.get("trial", 0) or 0),
            "value": float(row.get("value", 0.0) or 0.0),
            "seed": int(row.get("seed", 0) or 0),
            "params": dict(row.get("params") or {}),
        }
        for row in trials
    ]
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _start_tracker(
    *,
    tracking_mode: str | None,
    output_dir: Path,
    tracking_uri: str | None,
    run_id: str,
) -> Any:
    mode = str(tracking_mode or "").strip().lower()
    if not mode or mode == "none":
        return None
    return start_tracking_session(
        mode=mode,
        output_dir=output_dir / "tracking",
        run_id=str(run_id),
        tracking_uri=tracking_uri,
    )


def _validate_optuna_report_schema_if_available(report: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return

    schema_path = satellite_qkd_chain_optuna_report_schema_path()
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
