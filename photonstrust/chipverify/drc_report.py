"""Human-readable DRC report rendering."""
from __future__ import annotations


def render_drc_report(
    drc_result: dict,
    format: str = "text",
) -> str:
    """Render DRC results in human-readable format.

    Parameters
    ----------
    drc_result : dict
        DRC result with keys: "violations" (list of dicts), "summary", "pass"
    format : str
        "text", "markdown", or "html"
    """
    violations = drc_result.get("violations", [])
    summary = drc_result.get("summary", {})
    passed = drc_result.get("pass", len(violations) == 0)

    if format == "markdown":
        return _render_markdown(violations, summary, passed)
    elif format == "html":
        return _render_html(violations, summary, passed)
    else:
        return _render_text(violations, summary, passed)


def _group_by_severity(violations: list[dict]) -> dict[str, list[dict]]:
    """Group violations by severity level."""
    groups: dict[str, list[dict]] = {"error": [], "warning": [], "info": []}
    for v in violations:
        sev = v.get("severity", "warning").lower()
        if sev not in groups:
            groups[sev] = []
        groups[sev].append(v)
    return groups


def _render_text(violations, summary, passed):
    lines = []
    status = "PASS" if passed else "FAIL"
    lines.append(f"DRC Report — {status}")
    lines.append("=" * 40)

    if summary:
        lines.append(f"Total checks: {summary.get('total_checks', 'N/A')}")
        lines.append(f"Violations: {len(violations)}")

    if not violations:
        lines.append("No violations found.")
        return "\n".join(lines)

    groups = _group_by_severity(violations)
    for severity in ["error", "warning", "info"]:
        vlist = groups.get(severity, [])
        if not vlist:
            continue
        lines.append(f"\n[{severity.upper()}] ({len(vlist)} violations)")
        lines.append("-" * 30)
        for v in vlist:
            rule = v.get("rule", "unknown")
            msg = v.get("message", "")
            loc = v.get("location", "")
            lines.append(f"  {rule}: {msg}")
            if loc:
                lines.append(f"    at {loc}")

    return "\n".join(lines)


def _render_markdown(violations, summary, passed):
    lines = []
    status = "PASS" if passed else "FAIL"
    lines.append(f"# DRC Report — {status}")
    lines.append("")

    if summary:
        lines.append(f"- **Total checks**: {summary.get('total_checks', 'N/A')}")
        lines.append(f"- **Violations**: {len(violations)}")
        lines.append("")

    if not violations:
        lines.append("No violations found.")
        return "\n".join(lines)

    groups = _group_by_severity(violations)
    for severity in ["error", "warning", "info"]:
        vlist = groups.get(severity, [])
        if not vlist:
            continue
        lines.append(f"## {severity.upper()} ({len(vlist)})")
        lines.append("")
        lines.append("| Rule | Message | Location |")
        lines.append("|------|---------|----------|")
        for v in vlist:
            rule = v.get("rule", "unknown")
            msg = v.get("message", "")
            loc = v.get("location", "")
            lines.append(f"| {rule} | {msg} | {loc} |")
        lines.append("")

    return "\n".join(lines)


def _render_html(violations, summary, passed):
    status = "PASS" if passed else "FAIL"
    color = "green" if passed else "red"

    html = [f'<h1 style="color:{color}">DRC Report — {status}</h1>']

    if summary:
        html.append(f'<p>Total checks: {summary.get("total_checks", "N/A")}, '
                     f'Violations: {len(violations)}</p>')

    if not violations:
        html.append("<p>No violations found.</p>")
        return "\n".join(html)

    groups = _group_by_severity(violations)
    for severity in ["error", "warning", "info"]:
        vlist = groups.get(severity, [])
        if not vlist:
            continue
        html.append(f"<h2>{severity.upper()} ({len(vlist)})</h2>")
        html.append("<table border='1'><tr><th>Rule</th><th>Message</th><th>Location</th></tr>")
        for v in vlist:
            rule = v.get("rule", "unknown")
            msg = v.get("message", "")
            loc = v.get("location", "")
            html.append(f"<tr><td>{rule}</td><td>{msg}</td><td>{loc}</td></tr>")
        html.append("</table>")

    return "\n".join(html)
