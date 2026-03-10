from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "replay_satellite_chain_reports.py"
    spec = importlib.util.spec_from_file_location("replay_satellite_chain_reports_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_replay_satellite_chain_reports_main_success(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()

    sweep_rows = [
        {
            "row_index": 0,
            "mission_id": "alpha",
            "config_path": "configs/a.yml",
            "config_hash": "a" * 64,
            "decision": "GO",
            "key_bits_accumulated": 1.0,
            "mean_key_rate_bps": 1.0,
            "output_path": "out/a.json",
            "seed": 7,
            "status": "ok",
            "attempts": 1,
        }
    ]
    sweep_input = [
        {
            "row_index": 0,
            "mission_id": "alpha",
            "config_path": "configs/a.yml",
            "config_hash": "a" * 64,
        }
    ]
    sweep_payload = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_sweep",
        "generated_at": "2026-03-02T00:00:00Z",
        "summary": {
            "run_count": 1,
            "decision_counts": {"GO": 1, "HOLD": 0},
            "error_count": 0,
            "key_bits_total": 1.0,
            "mean_key_rate_bps_avg": 1.0,
            "backend": "local",
            "seed": 42,
            "status": "ok",
        },
        "runs": sweep_rows,
        "lineage": {
            "seed": 42,
            "seed_source": "x",
            "seed_strategy": "x",
            "input_order_fingerprint": _fingerprint(sweep_input),
            "backend_metadata": {"name": "local", "version": "threadpool", "python_version": "3.12"},
            "execution_policy": {
                "job_timeout_s": 600.0,
                "max_retries": 1,
                "max_workers": 1,
                "ray_num_cpus": 1.0,
                "ray_memory_mb": None,
                "ray_max_in_flight": None,
                "require_complete_results": True,
            },
        },
    }

    optuna_trials = [
        {
            "trial": 0,
            "value": 9.0,
            "params": {"x": 1.0},
            "seed": 42,
            "state": "COMPLETE",
            "trial_lineage": {
                "trial_id": 0,
                "candidate_config_hash": "b" * 64,
                "result_run_id": "run1",
                "result_output_path": "out/t0.json",
            },
        }
    ]
    optuna_replay_rows = [{"trial": 0, "value": 9.0, "seed": 42, "params": {"x": 1.0}}]
    optuna_payload = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_optuna_report",
        "generated_at": "2026-03-02T00:00:00Z",
        "study_name": "demo",
        "trial_count": 1,
        "best_value": 9.0,
        "best_params": {"x": 1.0},
        "trials": optuna_trials,
        "top_trials": optuna_trials,
        "lineage": {
            "seed": 42,
            "seed_source": "x",
            "seed_strategy": "x",
            "objective_config_hash": "c" * 64,
            "study_metadata": {"direction": "maximize", "sampler": "TPESampler", "optuna_version": "x"},
            "storage": {"enabled": False, "storage_url": "", "resume": False},
            "backend_metadata": {"optimizer": "optuna", "python_version": "3.12"},
            "replay_fingerprint": _fingerprint(optuna_replay_rows),
        },
    }

    sweep_path = tmp_path / "sweep.json"
    optuna_path = tmp_path / "optuna.json"
    sweep_path.write_text(json.dumps(sweep_payload), encoding="utf-8")
    optuna_path.write_text(json.dumps(optuna_payload), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "replay_satellite_chain_reports.py",
            "--sweep-report",
            str(sweep_path),
            "--optuna-report",
            str(optuna_path),
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is True


def test_replay_satellite_chain_reports_detects_fingerprint_mismatch(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    module = _load_script_module()
    sweep_path = tmp_path / "sweep.json"
    optuna_path = tmp_path / "optuna.json"
    sweep_path.write_text(
        json.dumps(
            {
                "lineage": {"input_order_fingerprint": "bad", "seed": 1, "seed_source": "x", "seed_strategy": "x", "backend_metadata": {}, "execution_policy": {}},
                "runs": [{"row_index": 0, "mission_id": "x", "config_path": "x", "config_hash": "x", "seed": 1, "status": "ok", "attempts": 1}],
            }
        ),
        encoding="utf-8",
    )
    optuna_path.write_text(
        json.dumps(
            {
                "lineage": {
                    "replay_fingerprint": "bad",
                    "seed": 1,
                    "seed_source": "x",
                    "seed_strategy": "x",
                    "objective_config_hash": "x",
                    "study_metadata": {},
                    "storage": {},
                    "backend_metadata": {},
                },
                "trials": [
                    {
                        "trial": 0,
                        "value": 1.0,
                        "params": {},
                        "seed": 1,
                        "state": "COMPLETE",
                        "trial_lineage": {
                            "trial_id": 0,
                            "candidate_config_hash": "x",
                            "result_run_id": "",
                            "result_output_path": "",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "replay_satellite_chain_reports.py",
            "--sweep-report",
            str(sweep_path),
            "--optuna-report",
            str(optuna_path),
            "--repro-only",
        ],
    )

    assert module.main() == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
