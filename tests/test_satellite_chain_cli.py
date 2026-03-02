from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import photonstrust.cli as cli_mod
import photonstrust.pipeline.satellite_chain as satellite_chain_mod


REPO_ROOT = Path(__file__).resolve().parents[1]
BERLIN_CONFIG = REPO_ROOT / "configs" / "satellite" / "eagle1_analog_berlin.yml"


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "photonstrust.cli", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_help_lists_satellite_chain_command() -> None:
    completed = _run_cli(["-h"])
    assert completed.returncode == 0
    assert "satellite-chain" in (completed.stdout or "")


def test_cli_satellite_chain_runs_berlin_config_and_returns_summary(tmp_path: Path) -> None:
    completed = _run_cli([
        "satellite-chain",
        str(BERLIN_CONFIG),
        "--output",
        str(tmp_path / "sat_chain_cli"),
    ])

    assert completed.returncode == 0, (completed.stdout or "") + (completed.stderr or "")
    line = (completed.stdout or "").strip().splitlines()[-1]
    payload = json.loads(line)

    assert "decision" in payload
    assert "key_bits_accumulated" in payload
    assert "mean_key_rate_bps" in payload
    assert "output_path" in payload


def test_cli_satellite_chain_strict_mode_exits_non_zero_on_hold(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run_satellite_chain(*args, **kwargs):
        _ = args, kwargs
        return {
            "decision": "HOLD",
            "certificate": {
                "schema_version": "0.1",
                "kind": "satellite_qkd_chain_certificate",
                "run_id": "fake",
                "generated_at": "2026-03-02T00:00:00+00:00",
                "mission": "fake",
                "ground_station": {
                    "latitude_deg": 52.5,
                    "pic_cert_run_id": None,
                    "eta_chip": 0.65,
                    "eta_ground_terminal": 0.23,
                },
                "pass": {
                    "altitude_km": 600.0,
                    "elevation_min_deg": 15.0,
                    "pass_duration_s": 100.0,
                    "samples_evaluated": 20,
                    "samples_with_positive_key_rate": 0,
                    "key_bits_accumulated": 0.0,
                    "mean_key_rate_bps": 0.0,
                    "peak_key_rate_bps": 0.0,
                    "peak_elevation_deg": 60.0,
                },
                "signoff": {
                    "decision": "HOLD",
                    "key_rate_positive_at_zenith": False,
                    "annual_key_above_1mbit": False,
                },
            },
            "output_path": None,
        }

    monkeypatch.setattr(satellite_chain_mod, "run_satellite_chain", _fake_run_satellite_chain)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "photonstrust",
            "satellite-chain",
            str(BERLIN_CONFIG),
            "--strict",
            "--output",
            "results/test_satellite_chain_strict_hold",
        ],
    )

    with pytest.raises(SystemExit) as excinfo:
        cli_mod.main()
    assert int(excinfo.value.code) == 1
