from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "run_satellite_chain_sweep.py"
    spec = importlib.util.spec_from_file_location("run_satellite_chain_sweep_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_satellite_chain_sweep_script_main_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    cfg_path = tmp_path / "scenario.yml"
    cfg_path.write_text("schema_version: '0.1'\nsatellite_qkd_chain: {}\n", encoding="utf-8")
    observed: dict[str, object] = {}

    def _fake_run_sweep(
        configs,
        *,
        output_root: Path,
        backend: str,
        max_workers: int,
        seed: int,
        job_timeout_s: float | None,
        max_retries: int,
        ray_num_cpus: float,
        ray_memory_mb: float | None,
        ray_max_in_flight: int | None,
        tracking_mode: str | None,
        tracking_uri: str | None,
    ) -> dict:
        observed["configs"] = list(configs)
        observed["output_root"] = Path(output_root)
        observed["backend"] = backend
        observed["max_workers"] = int(max_workers)
        observed["seed"] = int(seed)
        observed["job_timeout_s"] = job_timeout_s
        observed["max_retries"] = int(max_retries)
        observed["ray_num_cpus"] = float(ray_num_cpus)
        observed["ray_memory_mb"] = ray_memory_mb
        observed["ray_max_in_flight"] = ray_max_in_flight
        observed["tracking_mode"] = tracking_mode
        observed["tracking_uri"] = tracking_uri
        return {
            "summary": {
                "backend": backend,
                "seed": seed,
                "run_count": 1,
                "decision_counts": {"GO": 1, "HOLD": 0},
                "error_count": 0,
                "key_bits_total": 10.0,
                "mean_key_rate_bps_avg": 2.0,
                "status": "ok",
            },
            "lineage": {"input_order_fingerprint": "abc123"},
            "report_path": str(Path(output_root) / "satellite_chain_sweep.json"),
        }

    monkeypatch.setattr(module, "run_satellite_chain_sweep", _fake_run_sweep)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_satellite_chain_sweep.py",
            str(cfg_path),
            "--output-root",
            str(tmp_path / "out"),
            "--backend",
            "local",
            "--max-workers",
            "2",
            "--seed",
            "9",
            "--job-timeout-s",
            "120",
            "--max-retries",
            "3",
            "--ray-num-cpus",
            "1.5",
            "--tracking-mode",
            "local_json",
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["backend"] == "local"
    assert payload["report_path"].endswith("satellite_chain_sweep.json")
    assert payload["input_order_fingerprint"] == "abc123"
    assert observed["max_retries"] == 3
    assert observed["job_timeout_s"] == pytest.approx(120.0)


def test_run_satellite_chain_sweep_script_main_failure_returns_nonzero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()

    def _fail_run_sweep(*args, **kwargs):  # noqa: ANN002,ANN003
        _ = args, kwargs
        raise RuntimeError("broken sweep")

    monkeypatch.setattr(module, "run_satellite_chain_sweep", _fail_run_sweep)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_satellite_chain_sweep.py",
            "--output-root",
            str(tmp_path / "out"),
        ],
    )

    assert module.main() == 2
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert str(payload["error"]).startswith("satellite_chain_sweep_failed: broken sweep")
