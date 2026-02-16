"""Source benchmarking scenario."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.physics import get_emitter_stats
from photonstrust.qkd import compute_point


def run_source_benchmark(config: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario = config["source_benchmark"]
    source_cfg = scenario["source"]
    link_cfg = scenario["link_scenario"]

    stats = get_emitter_stats(source_cfg)
    link_cfg = {**link_cfg, "source": {**link_cfg["source"], **source_cfg}}
    projection = compute_point(link_cfg, scenario.get("distance_km", 0.0))

    result = {
        "g2_0": stats["g2_0"],
        "p_multi": stats["p_multi"],
        "emission_prob": stats["emission_prob"],
        "projected_key_rate_bps": projection.key_rate_bps,
        "projected_fidelity": projection.fidelity,
    }
    _write_results(output_dir / "results.json", result)
    return result


def _write_results(path: Path, result: dict) -> None:
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
