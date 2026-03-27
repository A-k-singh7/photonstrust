"""Visualization library for PhotonsTrust simulation results."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt
import numpy as np

from photonstrust.presets import DETECTOR_PRESETS

# ---------------------------------------------------------------------------
# Style constants
# ---------------------------------------------------------------------------

PT_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
]

PT_STYLE: dict[str, Any] = {"figsize": (10, 6), "dpi": 160, "grid_alpha": 0.4}

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _setup_figure(**kwargs: Any) -> tuple[plt.Figure, plt.Axes]:
    """Create a new figure and axes with PT_STYLE defaults."""
    figsize = kwargs.pop("figsize", PT_STYLE["figsize"])
    dpi = kwargs.pop("dpi", PT_STYLE["dpi"])
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi, **kwargs)
    return fig, ax


def _apply_style(
    ax: plt.Axes,
    title: str,
    xlabel: str,
    ylabel: str,
) -> None:
    """Apply consistent styling to an axes."""
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.grid(True, alpha=PT_STYLE["grid_alpha"], linestyle="--")
    ax.figure.tight_layout()


def _save_or_show(fig: plt.Figure, save_path: str | Path | None) -> plt.Figure:
    """Save the figure to *save_path* if provided, then return it."""
    if save_path is not None:
        path = Path(save_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=PT_STYLE["dpi"], bbox_inches="tight")
    return fig


def _plob_bound(
    distances_km: list[float] | np.ndarray,
    fiber_loss_db_per_km: float = 0.2,
) -> list[float]:
    """Compute the PLOB repeater-less secret-key-capacity bound.

    For each distance *d*:
        loss = d * fiber_loss_db_per_km
        eta  = 10**(-loss / 10)
        rate = -log2(1 - eta)   if eta < 1 else 0
    """
    rates: list[float] = []
    for d in distances_km:
        loss = d * fiber_loss_db_per_km
        eta = 10.0 ** (-loss / 10.0)
        if eta < 1.0:
            rates.append(-math.log2(1.0 - eta))
        else:
            rates.append(0.0)
    return rates


# ---------------------------------------------------------------------------
# 1. Rate-distance curve
# ---------------------------------------------------------------------------


def plot_rate_distance(
    results: list | dict[str, list],
    *,
    show_plob: bool = True,
    log_y: bool = True,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Plot key-rate vs distance.

    Parameters
    ----------
    results
        A ``list[QKDResult]`` for a single protocol, or
        ``dict[str, list[QKDResult]]`` for multi-protocol overlay.
    show_plob
        If *True*, overlay the PLOB bound curve.
    log_y
        If *True*, use a logarithmic y-axis.
    save_path
        Optional path to save the figure.
    """
    fig, ax = _setup_figure()

    # Normalise to dict form
    if isinstance(results, list):
        curves: dict[str, list] = {"Protocol": results}
    else:
        curves = results

    all_distances: list[float] = []

    for idx, (label, res_list) in enumerate(curves.items()):
        color = PT_COLORS[idx % len(PT_COLORS)]
        distances = [r.distance_km for r in res_list]
        rates = [max(r.key_rate_bps, 1e-12) for r in res_list]
        ax.plot(distances, rates, label=label, color=color, linewidth=2)
        all_distances.extend(distances)

    if show_plob and all_distances:
        d_min, d_max = min(all_distances), max(all_distances)
        d_arr = np.linspace(d_min, d_max, 200)
        plob = _plob_bound(d_arr.tolist())
        ax.plot(
            d_arr,
            plob,
            "--",
            color="gray",
            linewidth=1.5,
            label="PLOB bound",
        )

    if log_y:
        ax.set_yscale("log")

    ax.legend()
    _apply_style(ax, "Key Rate vs Distance", "Distance (km)", "Key Rate (bps)")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 2. Protocol comparison
# ---------------------------------------------------------------------------


