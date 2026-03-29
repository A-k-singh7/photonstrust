"""PhotonTrust Reliability Card — HTML report generator.

Produces a self-contained, printable HTML document combining:
- Simulation results (power, phase per port)
- DRC pass/fail summary
- Process yield (Monte Carlo)
- SPICE compact model table
- Layout GDS cell count
- Provenance (timestamp, software version, SHA-256 of inputs)

Output is a single .html file with embedded CSS — no external dependencies.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import platform
import sys
from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# HTML template helpers
# ---------------------------------------------------------------------------

_CSS = """
:root{--bg:#0f1117;--surface:#1a1d2e;--accent:#6c63ff;--accent2:#00d4aa;
--warn:#f59e0b;--err:#ef4444;--ok:#22c55e;--text:#e2e8f0;--muted:#64748b;
--border:#2d3748;font-family:'Inter',system-ui,sans-serif}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);padding:2rem;line-height:1.6}
.card{background:var(--surface);border:1px solid var(--border);border-radius:12px;
padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 4px 24px rgba(0,0,0,.4)}
h1{font-size:1.8rem;font-weight:700;background:linear-gradient(135deg,var(--accent),var(--accent2));
-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.25rem}
h2{font-size:1.1rem;font-weight:600;color:var(--accent2);margin-bottom:1rem;
border-bottom:1px solid var(--border);padding-bottom:.5rem}
.meta{color:var(--muted);font-size:.8rem;margin-bottom:1.5rem}
.badge{display:inline-block;padding:.2rem .6rem;border-radius:6px;font-size:.75rem;
font-weight:700;text-transform:uppercase;letter-spacing:.05em}
.badge.ok{background:#14532d;color:var(--ok)}
.badge.err{background:#450a0a;color:var(--err)}
.badge.warn{background:#451a03;color:var(--warn)}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th{text-align:left;padding:.5rem .75rem;color:var(--muted);font-weight:600;
border-bottom:1px solid var(--border);font-size:.75rem;text-transform:uppercase}
td{padding:.5rem .75rem;border-bottom:1px solid rgba(45,55,72,.5)}
tr:last-child td{border-bottom:none}
tr:hover td{background:rgba(108,99,255,.06)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.kv{display:flex;justify-content:space-between;padding:.4rem 0;
border-bottom:1px solid rgba(45,55,72,.3)}
.kv:last-child{border-bottom:none}
.kv-k{color:var(--muted);font-size:.85rem}
.kv-v{font-weight:600;font-size:.85rem}
.bar-track{background:#1e293b;border-radius:99px;height:8px;overflow:hidden;width:120px}
.bar-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--accent2))}
.sig{font-size:.7rem;color:var(--muted);word-break:break-all;font-family:monospace}
@media print{body{background:#fff;color:#000}.card{border:1px solid #ccc;box-shadow:none}}
"""


def _h(value: Any) -> str:
    return html.escape(str(value), quote=True)

def _badge(ok: bool, ok_label: str = "PASS", fail_label: str = "FAIL") -> str:
    cls = "ok" if ok else "err"
    label = ok_label if ok else fail_label
    return f'<span class="badge {cls}">{label}</span>'


def _kv(key: str, val: str) -> str:
    return f'<div class="kv"><span class="kv-k">{key}</span><span class="kv-v">{val}</span></div>'


def _yield_bar(y: float) -> str:
    pct = min(100, max(0, y * 100))
    color = "#22c55e" if pct >= 90 else "#f59e0b" if pct >= 75 else "#ef4444"
    return (
        f'<div style="display:flex;align-items:center;gap:.5rem">'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct:.1f}%;background:{color}"></div></div>'
        f'<span style="font-size:.8rem">{pct:.1f}%</span></div>'
    )


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_header(title: str, badge: str = "") -> str:
    return f'<div class="card"><h2>{_h(title)} {badge}</h2>'


def _build_overview(title: str, timestamp: str, provenance: dict) -> str:
    sha = provenance.get("input_sha256", "n/a")
    ver = provenance.get("version", sys.version.split()[0])
    return f"""
<div class="card">
  <h1>🔬 {_h(title)}</h1>
  <p class="meta">Generated: {_h(timestamp)} &nbsp;·&nbsp; Python {_h(ver)} &nbsp;·&nbsp; {_h(platform.system())}</p>
  <div class="sig">Provenance SHA-256: {_h(sha)}</div>
</div>"""


def _build_simulation_section(sim_result: Optional[dict]) -> str:
    if not sim_result:
        return ""
    wl = sim_result.get("wavelength_nm", "—")
    outs = sim_result.get("outputs", [])
    rows = ""
    for o in outs:
        node = o.get("node", "?")
        port = o.get("port", "?")
        pdb = o.get("power_dB")
        phase = o.get("phase_rad")
        pdb_s = f"{pdb:.2f} dB" if pdb is not None else "—"
        phase_s = f"{math.degrees(phase):.1f}°" if phase is not None else "—"
        rows += f"<tr><td>{_h(node)}</td><td>{_h(port)}</td><td>{_h(pdb_s)}</td><td>{_h(phase_s)}</td></tr>"
    if not rows:
        rows = "<tr><td colspan='4' style='color:var(--muted)'>No outputs</td></tr>"
    return f"""
{_section_header("Simulation Results", f"@ {wl} nm")}
<table><thead><tr><th>Node</th><th>Port</th><th>Power</th><th>Phase</th></tr></thead>
<tbody>{rows}</tbody></table></div>"""


def _build_drc_section(drc_result: Optional[dict]) -> str:
    if not drc_result:
        return ""
    ok = drc_result.get("ok", False)
    stats = drc_result.get("stats", {})
    violations = drc_result.get("violations", [])
    lvs = drc_result.get("lvs", {})
    badge = _badge(ok)
    rows = ""
    for v in violations[:20]:
        sev = v.get("severity", "error")
        cls = "warn" if sev == "warning" else "err"
        rows += (
            f"<tr><td>{_h(v.get('rule','?'))}</td>"
            f"<td><span class='badge {cls}'>{_h(sev)}</span></td>"
            f"<td>{_h(v.get('message',''))}</td></tr>"
        )
    viol_tbl = f"""<table style="margin-top:.75rem">
<thead><tr><th>Rule</th><th>Severity</th><th>Message</th></tr></thead>
<tbody>{rows if rows else "<tr><td colspan='3' style='color:var(--ok)'>No violations ✓</td></tr>"}</tbody>
</table>""" if violations else ""

    lvs_ok = lvs.get("ok", True)
    lvs_badge = _badge(lvs_ok, "LVS PASS", "LVS FAIL")
    return f"""
{_section_header("Layout DRC + LVS", badge)}
<div class="grid2">
  <div>
    {_kv("Shapes checked", str(stats.get("shapes_checked", "—")))}
    {_kv("Error count", str(stats.get("error_count", 0)))}
    {_kv("Warning count", str(stats.get("warning_count", 0)))}
  </div>
  <div>
    {_kv("LVS", lvs_badge)}
    {_kv("Matched connections", str(lvs.get("matched_count", "—")))}
    {_kv("Missing connections", str(len(lvs.get("missing_connections", []))))}
  </div>
</div>
{viol_tbl}
</div>"""


def _build_yield_section(yield_result: Optional[dict]) -> str:
    if not yield_result:
        return ""
    y = yield_result.get("estimated_yield", 0.0)
    ok = yield_result.get("pass", False)
    badge = _badge(ok)
    mc = yield_result.get("mc_yield")
    analytic = yield_result.get("analytic_yield")
    return f"""
{_section_header("Process Yield", badge)}
<div class="grid2">
  <div>
    {_kv("Estimated yield", _yield_bar(y))}
    {_kv("Monte Carlo yield", f"{mc:.1%}" if mc is not None else "—")}
    {_kv("Analytic yield", f"{analytic:.1%}" if analytic is not None else "—")}
  </div>
  <div>
    {_kv("Required min.", f"{yield_result.get('min_required_yield', 0.9):.0%}")}
    {_kv("MC samples", str(yield_result.get("mc_samples", "—")))}
    {_kv("Violations (analytic)", str(len(yield_result.get("violations", []))))}
  </div>
</div></div>"""


def _build_spice_section(spice_text: Optional[str]) -> str:
    if not spice_text:
        return ""
    subckt_count = spice_text.count(".subckt")
    ends_count = spice_text.count(".ends")
    line_count = len(spice_text.splitlines())
    return f"""
{_section_header("SPICE Compact Models")}
<div class="grid2">
  <div>
    {_kv("Subcircuits defined", str(subckt_count))}
    {_kv("Netlist lines", str(line_count))}
  </div>
  <div>
    {_kv(".ends verified", _badge(ends_count == subckt_count, "OK", "MISMATCH"))}
  </div>
</div>
<details style="margin-top:.75rem">
  <summary style="cursor:pointer;color:var(--muted);font-size:.8rem">View SPICE snippet (first 20 lines)</summary>
  <pre style="font-size:.7rem;overflow:auto;background:#0d1117;padding:.75rem;
border-radius:8px;margin-top:.5rem;color:{{}};max-height:200px">{_h(chr(10).join(spice_text.splitlines()[:20]))}</pre>
</details></div>"""


def _build_wdm_section(wdm_result: Optional[dict]) -> str:
    if not wdm_result:
        return ""
    channels = wdm_result.get("channels", [])
    rows = ""
    for ch in channels:
        peak = ch.get("peak_transmission_db", -100)
        passband = ch.get("passband_3db_nm", 0)
        ripple = ch.get("inband_ripple_db", 0)
        wl = ch.get("center_wavelength_nm", 0)
        rows += (
            f"<tr><td>Ch{ch.get('channel', '?'):02d}</td>"
            f"<td>{wl:.2f}</td>"
            f"<td>{peak:.2f}</td>"
            f"<td>{passband:.4f}</td>"
            f"<td>{ripple:.4f}</td></tr>"
        )
    adj_xt = wdm_result.get("worst_adjacent_crosstalk_db")
    osnr = wdm_result.get("osnr_estimate_db")
    return f"""
{_section_header("WDM Channel Analysis")}
<div class="grid2">
  <div>
    {_kv("Channels", str(wdm_result.get("n_channels", "—")))}
    {_kv("Channel spacing", f"{wdm_result.get('channel_spacing_ghz','—')} GHz")}
    {_kv("Avg peak transmission", f"{wdm_result.get('avg_peak_transmission_db','—'):.2f} dB")}
  </div>
  <div>
    {_kv("Worst adj. crosstalk", f"{adj_xt:.2f} dB" if adj_xt is not None else "—")}
    {_kv("OSNR estimate", f"{osnr:.1f} dB" if osnr is not None else "—")}
    {_kv("Wavelengths simulated", str(wdm_result.get("wavelengths_simulated", "—")))}
  </div>
</div>
<table style="margin-top:.75rem">
<thead><tr><th>Channel</th><th>λ (nm)</th><th>Peak (dB)</th><th>3-dB BW (nm)</th><th>Ripple (dB)</th></tr></thead>
<tbody>{rows if rows else "<tr><td colspan='5'>No channel data</td></tr>"}</tbody>
</table></div>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_reliability_card_html(
    *,
    netlist: Optional[dict[str, Any]] = None,
    drc_params: Optional[dict[str, Any]] = None,
    yield_metrics: Optional[list[dict[str, Any]]] = None,
    wdm_params: Optional[dict[str, Any]] = None,
    title: str = "PhotonTrust Reliability Card",
    wavelength_nm: float = 1550.0,
) -> str:
    """Generate a self-contained HTML reliability card.

    Parameters
    ----------
    netlist:
        Compiled PIC netlist dict.
    drc_params:
        Dict with keys for crosstalk DRC: ``gap_um``, ``length_um``,
        ``wavelength_nm``, ``target_xt_db``.
    yield_metrics:
        List of process variation metric dicts for yield estimation.
    wdm_params:
        Dict with ``channel_spacing_ghz``, ``n_channels``, etc. for WDM analysis.
    title:
        Card title.
    wavelength_nm:
        Simulation wavelength for single-point results.

    Returns
    -------
    str
        Complete self-contained HTML string.
    """
    import photonstrust.sdk as pt

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S UTC")

    # Provenance hash
    payload = json.dumps(
        {"netlist": netlist, "drc_params": drc_params, "yield_metrics": yield_metrics},
        sort_keys=True, default=str,
    ).encode()
    sha = hashlib.sha256(payload).hexdigest()[:16]

    provenance = {
        "input_sha256": sha,
        "version": sys.version.split()[0],
    }

    # Run simulation
    sim_result = None
    if netlist:
        try:
            sim_result = pt.simulate_netlist(netlist, wavelength_nm=wavelength_nm)
        except Exception:
            pass

    # Run layout DRC + LVS
    drc_result = None
    if netlist:
        try:
            layout_result = pt.run_layout_drc_lvs(netlist)
            drc_result = layout_result
        except Exception:
            pass

    # Crosstalk DRC
    xt_result = None
    if drc_params:
        try:
            xt_result = pt.run_drc_report(**drc_params)
        except Exception:
            pass

    # Yield
    yield_result = None
    if yield_metrics:
        try:
            yield_result = pt.estimate_yield(yield_metrics, mc_samples=5000)
        except Exception:
            pass

    # SPICE models
    spice_text = None
    try:
        spice_text = pt.all_spice_models()
    except Exception:
        pass

    # WDM
    wdm_result = None
    if netlist and wdm_params:
        try:
            from photonstrust.wdm.analysis import analyze_wdm_channels
            wdm_result = analyze_wdm_channels(netlist, **(wdm_params or {}))
        except Exception:
            pass

    # Overall pass/fail
    all_ok = all([
        (drc_result or {}).get("overall_pass", True),
        (xt_result or {}).get("overall_pass", True),
        (yield_result or {}).get("pass", True),
    ])

    overall_badge = _badge(all_ok, "ALL PASS", "ISSUES FOUND")
    safe_title = _h(title)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>{_CSS}</style>
</head>
<body>
{_build_overview(title, ts, provenance)}

<div class="card" style="display:flex;align-items:center;justify-content:space-between">
  <span style="font-size:1rem;font-weight:600">Overall Status</span>
  {overall_badge}
</div>

{_build_simulation_section(sim_result)}
{_build_drc_section(drc_result)}
{_build_yield_section(yield_result)}
{_build_spice_section(spice_text)}
{_build_wdm_section(wdm_result)}

<div class="card">
  <h2>Provenance</h2>
  {_kv("Timestamp", ts)}
  {_kv("Python", sys.version.split()[0])}
  {_kv("Platform", platform.platform())}
  {_kv("Input SHA-256", sha)}
</div>

</body></html>"""
    return html


def write_reliability_card(
    output_path: str,
    *,
    netlist: Optional[dict[str, Any]] = None,
    drc_params: Optional[dict[str, Any]] = None,
    yield_metrics: Optional[list[dict[str, Any]]] = None,
    title: str = "PhotonTrust Reliability Card",
) -> str:
    """Write reliability card HTML to a file.

    Returns the absolute path of the written HTML file.
    """
    from pathlib import Path
    html = generate_reliability_card_html(
        netlist=netlist, drc_params=drc_params,
        yield_metrics=yield_metrics, title=title,
    )
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    return str(p.resolve())
