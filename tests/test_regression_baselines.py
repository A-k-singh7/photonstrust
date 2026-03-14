from pathlib import Path

import json
import pytest

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep


def test_regression_baselines():
    root = Path(__file__).resolve().parents[1]
    baseline_path = root / "tests" / "fixtures" / "baselines.json"
    if not baseline_path.exists():
        pytest.skip("Baseline file not present. Run scripts/generate_baselines.py")

    baselines = json.loads(baseline_path.read_text(encoding="utf-8"))["baselines"]
    config = load_config(root / "configs" / "quickstart" / "qkd_default.yml")
    scenarios = build_scenarios(config)

    for scenario in scenarios:
        sweep = compute_sweep(scenario, include_uncertainty=False)
        results = sweep["results"]
        baseline = next(
            entry for entry in baselines if entry["band"] == scenario["band"]
        )
        assert len(results) == len(baseline["key_rate_bps"])
        for result, expected in zip(results, baseline["key_rate_bps"]):
            assert result.key_rate_bps == pytest.approx(expected, rel=1e-6, abs=1e-12)
