"""HTML report generation for performance DRC checks."""

from __future__ import annotations


def render_performance_drc_html(report: dict) -> str:
    check = report.get("check", {}) or {}
    inputs = (check.get("inputs", {}) or {}) if isinstance(check, dict) else {}
    results = report.get("results", {}) or {}
    layout = results.get("layout", {}) or {}
    layout = layout if isinstance(layout, dict) else {}
    routes = inputs.get("routes", None)
    route_count = len(routes) if isinstance(routes, list) else None

    kind = str(check.get("kind", "performance_drc")).strip() or "performance_drc"
    status = str(results.get("status", "unknown")).strip().lower()
    worst_xt = results.get("worst_xt_db")
    worst_margin = results.get("worst_margin_db")
    rec_gap = results.get("recommended_min_gap_um")

    points = results.get("points", []) or []
    rows = []
    for p in points:
        if not isinstance(p, dict):
            continue
        wl = p.get("wavelength_nm")
        xt = p.get("xt_db")
        margin = p.get("margin_db")
        passed = p.get("pass")
        rows.append(
            "<tr>"
            f"<td>{_fmt(wl, 3)}</td>"
            f"<td>{_fmt(xt, 3)}</td>"
            f"<td>{_fmt(margin, 3) if margin is not None else ''}</td>"
            f"<td>{'pass' if passed else ('fail' if passed is False else '')}</td>"
            "</tr>"
        )
    table_html = (
        "<table><thead><tr><th>wavelength (nm)</th><th>xt (dB)</th><th>margin (dB)</th><th>status</th></tr></thead>"
        f"<tbody>{''.join(rows) if rows else '<tr><td colspan=4>(no points)</td></tr>'}</tbody></table>"
    )

    loss_budget = results.get("loss_budget") if isinstance(results.get("loss_budget"), dict) else None
    loss_routes = loss_budget.get("routes", []) if isinstance(loss_budget, dict) else []
    loss_rows = []
    for route in loss_routes:
        if not isinstance(route, dict):
            continue
        loss_rows.append(
            "<tr>"
            f"<td>{_esc(route.get('route_id', ''))}</td>"
            f"<td>{_fmt(route.get('length_um'), 2)}</td>"
            f"<td>{_fmt(route.get('bend_count'), 0)}</td>"
            f"<td>{_fmt(route.get('crossing_count'), 0)}</td>"
            f"<td>{_fmt(route.get('propagation_loss_db'), 4)}</td>"
            f"<td>{_fmt(route.get('bend_loss_db'), 4)}</td>"
            f"<td>{_fmt(route.get('crossing_loss_db'), 4)}</td>"
            f"<td>{_fmt(route.get('route_loss_db'), 4)}</td>"
            f"<td>{_esc(route.get('risk_level', ''))}</td>"
            f"<td>{'pass' if route.get('pass') else 'fail'}</td>"
            "</tr>"
        )
    loss_table_html = (
        "<table><thead><tr>"
        "<th>route</th><th>length (um)</th><th>bends</th><th>crossings</th>"
        "<th>prop loss (dB)</th><th>bend loss (dB)</th><th>crossing loss (dB)</th><th>route loss (dB)</th>"
        "<th>risk</th><th>status</th></tr></thead>"
        f"<tbody>{''.join(loss_rows) if loss_rows else '<tr><td colspan=10>(no route metrics)</td></tr>'}</tbody></table>"
    )

    violations = results.get("violations", []) or []
    violation_rows = []
    for v in violations:
        if not isinstance(v, dict):
            continue
        violation_rows.append(
            "<tr>"
            f"<td><code>{_esc(v.get('id', ''))}</code></td>"
            f"<td>{_esc(v.get('code', ''))}</td>"
            f"<td>{_esc(v.get('severity', ''))}</td>"
            f"<td>{_esc(v.get('applicability', ''))}</td>"
            f"<td>{_esc(v.get('entity_ref', ''))}</td>"
            f"<td>{_esc(v.get('message', ''))}</td>"
            "</tr>"
        )
    violations_table_html = (
        "<table><thead><tr><th>id</th><th>code</th><th>severity</th><th>applicability</th>"
        "<th>entity</th><th>message</th></tr></thead>"
        f"<tbody>{''.join(violation_rows) if violation_rows else '<tr><td colspan=6>(no violations)</td></tr>'}</tbody></table>"
    )

    violation_summary = results.get("violation_summary") if isinstance(results.get("violation_summary"), dict) else {}

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>PhotonTrust Performance DRC</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #6b7280;
      --panel: #ffffff;
      --line: #e5e7eb;
      --ok: #0f766e;
      --fail: #b42318;
      --warn: #b54708;
      --bg: #f8fafc;
    }}
    body {{
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      margin: 28px;
      color: var(--ink);
      background: radial-gradient(circle at 20% 10%, #eef2ff 0%, var(--bg) 45%, #ffffff 100%);
    }}
    h1 {{ margin: 0 0 6px 0; font-size: 24px; }}
    .subtle {{ color: var(--muted); margin: 0 0 18px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }}
    .label {{ font-weight: 700; margin-bottom: 8px; }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 12px;
    }}
    .pill.ok {{ background: rgba(15, 118, 110, 0.12); color: var(--ok); }}
    .pill.fail {{ background: rgba(180, 35, 24, 0.12); color: var(--fail); }}
    .pill.warn {{ background: rgba(181, 71, 8, 0.12); color: var(--warn); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px 6px; text-align: left; }}
    th {{ color: var(--muted); font-weight: 700; }}
    .kv {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px 12px; }}
    .kv div:nth-child(odd) {{ color: var(--muted); }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
  </style>
</head>
<body>
  <h1>Performance DRC</h1>
  <p class="subtle">Check: <code>{_esc(kind)}</code></p>

  <div class="grid">
    <div class="card">
      <div class="label">Summary</div>
      <span class="pill {('ok' if status=='pass' else ('fail' if status=='fail' else 'warn'))}">{_esc(status)}</span>
      <div style="height:10px"></div>
      <div class="kv">
        <div>worst xt (dB)</div><div>{_fmt(worst_xt, 3)}</div>
        <div>worst margin (dB)</div><div>{_fmt(worst_margin, 3) if worst_margin is not None else ''}</div>
        <div>recommended min gap (um)</div><div>{_fmt(rec_gap, 4) if rec_gap is not None else ''}</div>
        <div>violations</div><div>{_fmt(violation_summary.get('total'), 0)}</div>
        <div>blocking violations</div><div>{_fmt(violation_summary.get('blocking'), 0)}</div>
      </div>
    </div>
    <div class="card">
      <div class="label">Inputs</div>
      <div class="kv">
        <div>gap (um)</div><div>{_fmt(inputs.get('gap_um'), 4)}</div>
        <div>parallel length (um)</div><div>{_fmt(inputs.get('parallel_length_um'), 2)}</div>
        <div>target xt (dB)</div><div>{_fmt(inputs.get('target_xt_db'), 2) if inputs.get('target_xt_db') is not None else ''}</div>
        <div>routes</div><div>{route_count if route_count is not None else ''}</div>
        <div>parallel runs</div><div>{_fmt(layout.get('parallel_runs_count'), 0) if layout.get('parallel_runs_count') is not None else ''}</div>
        <div>min extracted gap (um)</div><div>{_fmt(layout.get('min_gap_um'), 4) if layout.get('min_gap_um') is not None else ''}</div>
        <div>max parallel length (um)</div><div>{_fmt(layout.get('max_parallel_length_um'), 2) if layout.get('max_parallel_length_um') is not None else ''}</div>
      </div>
    </div>
  </div>

  <div class="card" style="margin-top: 14px;">
    <div class="label">Points</div>
    {table_html}
  </div>

  <div class="card" style="margin-top: 14px;">
    <div class="label">Loss Budget</div>
    <div class="kv" style="margin-bottom: 10px;">
      <div>loss pass</div><div>{'pass' if (isinstance(loss_budget, dict) and loss_budget.get('pass')) else ('fail' if isinstance(loss_budget, dict) else '')}</div>
      <div>route count</div><div>{_fmt((loss_budget or {}).get('route_count'), 0) if isinstance(loss_budget, dict) else ''}</div>
      <div>worst route</div><div>{_esc((loss_budget or {}).get('worst_route_id', '')) if isinstance(loss_budget, dict) else ''}</div>
      <div>worst route loss (dB)</div><div>{_fmt((loss_budget or {}).get('worst_route_loss_db'), 4) if isinstance(loss_budget, dict) else ''}</div>
    </div>
    {loss_table_html}
  </div>

  <div class="card" style="margin-top: 14px;">
    <div class="label">Annotated Violations</div>
    {violations_table_html}
  </div>
</body>
</html>
"""


def _esc(value: object) -> str:
    s = str(value)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\"", "&quot;")
        .replace("'", "&#39;")
    )


def _fmt(value: object, digits: int) -> str:
    try:
        x = float(value)  # type: ignore[arg-type]
    except Exception:
        return ""
    if x != x or x == float("inf") or x == float("-inf"):
        return ""
    return f"{x:.{int(digits)}f}"
