"""Teleportation SLA scenario."""

from __future__ import annotations

from pathlib import Path

import json

from photonstrust.physics import simulate_memory
from photonstrust.qkd import compute_point


def run_teleportation(config: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario = config["teleportation"]
    distances = _expand_range(scenario["distance_km"])
    results = []
    sla_cfg = scenario.get("sla", {})
    min_success = sla_cfg.get("min_success_prob")
    min_fidelity = sla_cfg.get("min_fidelity")

    for distance in distances:
        link_cfg = scenario["link_scenario"]
        result = compute_point(link_cfg, distance)
        latency_ns = scenario.get("classical_latency_ns", 0.0)
        memory_stats = simulate_memory(scenario["memory"], latency_ns)

        success_prob = min(1.0, result.p_pair * memory_stats.p_retrieve)
        fidelity = result.fidelity * memory_stats.fidelity
        outage = _is_outage(success_prob, fidelity, min_success, min_fidelity)
        results.append(
            {
                "distance_km": distance,
                "success_prob": success_prob,
                "fidelity": fidelity,
                "outage": outage,
            }
        )

    outage_probability = sum(1 for row in results if row["outage"]) / max(len(results), 1)
    summary = {
        "distances": len(results),
        "outage_probability": outage_probability,
        "min_success_prob": min_success,
        "min_fidelity": min_fidelity,
    }
    _write_results(output_dir / "results.json", results, summary)
    return {"results": results, "summary": summary}


def _expand_range(rng: dict) -> list[float]:
    start = float(rng["start"])
    stop = float(rng["stop"])
    step = float(rng["step"])
    count = int((stop - start) / step) + 1
    return [start + i * step for i in range(count)]


def _write_results(path: Path, results: list[dict], summary: dict) -> None:
    payload = {"results": results, "summary": summary}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _is_outage(
    success_prob: float,
    fidelity: float,
    min_success: float | None,
    min_fidelity: float | None,
) -> bool:
    if min_success is not None and success_prob < float(min_success):
        return True
    if min_fidelity is not None and fidelity < float(min_fidelity):
        return True
    return False
