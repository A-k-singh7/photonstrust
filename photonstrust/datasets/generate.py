"""Dataset generator for benchmark scenarios."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import argparse

from photonstrust.config import build_scenarios, load_config
from photonstrust.optimize import run_optimization
from photonstrust.repeater import run_repeater_optimization
from photonstrust.scenarios import run_source_benchmark, run_teleportation
from photonstrust.sweep import run_scenarios


def generate_dataset(config_path: Path, output_dir: Path) -> Path:
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if "repeater_optimization" in config:
        results = run_repeater_optimization(config, output_dir)
    elif "teleportation" in config:
        results = run_teleportation(config, output_dir)
    elif "source_benchmark" in config:
        results = run_source_benchmark(config, output_dir)
    elif "optimization" in config:
        results = run_optimization(config, output_dir)
    else:
        scenarios = build_scenarios(config)
        results = run_scenarios(scenarios, output_dir)

    entry = {
        "scenario_id": _scenario_id(config),
        "config": config,
        "results": results,
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "seed": _config_seed(config),
            "version": "0.1.0",
        },
    }

    output_path = output_dir / "dataset_entry.json"
    output_path.write_text(json.dumps(entry, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate PhotonTrust dataset entry")
    parser.add_argument("config", type=Path, help="Scenario config file")
    parser.add_argument("output", type=Path, help="Output directory")
    args = parser.parse_args()
    generate_dataset(args.config, args.output)


def _scenario_id(config: dict) -> str:
    if "scenario" in config:
        return config["scenario"]["id"]
    if "repeater_optimization" in config:
        return config["repeater_optimization"]["id"]
    if "teleportation" in config:
        return config["teleportation"]["id"]
    if "source_benchmark" in config:
        return config["source_benchmark"]["id"]
    if "optimization" in config:
        return config["optimization"]["id"]
    if "calibration" in config:
        return config["calibration"]["id"]
    return "unknown"


def _config_seed(config: dict) -> int:
    if "scenario" in config:
        return int(config["scenario"].get("seed", 0))
    if "teleportation" in config:
        return int(config["teleportation"].get("seed", 0))
    if "source_benchmark" in config:
        return int(config["source_benchmark"].get("seed", 0))
    if "repeater_optimization" in config:
        return int(config["repeater_optimization"].get("seed", 0))
    if "optimization" in config:
        return int(config["optimization"].get("seed", 0))
    if "calibration" in config:
        return int(config["calibration"].get("seed", 0))
    return 0


if __name__ == "__main__":
    main()
