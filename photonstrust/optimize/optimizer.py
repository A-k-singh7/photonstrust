"""Optimization routines."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.repeater import run_repeater_optimization


def run_optimization(config: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    optimization = config["optimization"]
    opt_type = optimization.get("type", "repeater_spacing")

    if opt_type == "repeater_spacing":
        results = run_repeater_optimization({"repeater_optimization": optimization}, output_dir)
        best = _select_best_spacing(results)
        _write_best(output_dir / "best.json", best)
        return {"results": results, "best": best}

    raise ValueError(f"Unknown optimization type: {opt_type}")


def _select_best_spacing(results: dict) -> dict:
    best = {}
    for total_distance, rows in results.items():
        best_row = max(rows, key=lambda r: r["throughput_hz"])
        sensitivity = _spacing_sensitivity(rows, best_row["spacing_km"])
        best[str(total_distance)] = {
            **best_row,
            "sensitivity": sensitivity,
        }
    return best


def _write_best(path: Path, best: dict) -> None:
    compact = {
        key: {
            "spacing_km": row["spacing_km"],
            "throughput_hz": row["throughput_hz"],
            "local_sensitivity": row["sensitivity"]["local_sensitivity"],
        }
        for key, row in best.items()
    }
    path.write_text(json.dumps(compact, indent=2), encoding="utf-8")


def _spacing_sensitivity(rows: list[dict], best_spacing: float) -> dict:
    ordered = sorted(rows, key=lambda row: row["spacing_km"])
    idx = next((i for i, row in enumerate(ordered) if row["spacing_km"] == best_spacing), None)
    if idx is None:
        return {"local_sensitivity": 0.0}

    left = ordered[idx - 1] if idx - 1 >= 0 else None
    right = ordered[idx + 1] if idx + 1 < len(ordered) else None
    if not left and not right:
        return {"local_sensitivity": 0.0}
    if left and right:
        d_throughput = right["throughput_hz"] - left["throughput_hz"]
        d_spacing = right["spacing_km"] - left["spacing_km"]
        return {"local_sensitivity": d_throughput / d_spacing if d_spacing else 0.0}
    neighbor = left or right
    d_throughput = ordered[idx]["throughput_hz"] - neighbor["throughput_hz"]
    d_spacing = ordered[idx]["spacing_km"] - neighbor["spacing_km"]
    return {"local_sensitivity": d_throughput / d_spacing if d_spacing else 0.0}
