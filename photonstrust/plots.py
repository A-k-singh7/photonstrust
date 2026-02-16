"""Plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib

from photonstrust.qkd import QKDResult


# Use a non-interactive backend so plotting works in headless CI environments.
matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt


def plot_key_rate(curves: dict[str, list[QKDResult]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 5))
    for label, results in curves.items():
        distances = [r.distance_km for r in results]
        key_rates = [max(r.key_rate_bps, 1e-12) for r in results]
        plt.plot(distances, key_rates, label=label, linewidth=2)
    plt.yscale("log")
    plt.xlabel("Distance (km)")
    plt.ylabel("Key rate (bps)")
    plt.title("Entanglement-based QKD key rate")
    plt.grid(True, which="both", linestyle="--", alpha=0.4)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()
