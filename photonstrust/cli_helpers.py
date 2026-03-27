"""CLI formatting and interactive helpers."""

from __future__ import annotations

import json
from typing import Any


def format_table(headers: list[str], rows: list[list[str]], *, title: str = "") -> str:
    """Plain-text table with column alignment."""
    if not headers:
        return ""

    # Calculate column widths (minimum of header width or widest cell)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    def _row_line(cells: list[str]) -> str:
        parts = []
        for i, cell in enumerate(cells):
            width = col_widths[i] if i < len(col_widths) else len(str(cell))
            parts.append(f" {str(cell):<{width}} ")
        return "|" + "|".join(parts) + "|"

    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"

    lines: list[str] = []
    if title:
        lines.append(title)
        lines.append("")
    lines.append(separator)
    lines.append(_row_line(headers))
    lines.append(separator)
    for row in rows:
        # Pad row to match header count
        padded = list(row) + [""] * (len(headers) - len(row))
        lines.append(_row_line(padded))
    lines.append(separator)
    return "\n".join(lines)


def try_rich_table(
    headers: list[str], rows: list[list[str]], *, title: str = ""
) -> str | None:
    """Try to render with ``rich`` if available, else return None."""
    try:
        from rich.console import Console
        from rich.table import Table
        import io

        table = Table(title=title or None)
        for h in headers:
            table.add_column(h)
        for row in rows:
            table.add_row(*[str(c) for c in row])

        buf = io.StringIO()
        console = Console(file=buf, force_terminal=False, width=120)
        console.print(table)
        return buf.getvalue()
    except ImportError:
        return None


def print_table(
    headers: list[str], rows: list[list[str]], *, title: str = ""
) -> None:
    """Print table using rich if available, otherwise plain text."""
    rich_output = try_rich_table(headers, rows, title=title)
    if rich_output is not None:
        try:
            print(rich_output, end="")
        except UnicodeEncodeError:
            # Fallback for terminals that cannot render rich Unicode (e.g. Windows cp1252)
            print(format_table(headers, rows, title=title))
    else:
        print(format_table(headers, rows, title=title))


def print_result_summary(result: Any) -> None:
    """Pretty-print any result object that has a ``.summary()`` method."""
    if hasattr(result, "summary"):
        print(result.summary())
    elif isinstance(result, dict):
        print(json.dumps(result, indent=2, default=str))
    else:
        print(str(result))


def prompt_choice(prompt: str, options: list[str], default: str = "") -> str:
    """Interactive choice with validation."""
    print(prompt)
    for i, opt in enumerate(options, 1):
        marker = " (default)" if opt == default else ""
        print(f"  {i}. {opt}{marker}")
    while True:
        raw = input("> ").strip()
        if not raw and default:
            return default
        # Accept by number
        try:
            idx = int(raw)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        except ValueError:
            pass
        # Accept by name (case-insensitive)
        lower = raw.lower()
        for opt in options:
            if opt.lower() == lower:
                return opt
        print(f"Invalid choice. Enter 1-{len(options)} or a name from the list.")


def prompt_float(prompt: str, default: float = 0.0) -> float:
    """Float input with validation and default."""
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            print("Please enter a valid number.")