def plot_protocol_comparison(
    comparison: dict[str, list],
    *,
    metric: str = "key_rate_bps",
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Overlay multiple protocols on the same axes for a chosen metric."""
    fig, ax = _setup_figure()

    for idx, (label, res_list) in enumerate(comparison.items()):
        color = PT_COLORS[idx % len(PT_COLORS)]
        distances = [r.distance_km for r in res_list]
        values = [getattr(r, metric) for r in res_list]
        ax.plot(distances, values, label=label, color=color, linewidth=2, marker="o", markersize=3)

    if comparison:
        ax.legend()
    ylabel = metric.replace("_", " ").title()
    _apply_style(ax, f"Protocol Comparison ({ylabel})", "Distance (km)", ylabel)
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 3. PIC spectrum
# ---------------------------------------------------------------------------


def plot_pic_spectrum(
    sweep_results: dict[str, Any],
    *,
    port: str | None = None,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Plot PIC transmission spectrum (transmission vs wavelength)."""
    fig, ax = _setup_figure()

    wavelengths = np.asarray(sweep_results["wavelengths_nm"])
    transmission = np.asarray(sweep_results["transmission_db"])

    # If transmission is 2-D (multi-port), allow selecting a single port or
    # plot all ports.
    if transmission.ndim == 2:
        if port is not None:
            port_idx = int(port) if port.isdigit() else 0
            ax.plot(wavelengths, transmission[port_idx], color=PT_COLORS[0], linewidth=1.5)
        else:
            for i, row in enumerate(transmission):
                ax.plot(
                    wavelengths,
                    row,
                    color=PT_COLORS[i % len(PT_COLORS)],
                    linewidth=1.5,
                    label=f"Port {i}",
                )
            ax.legend(fontsize=8)
    else:
        label = f"Port {port}" if port else "Transmission"
        ax.plot(wavelengths, transmission, color=PT_COLORS[0], linewidth=1.5, label=label)

    _apply_style(ax, "PIC Transmission Spectrum", "Wavelength (nm)", "Transmission (dB)")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 4. Network topology
# ---------------------------------------------------------------------------


def plot_network_topology(
    network: dict[str, Any],
    *,
    show_key_rates: bool = True,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Draw a node-link network graph using matplotlib (no networkx)."""
    fig, ax = _setup_figure()

    nodes = network.get("nodes", [])
    links = network.get("links", [])

    # Build positions: use explicit location or auto-layout in a circle.
    positions: dict[str, tuple[float, float]] = {}
    n = len(nodes)
    for i, node in enumerate(nodes):
        loc = node.get("location")
        if loc is not None and len(loc) >= 2:
            positions[node["node_id"]] = (float(loc[0]), float(loc[1]))
        else:
            angle = 2 * math.pi * i / max(n, 1)
            positions[node["node_id"]] = (math.cos(angle), math.sin(angle))

    # Draw links
    for link in links:
        a, b = link["node_a"], link["node_b"]
        if a in positions and b in positions:
            xa, ya = positions[a]
            xb, yb = positions[b]
            ax.plot([xa, xb], [ya, yb], color="#aaaaaa", linewidth=1.5, zorder=1)
            if show_key_rates and "distance_km" in link:
                mx, my = (xa + xb) / 2, (ya + yb) / 2
                ax.text(
                    mx,
                    my,
                    f"{link['distance_km']:.0f} km",
                    fontsize=7,
                    ha="center",
                    va="center",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.7),
                    zorder=3,
                )

    # Draw nodes
    for nid, (x, y) in positions.items():
        ax.plot(x, y, "o", color=PT_COLORS[0], markersize=12, zorder=2)
        ax.text(
            x,
            y + 0.08,
            nid,
            fontsize=8,
            ha="center",
            va="bottom",
            fontweight="bold",
            zorder=4,
        )

    ax.set_aspect("equal", adjustable="datalim")
    _apply_style(ax, "Network Topology", "", "")
    ax.set_xticks([])
    ax.set_yticks([])
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 5. Constellation / satellite passes
# ---------------------------------------------------------------------------


def plot_constellation(
    passes: list[dict[str, Any]],
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Plot satellite pass elevation profiles over time."""
    fig, ax = _setup_figure()

    gs_ids = sorted({p.get("ground_station_id", "GS") for p in passes})
    color_map = {gs: PT_COLORS[i % len(PT_COLORS)] for i, gs in enumerate(gs_ids)}

    for p in passes:
        gs = p.get("ground_station_id", "GS")
        t_start = p["start_time_s"]
        t_end = p["end_time_s"]
        elev = p.get("max_elevation_deg", 45)
        # Simple triangular elevation profile
        t_mid = (t_start + t_end) / 2
        ax.plot(
            [t_start, t_mid, t_end],
            [0, elev, 0],
            color=color_map[gs],
            linewidth=1.5,
            label=gs,
        )

    # Deduplicate legend entries
    handles, labels = ax.get_legend_handles_labels()
    seen: dict[str, Any] = {}
    for h, l in zip(handles, labels):
        if l not in seen:
            seen[l] = h
    ax.legend(seen.values(), seen.keys(), fontsize=8)

    _apply_style(ax, "Satellite Pass Elevation", "Time (s)", "Elevation (deg)")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 6. Detector comparison
# ---------------------------------------------------------------------------


def plot_detector_comparison(
    detectors: dict[str, dict[str, Any]] | None = None,
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Multi-panel bar chart comparing detector metrics (PDE, dark counts, jitter)."""
    if detectors is None:
        detectors = DETECTOR_PRESETS

    metrics = [
        ("pde", "PDE"),
        ("dark_counts_cps", "Dark Counts (cps)"),
        ("jitter_ps_fwhm", "Jitter (ps FWHM)"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5), dpi=PT_STYLE["dpi"])
    names = list(detectors.keys())
    x = np.arange(len(names))

    for i, (key, ylabel) in enumerate(metrics):
        ax = axes[i]
        values = [detectors[n].get(key, 0) for n in names]
        colors = [PT_COLORS[j % len(PT_COLORS)] for j in range(len(names))]
        ax.bar(x, values, color=colors, width=0.6)
        ax.set_xticks(x)
        ax.set_xticklabels(names, fontsize=8, rotation=30, ha="right")
        _apply_style(ax, ylabel, "", ylabel)

    fig.suptitle("Detector Comparison", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 7. Yield histogram
# ---------------------------------------------------------------------------


def plot_yield_histogram(
    yield_result: dict[str, Any],
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Histogram of yield metric samples with pass/fail shading."""
    fig, ax = _setup_figure()

    samples = np.asarray(yield_result["metric_samples"])
    spec_min = yield_result.get("spec_min", None)
    spec_max = yield_result.get("spec_max", None)

    ax.hist(samples, bins=40, color=PT_COLORS[0], edgecolor="white", alpha=0.8)

    ylims = ax.get_ylim()
    if spec_min is not None:
        ax.axvline(spec_min, color="red", linewidth=1.5, linestyle="--", label="Spec min")
        ax.axvspan(ax.get_xlim()[0], spec_min, color="red", alpha=0.08)
    if spec_max is not None:
        ax.axvline(spec_max, color="red", linewidth=1.5, linestyle="--", label="Spec max")
        ax.axvspan(spec_max, ax.get_xlim()[1], color="red", alpha=0.08)

    ax.legend(fontsize=8)
    _apply_style(ax, "Yield Distribution", "Metric Value", "Count")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 8. Heatmap
# ---------------------------------------------------------------------------


def plot_heatmap(
    data: Any,
    *,
    x_label: str = "X",
    y_label: str = "Y",
    value_label: str = "Value",
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Colormap heatmap of a 2-D array."""
    fig, ax = _setup_figure()

    arr = np.atleast_2d(np.asarray(data, dtype=float))
    im = ax.imshow(arr, aspect="auto", cmap="viridis", origin="lower")
    fig.colorbar(im, ax=ax, label=value_label)

    _apply_style(ax, "Heatmap", x_label, y_label)
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 9. Eye diagram
# ---------------------------------------------------------------------------


def plot_eye_diagram(
    transient_data: dict[str, Any],
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Plot an eye diagram by folding a transient waveform on its bit period."""
    fig, ax = _setup_figure()

    time_ps = np.asarray(transient_data["time_ps"], dtype=float)
    voltage = np.asarray(transient_data["voltage_v"], dtype=float)

    # Estimate bit period from data length (default: fold into ~4 UI windows)
    total = time_ps[-1] - time_ps[0] if len(time_ps) > 1 else 1.0
    bit_period = transient_data.get("bit_period_ps", total / 4.0)

    if bit_period <= 0:
        bit_period = total / 4.0

    # Fold time axis onto two unit intervals (2 UI) for a standard eye
    folded_time = (time_ps - time_ps[0]) % (2 * bit_period)

    ax.plot(folded_time, voltage, color=PT_COLORS[0], alpha=0.3, linewidth=0.5)

    _apply_style(ax, "Eye Diagram", "Time (ps)", "Voltage (V)")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 10. Passband / AWG response
# ---------------------------------------------------------------------------


def plot_passband(
    awg_result: dict[str, Any],
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Plot multi-channel AWG passband response."""
    fig, ax = _setup_figure()

    wavelengths = np.asarray(awg_result["wavelengths_nm"])
    channels = awg_result["channels"]

    for i, ch in enumerate(channels):
        transmission = np.asarray(ch["transmission_db"])
        label = ch.get("label", f"Ch {i}")
        ax.plot(
            wavelengths,
            transmission,
            color=PT_COLORS[i % len(PT_COLORS)],
            linewidth=1.2,
            label=label,
        )

    ax.legend(fontsize=7, ncol=2)
    _apply_style(ax, "AWG Passband Response", "Wavelength (nm)", "Transmission (dB)")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 11. QBER budget
# ---------------------------------------------------------------------------


def plot_qber_budget(
    qkd_result: Any,
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Stacked bar chart of QBER contributions."""
    fig, ax = _setup_figure()

    qber_keys = [
        ("q_dark", "Dark counts"),
        ("q_timing", "Timing jitter"),
        ("q_misalignment", "Misalignment"),
        ("q_source", "Source"),
    ]

    # Support both dataclass and dict inputs
    def _get(obj: Any, key: str, default: float = 0.0) -> float:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    values = [_get(qkd_result, k) for k, _ in qber_keys]
    labels = [lbl for _, lbl in qber_keys]
    colors = PT_COLORS[: len(values)]

    bottom = 0.0
    for val, lbl, col in zip(values, labels, colors):
        ax.bar("QBER", val, bottom=bottom, color=col, label=lbl, width=0.5)
        bottom += val

    total = _get(qkd_result, "qber_total", sum(values))
    ax.axhline(total, color="black", linewidth=1, linestyle="--", label=f"Total QBER ({total:.4f})")

    ax.legend(fontsize=8)
    _apply_style(ax, "QBER Budget Breakdown", "", "QBER")
    return _save_or_show(fig, save_path)


# ---------------------------------------------------------------------------
# 12. Loss budget (waterfall chart)
# ---------------------------------------------------------------------------


def plot_loss_budget(
    qkd_result: Any,
    *,
    save_path: str | Path | None = None,
) -> plt.Figure:
    """Waterfall chart showing loss contributions."""
    fig, ax = _setup_figure()

    def _get(obj: Any, key: str, default: float = 0.0) -> float:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    total_loss = _get(qkd_result, "loss_db", 0.0)
    distance = _get(qkd_result, "distance_km", 0.0)

    # Build loss components — use heuristic split when detailed fields absent
    fiber_loss = _get(qkd_result, "fiber_loss_db", distance * 0.2)
    coupling_loss = _get(qkd_result, "coupling_loss_db", 1.0)
    detector_loss = _get(qkd_result, "detector_loss_db", 0.0)
    other_loss = max(0.0, total_loss - fiber_loss - coupling_loss - detector_loss)

    components = [
        ("Fiber", fiber_loss),
        ("Coupling", coupling_loss),
        ("Detector", detector_loss),
        ("Other", other_loss),
    ]

    # Waterfall: bars stacked upward from zero
    cumulative = 0.0
    for i, (label, val) in enumerate(components):
        ax.bar(
            label,
            val,
            bottom=cumulative,
            color=PT_COLORS[i % len(PT_COLORS)],
            width=0.5,
            edgecolor="white",
        )
        # Annotate value on bar
        if val > 0:
            ax.text(
                i,
                cumulative + val / 2,
                f"{val:.1f} dB",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="bold",
            )
        cumulative += val

    # Total bar
    ax.bar("Total", total_loss, color="#333333", width=0.5, edgecolor="white")
    ax.text(
        len(components),
        total_loss / 2,
        f"{total_loss:.1f} dB",
        ha="center",
        va="center",
        fontsize=8,
        fontweight="bold",
        color="white",
    )

    _apply_style(ax, "Loss Budget", "", "Loss (dB)")
    return _save_or_show(fig, save_path)
