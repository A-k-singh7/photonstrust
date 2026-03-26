"""Self-contained HTML report generator for PhotonsTrust results.

Example
-------
    from photonstrust.easy import simulate_qkd_link
    from photonstrust.reporting.html_report import generate_html_report

    result = simulate_qkd_link(protocol="bb84", distance_km=50)
    html = generate_html_report(result, title="BB84 Link Analysis")
    with open("report.html", "w") as f:
        f.write(html)
"""

from __future__ import annotations

import base64
import io
import math
from datetime import datetime, timezone
from typing import Any

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Color scheme (matches PT_COLORS from visualize.py)
# ---------------------------------------------------------------------------

_PT_COLORS = [
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_html_report(
    results: Any,
    *,
    title: str = "PhotonsTrust Report",
    include_plots: bool = True,
    include_methodology: bool = True,
) -> str:
    """Generate a self-contained HTML report.

    Auto-detects result type (QKDLinkResult, ProtocolComparison,
    PICDesignResult, NetworkPlan, SatellitePlan, or raw dict/list).

    Parameters
    ----------
    results
        Any PhotonsTrust result object or a plain dict/list.
    title
        HTML page title and report heading.
    include_plots
        Whether to embed base64 PNG plots in the report.
    include_methodology
        Whether to include a methodology description section.

    Returns
    -------
    str
        Complete, self-contained HTML document.
    """
    result_type = _detect_result_type(results)

    sections: list[str] = []

    # 1. Executive summary (always)
    sections.append(_render_executive_summary(results, result_type))

    # 2. Configuration (if available)
    config = _extract_config(results, result_type)
    if config:
        sections.append(_render_configuration_section(config))

    # 3. Results table (if tabular data exists)
    table_html = _render_results_table(results, result_type)
    if table_html:
        sections.append(table_html)

    # 4. Plots (if requested and supported)
    if include_plots and result_type in ("qkd_link", "protocol_comparison"):
        plots_html = _render_plots_section(results, result_type)
        if plots_html:
            sections.append(plots_html)

    # 5. Methodology
    if include_methodology and result_type in (
        "qkd_link",
        "protocol_comparison",
        "satellite",
    ):
        sections.append(_render_methodology_section())

    # 6. References (for QKD results)
    if result_type in ("qkd_link", "protocol_comparison"):
        sections.append(_render_references_section())

    body = "\n".join(sections)
    css = _default_css()
    return _html_skeleton(title, body, css)


def generate_summary_card(results: Any, *, title: str = "Summary") -> str:
    """Generate a compact HTML summary card (subset of full report).

    Returns a minimal HTML snippet suitable for embedding. Does not include
    plots, methodology, or references.
    """
    result_type = _detect_result_type(results)
    sections: list[str] = []
    sections.append(_render_executive_summary(results, result_type))
    config = _extract_config(results, result_type)
    if config:
        sections.append(_render_configuration_section(config))
    body = "\n".join(sections)
    css = _default_css()
    return _html_skeleton(title, body, css)


# ---------------------------------------------------------------------------
# Result type detection
# ---------------------------------------------------------------------------


def _detect_result_type(results: Any) -> str:
    """Detect the type of result object."""
    type_name = type(results).__name__
    if type_name == "QKDLinkResult":
        return "qkd_link"
    elif type_name == "ProtocolComparison":
        return "protocol_comparison"
    elif type_name == "PICDesignResult":
        return "pic_design"
    elif type_name == "NetworkPlan":
        return "network"
    elif type_name == "SatellitePlan":
        return "satellite"
    elif isinstance(results, dict):
        return "raw_dict"
    elif isinstance(results, list):
        return "raw_list"
    return "unknown"


def _extract_config(results: Any, result_type: str) -> dict | None:
    """Extract configuration dictionary if available."""
    if result_type == "qkd_link" and hasattr(results, "config"):
        return results.config
    if result_type == "protocol_comparison" and hasattr(results, "protocols"):
        # Merge configs from all protocols
        merged: dict[str, Any] = {}
        for name, lr in results.protocols.items():
            if hasattr(lr, "config") and lr.config:
                merged[name] = lr.config
        return merged if merged else None
    if hasattr(results, "config"):
        return results.config  # type: ignore[union-attr]
    if isinstance(results, dict) and "config" in results:
        return results["config"]
    return None


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------


def _render_executive_summary(results: Any, result_type: str) -> str:
    """Key metrics at a glance -- protocol, max distance, peak rate, etc."""
    cards: list[tuple[str, str]] = []

    if result_type == "qkd_link":
        r_list = getattr(results, "results", [])
        if r_list:
            protocol = r_list[0].protocol_name or "N/A"
            peak_rate = max(r.key_rate_bps for r in r_list)
            max_dist = results.max_distance_km()
            min_qber = min(r.qber_total for r in r_list)
            cards = [
                ("Protocol", protocol),
                ("Peak Key Rate", _format_rate(peak_rate)),
                ("Max Distance", f"{max_dist:.1f} km"),
                ("Min QBER", f"{min_qber:.4f}"),
                ("Points", str(len(r_list))),
            ]

    elif result_type == "protocol_comparison":
        protocols = getattr(results, "protocols", {})
        n_protocols = len(protocols)
        all_rates: list[float] = []
        all_dists: list[float] = []
        for lr in protocols.values():
            for r in lr.results:
                all_rates.append(r.key_rate_bps)
                all_dists.append(r.distance_km)
        cards = [
            ("Protocols Compared", str(n_protocols)),
            ("Protocol Names", ", ".join(sorted(protocols.keys()))),
            ("Best Peak Rate", _format_rate(max(all_rates)) if all_rates else "N/A"),
            ("Max Distance Tested", f"{max(all_dists):.1f} km" if all_dists else "N/A"),
        ]

    elif result_type == "pic_design":
        netlist = getattr(results, "netlist", {})
        n_nodes = len(netlist.get("nodes", []))
        n_edges = len(netlist.get("edges", []))
        drc = getattr(results, "drc_result", None)
        drc_status = drc.get("status", "N/A") if drc else "not run"
        cards = [
            ("Components", str(n_nodes)),
            ("Connections", str(n_edges)),
            ("DRC Status", drc_status),
        ]

    elif result_type == "network":
        topo = getattr(results, "topology", {})
        n_nodes = len(topo.get("nodes", []))
        n_links = len(topo.get("links", []))
        n_paths = len(getattr(results, "paths", []))
        agg = getattr(results, "aggregate", {})
        agg_rate = agg.get("total_key_rate_bps")
        cards = [
            ("Nodes", str(n_nodes)),
            ("Links", str(n_links)),
            ("Paths", str(n_paths)),
            ("Aggregate Rate", _format_rate(agg_rate) if agg_rate else "N/A"),
        ]

    elif result_type == "satellite":
        schedule = getattr(results, "schedule", {})
        constellation = getattr(results, "constellation", None) or {}
        n_sats = constellation.get("total_sats", "N/A")
        n_passes = schedule.get("n_passes", 0)
        utilization = schedule.get("utilization", 0.0)
        cards = [
            ("Satellites", str(n_sats)),
            ("Passes", str(n_passes)),
            ("Utilization", f"{utilization:.0%}"),
        ]

    elif result_type == "raw_dict":
        cards = [(k, str(v)[:80]) for k, v in list(results.items())[:6]]

    elif result_type == "raw_list":
        cards = [("Items", str(len(results)))]

    else:
        summary_text = ""
        if hasattr(results, "summary"):
            summary_text = results.summary()
        cards = [("Summary", summary_text or str(results)[:200])]

    if not cards:
        cards = [("Status", "No data available")]

    # Build HTML metric cards
    card_html = '<div class="metric-cards">\n'
    for label, value in cards:
        card_html += (
            f'  <div class="metric-card">\n'
            f'    <div class="metric-label">{_escape(label)}</div>\n'
            f'    <div class="metric-value">{_escape(value)}</div>\n'
            f"  </div>\n"
        )
    card_html += "</div>\n"

    return f'<section class="executive-summary">\n<h2>Executive Summary</h2>\n{card_html}</section>\n'


def _render_configuration_section(config: dict) -> str:
    """Parameter table showing simulation configuration."""
    if not config:
        return ""

    rows: list[list[str]] = []

    def _flatten(d: Any, prefix: str = "") -> None:
        if isinstance(d, dict):
            for k, v in d.items():
                key_str = f"{prefix}.{k}" if prefix else str(k)
                if isinstance(v, dict):
                    _flatten(v, key_str)
                else:
                    rows.append([key_str, str(v)])
        else:
            rows.append([prefix or "value", str(d)])

    _flatten(config)

    table = _render_table(["Parameter", "Value"], rows, caption="Configuration")
    return f'<section class="configuration">\n<h2>Configuration</h2>\n{table}</section>\n'


def _render_results_table(results: Any, result_type: str) -> str:
    """Tabular data: distance, key rate, QBER, fidelity for each point."""
    if result_type == "qkd_link":
        r_list = getattr(results, "results", [])
        if not r_list:
            return ""
        headers = ["Distance (km)", "Key Rate (bps)", "QBER", "Fidelity", "Loss (dB)"]
        rows = []
        for r in r_list:
            rows.append([
                f"{r.distance_km:.1f}",
                _format_rate(r.key_rate_bps),
                f"{r.qber_total:.5f}",
                f"{r.fidelity:.5f}",
                f"{r.loss_db:.2f}",
            ])
        table = _render_table(headers, rows, caption="QKD Link Results")
        return f'<section class="results-data">\n<h2>Results</h2>\n{table}</section>\n'

    if result_type == "protocol_comparison":
        protocols = getattr(results, "protocols", {})
        headers = ["Protocol", "Distance (km)", "Key Rate (bps)", "QBER", "Fidelity"]
        rows = []
        for name, lr in sorted(protocols.items()):
            for r in lr.results:
                rows.append([
                    name,
                    f"{r.distance_km:.1f}",
                    _format_rate(r.key_rate_bps),
                    f"{r.qber_total:.5f}",
                    f"{r.fidelity:.5f}",
                ])
        table = _render_table(headers, rows, caption="Protocol Comparison Results")
        return f'<section class="results-data">\n<h2>Results</h2>\n{table}</section>\n'

    if result_type == "raw_list" and results:
        if isinstance(results[0], dict):
            all_keys: list[str] = []
            for item in results:
                for k in item:
                    if k not in all_keys:
                        all_keys.append(k)
            rows = [[str(item.get(k, "")) for k in all_keys] for item in results]
            table = _render_table(all_keys, rows, caption="Data")
            return f'<section class="results-data">\n<h2>Results</h2>\n{table}</section>\n'

    return ""


def _render_plots_section(results: Any, result_type: str) -> str:
    """Base64-embedded PNG plots."""
    plots: list[str] = []

    if result_type == "qkd_link":
        fig = _plot_qkd_link(results)
        if fig is not None:
            plots.append(_figure_to_base64(fig))
            plt.close(fig)

    elif result_type == "protocol_comparison":
        fig = _plot_protocol_comparison(results)
        if fig is not None:
            plots.append(_figure_to_base64(fig))
            plt.close(fig)

    if not plots:
        return ""

    imgs = "\n".join(
        f'<div class="plot-container"><img src="{uri}" alt="Plot" /></div>'
        for uri in plots
    )
    return f'<section class="plots">\n<h2>Plots</h2>\n{imgs}\n</section>\n'


def _render_methodology_section() -> str:
    """Brief physics model description."""
    text = (
        "<p>This report was generated using PhotonsTrust, a comprehensive "
        "quantum key distribution simulation framework. The underlying model "
        "accounts for the following physical effects:</p>\n"
        "<ul>\n"
        "  <li><strong>Channel loss:</strong> Fiber attenuation (typ. 0.2 dB/km at 1550 nm) "
        "including splice and connector losses.</li>\n"
        "  <li><strong>Detector imperfections:</strong> Dark count rates, detection efficiency, "
        "timing jitter, and afterpulsing probability.</li>\n"
        "  <li><strong>Source characteristics:</strong> Mean photon number, multi-photon emission "
        "probability, and spectral purity.</li>\n"
        "  <li><strong>Error contributions:</strong> Optical misalignment, polarization drift, "
        "background photons, Raman scattering, and dark counts.</li>\n"
        "  <li><strong>Finite-key effects:</strong> Statistical fluctuations in parameter "
        "estimation with composable security bounds.</li>\n"
        "  <li><strong>Privacy amplification:</strong> Asymptotic and finite-key secret-key "
        "rate formulas appropriate to each protocol.</li>\n"
        "</ul>\n"
        "<p>Key rates are computed using protocol-specific security proofs. "
        "Decoy-state analysis uses the vacuum + weak decoy method for BB84-based "
        "protocols. Twin-field protocols use the sending-or-not-sending variant.</p>"
    )
    return (
        '<section class="methodology">\n'
        "<h2>Methodology</h2>\n"
        f"{text}\n"
        "</section>\n"
    )


def _render_references_section() -> str:
    """Cited papers for QKD protocols."""
    refs = [
        (
            "Bennett, C.H. and Brassard, G. (1984). "
            '"Quantum cryptography: Public key distribution and coin tossing." '
            "Proceedings of IEEE International Conference on Computers, Systems and Signal Processing."
        ),
        (
            "Lo, H.-K., Ma, X., and Chen, K. (2005). "
            '"Decoy state quantum key distribution." '
            "Physical Review Letters, 94(23), 230504. "
            "https://doi.org/10.1103/PhysRevLett.94.230504"
        ),
        (
            "Lucamarini, M., Yuan, Z.L., Dynes, J.F., and Shields, A.J. (2018). "
            '"Overcoming the rate-distance limit of quantum key distribution without quantum repeaters." '
            "Nature, 557, 400-403. "
            "https://doi.org/10.1038/s41586-018-0066-6"
        ),
        (
            "Pirandola, S., Laurenza, R., Ottaviani, C., and Banchi, L. (2017). "
            '"Fundamental limits of repeaterless quantum communications." '
            "Nature Communications, 8, 15043. "
            "https://doi.org/10.1038/ncomms15043"
        ),
        (
            "Scarani, V., Bechmann-Pasquinucci, H., Cerf, N.J., Dusek, M., "
            'Lutkenhaus, N., and Peev, M. (2009). "The security of practical '
            'quantum key distribution." '
            "Reviews of Modern Physics, 81(3), 1301. "
            "https://doi.org/10.1103/RevModPhys.81.1301"
        ),
    ]
    items = "\n".join(f"  <li>{_escape(r)}</li>" for r in refs)
    return (
        '<section class="references">\n'
        "<h2>References</h2>\n"
        f"<ol>\n{items}\n</ol>\n"
        "</section>\n"
    )


# ---------------------------------------------------------------------------
# Plot helpers (inline, no import of visualize.py)
# ---------------------------------------------------------------------------


def _plot_qkd_link(results: Any) -> plt.Figure | None:
    """Create a rate-vs-distance plot for a QKDLinkResult."""
    r_list = getattr(results, "results", [])
    if not r_list:
        return None

    distances = [r.distance_km for r in r_list]
    rates = [max(r.key_rate_bps, 1e-30) for r in r_list]

    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    ax.semilogy(distances, rates, marker="o", linewidth=1.5, color=_PT_COLORS[0])
    ax.set_xlabel("Distance (km)", fontsize=11)
    ax.set_ylabel("Secure Key Rate (bps)", fontsize=11)

    protocol = r_list[0].protocol_name if r_list else ""
    ax.set_title(f"Key Rate vs Distance \u2014 {protocol}", fontsize=13, fontweight="bold")
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


def _plot_protocol_comparison(results: Any) -> plt.Figure | None:
    """Create a multi-protocol overlay plot for ProtocolComparison."""
    protocols = getattr(results, "protocols", {})
    if not protocols:
        return None

    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    for idx, (name, lr) in enumerate(sorted(protocols.items())):
        distances = [r.distance_km for r in lr.results]
        rates = [max(r.key_rate_bps, 1e-30) for r in lr.results]
        color = _PT_COLORS[idx % len(_PT_COLORS)]
        ax.semilogy(distances, rates, marker="o", linewidth=1.5, color=color, label=name)

    ax.set_xlabel("Distance (km)", fontsize=11)
    ax.set_ylabel("Secure Key Rate (bps)", fontsize=11)
    ax.set_title("Protocol Comparison", fontsize=13, fontweight="bold")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, which="both", linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# HTML infrastructure
# ---------------------------------------------------------------------------


def _html_skeleton(title: str, body: str, css: str) -> str:
    """Full HTML page: <!DOCTYPE html>..."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8" />\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1" />\n'
        '  <meta name="generator" content="PhotonsTrust" />\n'
        f"  <title>{_escape(title)}</title>\n"
        f"  <style>\n{css}\n  </style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="container">\n'
        f'  <header>\n    <h1>{_escape(title)}</h1>\n'
        f'    <p class="timestamp">Generated: {timestamp}</p>\n'
        "  </header>\n"
        f"  <main>\n{body}\n  </main>\n"
        '  <footer>\n    <p>Generated by <strong>PhotonsTrust</strong></p>\n  </footer>\n'
        "</div>\n"
        "</body>\n"
        "</html>"
    )


def _default_css() -> str:
    """Inline CSS for clean, printable reports.

    Features:
    - Clean sans-serif font (system fonts)
    - Responsive max-width container
    - Table styling with alternating rows
    - Print-friendly media queries
    - Metric card styling
    - Color scheme matching PT_COLORS from visualize.py
    """
    return """\
/* PhotonsTrust Report Styles */
*, *::before, *::after { box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  line-height: 1.6;
  color: #333;
  background: #f8f9fa;
  margin: 0;
  padding: 0;
}

.container {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
  background: #fff;
}

header {
  background: #1f77b4;
  color: #fff;
  padding: 24px 32px;
  margin: -24px -24px 24px -24px;
  border-bottom: 4px solid #155a8a;
}

header h1 {
  margin: 0 0 4px 0;
  font-size: 1.8rem;
  font-weight: 700;
}

header .timestamp {
  margin: 0;
  font-size: 0.85rem;
  opacity: 0.85;
}

h2 {
  color: #1f77b4;
  border-bottom: 2px solid #e0e0e0;
  padding-bottom: 6px;
  margin-top: 32px;
  font-size: 1.3rem;
}

section {
  margin-bottom: 28px;
}

/* Metric cards */
.metric-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
}

