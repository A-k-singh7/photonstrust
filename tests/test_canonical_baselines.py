from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep
from photonstrust.validation import validate_scenarios_or_raise


def test_canonical_configs_validate() -> None:
    root = Path(__file__).resolve().parents[1]
    canonical_dir = root / "configs" / "canonical"
    paths = sorted(canonical_dir.glob("phase41_*.yml"))
    assert paths, "Expected Phase 41 canonical configs"

    for p in paths:
        cfg = load_config(p)
        scenarios = build_scenarios(cfg)
        validate_scenarios_or_raise(scenarios)


def test_canonical_baselines_match_fixture() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture = root / "tests" / "fixtures" / "canonical_phase41_baselines.json"
    assert fixture.exists(), "Missing baseline fixture. Run scripts/generate_phase41_canonical_baselines.py"

    data = json.loads(fixture.read_text(encoding="utf-8"))
    assert data.get("schema_version") == "0.1"
    configs = data.get("configs") or []
    assert isinstance(configs, list) and configs

    for entry in configs:
        rel = str(entry.get("config_relpath") or "")
        assert rel
        cfg_path = root / Path(rel)
        assert cfg_path.exists(), f"Config missing: {rel}"

        cfg = load_config(cfg_path)
        scenarios = build_scenarios(cfg)
        validate_scenarios_or_raise(scenarios)

        expected_list = entry.get("baselines") or []
        assert isinstance(expected_list, list) and expected_list

        expected_by_key = {(e["scenario_id"], e["band"]): e for e in expected_list}
        for scenario in scenarios:
            key = (scenario["scenario_id"], scenario["band"])
            assert key in expected_by_key
            expected = expected_by_key[key]

            sweep = compute_sweep(scenario, include_uncertainty=False)
            results = sweep["results"]
            obs_key = [float(r.key_rate_bps) for r in results]
            obs_qber = [float(r.qber_total) for r in results]
            obs_raman = [float(r.raman_counts_cps) for r in results]

            assert len(obs_key) == len(expected["key_rate_bps"])
            assert len(obs_qber) == len(expected["qber"])

            for obs, exp in zip(obs_key, expected["key_rate_bps"]):
                assert obs == pytest.approx(float(exp), rel=1e-6, abs=1e-12)
            for obs, exp in zip(obs_qber, expected["qber"]):
                assert obs == pytest.approx(float(exp), rel=1e-6, abs=1e-12)
            for obs, exp in zip(obs_raman, expected.get("raman_counts_cps") or [0.0] * len(obs_raman)):
                assert obs == pytest.approx(float(exp), rel=1e-6, abs=1e-12)
