from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    script_path = REPO_ROOT / "scripts" / "run_orbit_provider_parity.py"
    spec = importlib.util.spec_from_file_location("run_orbit_provider_parity_under_test", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_orbit_provider_parity_main_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    cfg_a = tmp_path / "a.yml"
    cfg_b = tmp_path / "b.yml"
    cfg_a.write_text("schema_version: '0.1'\n", encoding="utf-8")
    cfg_b.write_text("schema_version: '0.1'\n", encoding="utf-8")
    output_dir = tmp_path / "parity_out"
    seen_calls: list[dict[str, object]] = []

    def _fake_load_config(path: Path) -> dict:
        path_obj = Path(path)
        if path_obj == cfg_a.resolve():
            return {
                "schema_version": "0.1",
                "satellite_qkd_chain": {
                    "id": "sat_a",
                    "runtime": {"execution_mode": "preview"},
                    "orbit_provider": {"parity": {"include_orekit": True}},
                },
            }
        return {
            "schema_version": "0.1",
            "satellite_qkd_chain": {
                "id": "sat_b",
                "runtime": {"execution_mode": "preview"},
            },
        }

    def _fake_run_provider_parity(*, config: dict, providers: list[str], reference_provider: str | None) -> dict:
        seen_calls.append(
            {
                "config_id": str((config.get("satellite_qkd_chain") or {}).get("id")),
                "providers": list(providers),
                "reference_provider": reference_provider,
            }
        )
        return {
            "providers": list(providers),
            "reference_provider": reference_provider,
            "violations": [],
        }

    monkeypatch.setattr(module, "load_config", _fake_load_config)
    monkeypatch.setattr(module, "run_provider_parity", _fake_run_provider_parity)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_orbit_provider_parity.py",
            str(cfg_a),
            str(cfg_b),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert module.main() == 0
    payload = json.loads(capsys.readouterr().out.strip())
    report_path = Path(str(payload["report_path"]))
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert payload["ok"] is True
    assert payload["configs_total"] == 2
    assert payload["threshold_violations_total"] == 0
    assert payload["status_counts"]["ok"] == 2
    assert report_payload["summary"]["orekit_reference_enabled"] is True
    assert seen_calls[0]["providers"] == ["skyfield", "poliastro"]
    assert seen_calls[0]["reference_provider"] == "orekit"
    assert seen_calls[1]["reference_provider"] is None


def test_run_orbit_provider_parity_main_strict_fails_on_violations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    module = _load_script_module()
    cfg = tmp_path / "strict.yml"
    cfg.write_text("schema_version: '0.1'\n", encoding="utf-8")

    def _fake_load_config(path: Path) -> dict:
        _ = path
        return {
            "schema_version": "0.1",
            "satellite_qkd_chain": {
                "id": "sat_strict",
                "runtime": {"execution_mode": "preview"},
            },
        }

    def _fake_run_provider_parity(*, config: dict, providers: list[str], reference_provider: str | None) -> dict:
        _ = config, providers, reference_provider
        return {
            "violations": [
                {
                    "metric": "pass_duration_s",
                    "delta_kind": "abs",
                    "observed": 3.0,
                    "limit": 1.0,
                }
            ]
        }

    monkeypatch.setattr(module, "load_config", _fake_load_config)
    monkeypatch.setattr(module, "run_provider_parity", _fake_run_provider_parity)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_orbit_provider_parity.py",
            str(cfg),
            "--strict",
            "--output-dir",
            str(tmp_path / "strict_out"),
        ],
    )

    assert module.main() == 1
    payload = json.loads(capsys.readouterr().out.strip())
    assert payload["ok"] is False
    assert payload["strict_mode"] is True
    assert payload["threshold_violations_total"] == 1
    assert payload["status_counts"]["violations"] == 1
