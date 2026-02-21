"""Interactive DRC wizard – photonstrust drc <path> [options]

Usage examples
--------------
  photonstrust-drc pic_chain.json
  photonstrust-drc pic_chain.json --gap 1.2 --length 150 --wavelength 1310
  photonstrust-drc --gap 1.2 --length 150 --wavelength 1550 --target -30
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text


def _crosstalk_check(
    gap_um: float,
    length_um: float,
    wavelength_nm: float,
    target_xt_db: float,
) -> dict:
    from photonstrust.components.pic.crosstalk import (
        predict_parallel_waveguide_xt_db,
        recommended_min_gap_um,
    )

    actual_xt = predict_parallel_waveguide_xt_db(
        gap_um=gap_um,
        parallel_length_um=length_um,
        wavelength_nm=wavelength_nm,
    )
    min_gap = recommended_min_gap_um(
        target_xt_db=target_xt_db,
        parallel_length_um=length_um,
        wavelength_nm=wavelength_nm,
    )
    passed = actual_xt <= target_xt_db
    return {
        "gap_um": gap_um,
        "length_um": length_um,
        "wavelength_nm": wavelength_nm,
        "actual_xt_db": actual_xt,
        "target_xt_db": target_xt_db,
        "recommended_min_gap_um": min_gap,
        "pass": passed,
    }


def _yield_check(netlist_path: Path, samples: int) -> Optional[dict]:
    try:
        from photonstrust.pic.layout.verification.core import estimate_process_yield
    except ImportError:
        return None

    payload = json.loads(netlist_path.read_text(encoding="utf-8"))
    metrics = payload.get("process_metrics")
    if not metrics:
        return None

    return estimate_process_yield(
        metrics=metrics,
        monte_carlo_samples=samples,
    )


def _print_drc_table(console: Console, checks: list[dict]) -> None:
    table = Table(
        title="⚛ PhotonTrust Performance DRC Report",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    table.add_column("Check", style="bold")
    table.add_column("Value", justify="right")
    table.add_column("Target", justify="right")
    table.add_column("Margin", justify="right")
    table.add_column("Status", justify="center")

    all_pass = True
    for c in checks:
        actual = c["actual_xt_db"]
        target = c["target_xt_db"]
        margin = actual - target
        passed = c["pass"]
        all_pass = all_pass and passed

        status_text = Text("✅ PASS", style="bold green") if passed else Text("❌ FAIL", style="bold red")
        margin_style = "green" if margin <= 0 else "red"
        table.add_row(
            f"Crosstalk @ gap={c['gap_um']}µm len={c['length_um']}µm λ={c['wavelength_nm']}nm",
            f"{actual:.2f} dB",
            f"{target:.2f} dB",
            Text(f"{margin:+.2f} dB", style=margin_style),
            status_text,
        )
        table.add_row(
            "  └─ Recommended min gap",
            f"{c['recommended_min_gap_um']:.2f} µm",
            "", "", "",
        )

    console.print()
    console.print(table)
    console.print()

    if all_pass:
        console.print(Panel("[bold green]✅  All DRC checks passed.[/bold green]", border_style="green"))
    else:
        console.print(Panel("[bold red]❌  One or more DRC violations detected.[/bold red]", border_style="red"))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="photonstrust-drc",
        description="Interactive Performance DRC Wizard – layout crosstalk + process yield analysis",
    )
    parser.add_argument("netlist", nargs="?", help="Path to compiled netlist or process_metrics JSON")
    parser.add_argument("--gap", type=float, default=1.0, help="Waveguide gap (µm), default=1.0")
    parser.add_argument("--length", type=float, default=100.0, help="Parallel run length (µm), default=100.0")
    parser.add_argument("--wavelength", type=float, default=1550.0, help="Wavelength (nm), default=1550.0")
    parser.add_argument("--target", type=float, default=-30.0, help="Crosstalk target (dB), default=-30.0")
    parser.add_argument("--mc-samples", type=int, default=5000, help="Monte Carlo samples for yield, default=5000")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Emit JSON instead of rich table")

    args = parser.parse_args()
    console = Console()

    checks = []
    yield_result = None

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        t = progress.add_task("Running crosstalk DRC...", total=None)
        try:
            checks.append(_crosstalk_check(
                gap_um=args.gap,
                length_um=args.length,
                wavelength_nm=args.wavelength,
                target_xt_db=args.target,
            ))
        except Exception as exc:
            progress.stop()
            console.print(f"[red]Crosstalk check failed: {exc}[/red]")
            raise SystemExit(1) from exc

        progress.update(t, description="Running yield Monte Carlo...")
        if args.netlist:
            try:
                yield_result = _yield_check(Path(args.netlist), samples=args.mc_samples)
            except Exception as exc:
                console.print(f"[yellow]Yield check skipped: {exc}[/yellow]")

        progress.stop()

    if args.json_out:
        out = {"crosstalk_checks": checks}
        if yield_result:
            out["yield"] = yield_result
        print(json.dumps(out, indent=2))
        raise SystemExit(0 if all(c["pass"] for c in checks) else 1)

    _print_drc_table(console, checks)

    if yield_result:
        y = yield_result
        yval = y.get("estimated_yield", 0.0)
        req = y.get("min_required_yield", 0.9)
        y_pass = y.get("pass", False)

        yt = Table(title="Process Yield", box=box.SIMPLE_HEAVY, header_style="bold cyan")
        yt.add_column("Metric")
        yt.add_column("Value", justify="right")
        yt.add_row("Estimated Yield", Text(f"{yval:.2%}", style="green" if y_pass else "red"))
        yt.add_row("Required Yield", f"{req:.2%}")
        yt.add_row("Status", Text("PASS ✅" if y_pass else "FAIL ❌", style="green" if y_pass else "red"))
        console.print(yt)

    all_pass = all(c["pass"] for c in checks)
    if yield_result:
        all_pass = all_pass and yield_result.get("pass", False)

    raise SystemExit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