.metric-card {
  flex: 1 1 140px;
  min-width: 120px;
  background: #f0f7ff;
  border: 1px solid #cce0f5;
  border-radius: 8px;
  padding: 14px 18px;
  text-align: center;
}

.metric-label {
  font-size: 0.8rem;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 1.15rem;
  font-weight: 700;
  color: #1f77b4;
  word-break: break-word;
}

/* Tables */
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 12px;
  font-size: 0.9rem;
}

table caption {
  caption-side: top;
  text-align: left;
  font-weight: 600;
  font-size: 0.95rem;
  margin-bottom: 6px;
  color: #555;
}

th, td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

th {
  background: #1f77b4;
  color: #fff;
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

tr:nth-child(even) td {
  background: #f8fafd;
}

tr:hover td {
  background: #eef4fc;
}

/* Plots */
.plot-container {
  text-align: center;
  margin: 16px 0;
}

.plot-container img {
  max-width: 100%;
  height: auto;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
}

/* Methodology & references */
.methodology ul {
  padding-left: 24px;
}

.methodology li {
  margin-bottom: 6px;
}

.references ol {
  padding-left: 24px;
}

.references li {
  margin-bottom: 8px;
  font-size: 0.88rem;
  line-height: 1.5;
}

/* Footer */
footer {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
  text-align: center;
  font-size: 0.8rem;
  color: #999;
}

/* Print styles */
@media print {
  body { background: #fff; }
  .container { max-width: 100%; padding: 0; }
  header {
    background: none !important;
    color: #000 !important;
    border-bottom: 2px solid #000;
    padding: 12px 0;
    margin: 0 0 16px 0;
  }
  header h1 { color: #000; }
  header .timestamp { color: #666; }
  h2 { color: #000; }
  .metric-card {
    background: #fff !important;
    border: 1px solid #ccc;
  }
  .metric-value { color: #000; }
  th { background: #ddd !important; color: #000 !important; }
  tr:hover td { background: inherit; }
  footer { display: none; }
}"""


def _figure_to_base64(fig: Any) -> str:
    """Convert matplotlib Figure to base64 PNG data URI."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("ascii")
    buf.close()
    return f"data:image/png;base64,{encoded}"


def _render_table(
    headers: list[str],
    rows: list[list[str]],
    caption: str = "",
) -> str:
    """HTML table builder."""
    parts: list[str] = ['<table>']
    if caption:
        parts.append(f"  <caption>{_escape(caption)}</caption>")
    parts.append("  <thead>")
    parts.append("    <tr>")
    for h in headers:
        parts.append(f"      <th>{_escape(h)}</th>")
    parts.append("    </tr>")
    parts.append("  </thead>")
    parts.append("  <tbody>")
    for row in rows:
        parts.append("    <tr>")
        for cell in row:
            parts.append(f"      <td>{_escape(cell)}</td>")
        parts.append("    </tr>")
    parts.append("  </tbody>")
    parts.append("</table>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """Escape HTML special characters."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _format_rate(bps: float | None) -> str:
    """Pretty-print a key rate value."""
    if bps is None or not math.isfinite(bps) or bps <= 0:
        return "0 bps"
    if bps >= 1e9:
        return f"{bps / 1e9:.2f} Gbps"
    if bps >= 1e6:
        return f"{bps / 1e6:.2f} Mbps"
    if bps >= 1e3:
        return f"{bps / 1e3:.2f} kbps"
    return f"{bps:.1f} bps"
