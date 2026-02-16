"""Generate regression baselines for PhotonTrust scenarios."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.config import build_scenarios, load_config
from photonstrust.qkd import compute_sweep


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_path = root / "tests" / "fixtures" / "baselines.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    config_path = root / "configs" / "demo1_default.yml"
    config = load_config(config_path)
    scenarios = build_scenarios(config)

    baselines = []
    for scenario in scenarios:
        sweep = compute_sweep(scenario, include_uncertainty=False)
        results = sweep["results"]
        baselines.append(
            {
                "scenario_id": scenario["scenario_id"],
                "band": scenario["band"],
                "distances_km": [r.distance_km for r in results],
                "key_rate_bps": [r.key_rate_bps for r in results],
                "qber": [r.qber_total for r in results],
            }
        )

    output_path.write_text(json.dumps({"baselines": baselines}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
