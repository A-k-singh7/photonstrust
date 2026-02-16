"""Repeater spacing optimization (Demo 2)."""

from __future__ import annotations

import json
import math
from pathlib import Path

from photonstrust.plots import plot_key_rate
from photonstrust.physics import simulate_memory
from photonstrust.qkd import compute_point


def run_repeater_optimization(config: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    optimization = config["repeater_optimization"]
    totals = optimization["total_distance_km"]
    if isinstance(totals, (int, float)):
        totals = [float(totals)]

    spacing_cfg = optimization["spacing_km"]
    spacings = _expand_range(spacing_cfg)

    scenario = optimization["link_scenario"]
    memory = optimization["memory"]
    results = {}

    for total_distance in totals:
        spacing_results = []
        for spacing in spacings:
            segments = max(1, math.ceil(total_distance / spacing))
            link_distance = total_distance / segments
            link_result = compute_point(scenario, link_distance)
            throughput, fidelity = _chain_metrics(link_result, segments, memory)
            spacing_results.append(
                {
                    "spacing_km": spacing,
                    "segments": segments,
                    "link_distance_km": link_distance,
                    "throughput_hz": throughput,
                    "fidelity": fidelity,
                }
            )
        results[total_distance] = spacing_results

    _write_results(output_dir / "results.json", results)
    _plot_throughput(output_dir / "throughput_vs_spacing.png", results)
    _write_html_report(output_dir / "report.html", results, memory)

    return results


def _chain_metrics(link_result, segments: int, memory: dict) -> tuple[float, float]:
    harmonic = sum(1.0 / k for k in range(1, segments + 1))
    wait_time_s = harmonic / max(link_result.entanglement_rate_hz, 1e-12)
    wait_time_ns = wait_time_s * 1e9

    memory_cfg = {
        **memory,
        "physics_backend": memory.get("physics_backend", "analytic"),
        "store_efficiency": memory.get("store_efficiency", 1.0),
    }
    stats = simulate_memory(memory_cfg, wait_time_ns)

    throughput = (link_result.entanglement_rate_hz / harmonic) * stats.p_retrieve
    fidelity = link_result.fidelity * stats.fidelity
    return throughput, fidelity


def _expand_range(rng: dict) -> list[float]:
    start = float(rng["start"])
    stop = float(rng["stop"])
    step = float(rng["step"])
    count = int((stop - start) / step) + 1
    return [start + i * step for i in range(count)]


def _write_results(path: Path, results: dict) -> None:
    path.write_text(json.dumps(results, indent=2), encoding="utf-8")


def _plot_throughput(path: Path, results: dict) -> None:
    curves = {}
    for total_distance, rows in results.items():
        curves[f"{total_distance} km"] = [
            _FakeResult(row["spacing_km"], row["throughput_hz"]) for row in rows
        ]
    plot_key_rate(curves, path)


def _write_html_report(path: Path, results: dict, memory: dict) -> None:
    lines = ["<!doctype html>", "<html lang=\"en\">", "<head>"]
    lines.append("<meta charset=\"utf-8\" />")
    lines.append("<title>PhotonTrust Repeater Optimization</title>")
    lines.append("<style>body{font-family:Segoe UI, Tahoma, sans-serif;margin:32px;}</style>")
    lines.append("</head><body>")
    lines.append("<h1>Repeater Spacing Optimization</h1>")
    lines.append(f"<p>T2: {memory['t2_ms']} ms | Retrieval: {memory['retrieval_efficiency']}</p>")
    for total_distance, rows in results.items():
        best = max(rows, key=lambda r: r["throughput_hz"])
        lines.append(
            f"<h2>Total distance {total_distance} km</h2>"
            f"<p>Best spacing: {best['spacing_km']} km | Throughput: {best['throughput_hz']:.4g} Hz</p>"
        )
    lines.append("</body></html>")
    path.write_text("\n".join(lines), encoding="utf-8")


class _FakeResult:
    def __init__(self, distance_km: float, key_rate_bps: float):
        self.distance_km = distance_km
        self.key_rate_bps = key_rate_bps
