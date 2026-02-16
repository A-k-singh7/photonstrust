"""Heralding realism comparison (Demo 3)."""

from __future__ import annotations

from pathlib import Path

from photonstrust.plots import plot_key_rate
from photonstrust.qkd import compute_point


def run_heralding_comparison(config: dict, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    comparison = config["heralding_comparison"]
    distances = _expand_range(comparison["distance_km"])

    realistic = comparison["scenario"]
    toy = _build_toy_scenario(realistic)

    realistic_results = [compute_point(realistic, d) for d in distances]
    toy_results = [compute_point(toy, d) for d in distances]

    _write_results(output_dir / "results.json", distances, realistic_results, toy_results)
    plot_key_rate(
        {
            "realistic": realistic_results,
            "toy_model": toy_results,
        },
        output_dir / "key_rate_comparison.png",
    )
    _write_html_report(output_dir / "report.html", realistic_results, toy_results)
    return {"realistic": realistic_results, "toy": toy_results}


def _build_toy_scenario(realistic: dict) -> dict:
    toy = _deepcopy(realistic)
    toy["detector"]["dark_counts_cps"] = 0.0
    toy["detector"]["afterpulsing_prob"] = 0.0
    toy["detector"]["jitter_ps_fwhm"] = 1.0
    if toy["source"]["type"] == "emitter_cavity":
        toy["source"]["g2_0"] = 0.0
    if toy["source"]["type"] == "spdc":
        toy["source"]["mu"] = min(toy["source"]["mu"], 0.01)
    return toy


def _expand_range(rng: dict) -> list[float]:
    start = float(rng["start"])
    stop = float(rng["stop"])
    step = float(rng["step"])
    count = int((stop - start) / step) + 1
    return [start + i * step for i in range(count)]


def _write_results(path: Path, distances, realistic, toy) -> None:
    lines = ["{"]
    lines.append('  "distances_km": [' + ", ".join(f"{d:.6g}" for d in distances) + "],")
    lines.append('  "realistic": [')
    for idx, res in enumerate(realistic):
        comma = "," if idx < len(realistic) - 1 else ""
        lines.append(
            "    {"
            f"\"key_rate_bps\": {res.key_rate_bps:.6g}, "
            f"\"qber_total\": {res.qber_total:.6g}"
            "}" + comma
        )
    lines.append("  ],")
    lines.append('  "toy_model": [')
    for idx, res in enumerate(toy):
        comma = "," if idx < len(toy) - 1 else ""
        lines.append(
            "    {"
            f"\"key_rate_bps\": {res.key_rate_bps:.6g}, "
            f"\"qber_total\": {res.qber_total:.6g}"
            "}" + comma
        )
    lines.append("  ]")
    lines.append("}")
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_html_report(path: Path, realistic, toy) -> None:
    delta = toy[-1].key_rate_bps - realistic[-1].key_rate_bps
    lines = ["<!doctype html>", "<html lang=\"en\">", "<head>"]
    lines.append("<meta charset=\"utf-8\" />")
    lines.append("<title>PhotonTrust Heralding Comparison</title>")
    lines.append("<style>body{font-family:Segoe UI, Tahoma, sans-serif;margin:32px;}</style>")
    lines.append("</head><body>")
    lines.append("<h1>Heralding Realism Matters</h1>")
    lines.append(
        f"<p>Toy model overestimates key rate by {delta:.4g} bps at the max distance.</p>"
    )
    lines.append("</body></html>")
    path.write_text("\n".join(lines), encoding="utf-8")


def _deepcopy(value):
    if isinstance(value, dict):
        return {k: _deepcopy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deepcopy(v) for v in value]
    return value
