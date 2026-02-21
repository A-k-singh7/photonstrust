"""PhotonTrust: Clean Notebook & Scripting Python API

This module exposes a clean, documented surface for Jupyter Notebooks
and GDSFactory scripts. All heavy engine operations are available
here without needing to use the CLI.

Example (Jupyter notebook)
--------------------------
    import photonstrust.api as pt

    # 1) Predict crosstalk
    xt = pt.predict_crosstalk(gap_um=1.2, length_um=150, wavelength_nm=1550)
    print(f"Crosstalk: {xt:.2f} dB")

    # 2) Get recommended minimum gap
    gap = pt.min_gap_for_crosstalk(target_xt_db=-30, length_um=100, wavelength_nm=1310)
    print(f"Use at least {gap:.2f} µm gap")

    # 3) Estimate process yield
    metrics = [
        {"name": "phase_error_deg", "nominal": 0, "sigma": 1.2,
         "sensitivity": 1.0, "min_allowed": -5, "max_allowed": 5},
    ]
    yield_result = pt.estimate_yield(metrics, mc_samples=10_000)
    print(f"Estimated yield: {yield_result['estimated_yield']:.1%}")

    # 4) Simulate a PIC netlist
    import json, pathlib
    netlist = json.loads(pathlib.Path("my_chip.json").read_text())
    result = pt.simulate_netlist(netlist, wavelength_nm=1550)
"""

from __future__ import annotations

from typing import Any, Optional

__all__ = [
    "predict_crosstalk",
    "min_gap_for_crosstalk",
    "estimate_yield",
    "simulate_netlist",
    "simulate_netlist_sweep",
    "run_drc_report",
]


# ---------------------------------------------------------------------------
# Crosstalk / Performance DRC
# ---------------------------------------------------------------------------

def predict_crosstalk(
    *,
    gap_um: float,
    length_um: float,
    wavelength_nm: float,
    corner_params: Optional[dict] = None,
) -> float:
    """Predict parallel waveguide crosstalk in dB.

    Parameters
    ----------
    gap_um:
        Gap between parallel waveguide cores (µm).
    length_um:
        Parallel coupling region length (µm).
    wavelength_nm:
        Optical wavelength (nm).
    corner_params:
        Optional dict with process-corner overrides, e.g.
        ``{"delta_width_nm": 5, "temperature_c": 70}``.

    Returns
    -------
    float
        Predicted crosstalk (dB). More negative = better isolation.

    Example
    -------
    >>> import photonstrust.api as pt
    >>> pt.predict_crosstalk(gap_um=1.5, length_um=100, wavelength_nm=1550)
    -34.7
    """
    from photonstrust.components.pic.crosstalk import predict_parallel_waveguide_xt_db

    return float(
        predict_parallel_waveguide_xt_db(
            gap_um=float(gap_um),
            parallel_length_um=float(length_um),
            wavelength_nm=float(wavelength_nm),
            **(corner_params or {}),
        )
    )


def min_gap_for_crosstalk(
    *,
    target_xt_db: float,
    length_um: float,
    wavelength_nm: float,
) -> float:
    """Return the minimum gap (µm) to achieve a crosstalk target.

    Parameters
    ----------
    target_xt_db:
        Required worst-case crosstalk (dB), e.g. ``-30``.
    length_um:
        Parallel coupling length (µm).
    wavelength_nm:
        Optical wavelength (nm).

    Returns
    -------
    float
        Minimum recommended gap in µm.
    """
    from photonstrust.components.pic.crosstalk import recommended_min_gap_um

    return float(
        recommended_min_gap_um(
            target_xt_db=float(target_xt_db),
            parallel_length_um=float(length_um),
            wavelength_nm=float(wavelength_nm),
        )
    )


# ---------------------------------------------------------------------------
# Process Yield
# ---------------------------------------------------------------------------

def estimate_yield(
    metrics: list[dict[str, Any]],
    *,
    mc_samples: int = 5_000,
    min_required_yield: float = 0.90,
    seed: int = 7,
    correlation_matrix: Optional[list[list[float]]] = None,
) -> dict[str, Any]:
    """Estimate photonic process yield via analytic + Monte Carlo.

    Parameters
    ----------
    metrics:
        List of dicts, each with keys:
        ``name``, ``nominal``, ``sigma``, ``sensitivity``,
        ``min_allowed``, ``max_allowed``.
    mc_samples:
        Number of Monte Carlo trials (0 = analytic only).
    min_required_yield:
        Fraction threshold below which the result is a failure.
    seed:
        RNG seed for reproducibility.
    correlation_matrix:
        Optional NxN correlation matrix for correlated process
        variation simulation.

    Returns
    -------
    dict
        Includes keys: ``estimated_yield``, ``analytic_yield``,
        ``mc_yield``, ``pass``, ``violations``.

    Example
    -------
    >>> metrics = [
    ...     {"name": "width_nm", "nominal": 500, "sigma": 5,
    ...      "sensitivity": 1.0, "min_allowed": 488, "max_allowed": 512},
    ... ]
    >>> pt.estimate_yield(metrics, mc_samples=10_000)
    {'estimated_yield': 0.981, 'pass': True, ...}
    """
    from photonstrust.pic.layout.verification.core import estimate_process_yield

    return estimate_process_yield(
        metrics=metrics,
        monte_carlo_samples=mc_samples,
        min_required_yield=float(min_required_yield),
        seed=int(seed),
        correlation_matrix=correlation_matrix,
    )


# ---------------------------------------------------------------------------
# PIC Netlist Simulation
# ---------------------------------------------------------------------------

def simulate_netlist(
    netlist: dict[str, Any],
    *,
    wavelength_nm: Optional[float] = None,
) -> dict[str, Any]:
    """Simulate a compiled PIC netlist at a single wavelength.

    Parameters
    ----------
    netlist:
        Dict matching the compiled netlist schema (from ``graph compile``).
    wavelength_nm:
        Wavelength override (nm). Uses the netlist default if ``None``.

    Returns
    -------
    dict
        Simulation results including per-port optical powers and phases.
    """
    from photonstrust.pic import simulate_pic_netlist

    return simulate_pic_netlist(netlist, wavelength_nm=wavelength_nm)


def simulate_netlist_sweep(
    netlist: dict[str, Any],
    *,
    wavelengths_nm: list[float],
) -> list[dict[str, Any]]:
    """Simulate a compiled PIC netlist across a wavelength sweep.

    Parameters
    ----------
    netlist:
        Dict matching the compiled netlist schema.
    wavelengths_nm:
        List of wavelengths (nm) to sweep.

    Returns
    -------
    list[dict]
        One result dict per wavelength.
    """
    from photonstrust.pic import simulate_pic_netlist_sweep

    return simulate_pic_netlist_sweep(netlist, wavelengths_nm=wavelengths_nm)


# ---------------------------------------------------------------------------
# One-shot DRC report
# ---------------------------------------------------------------------------

def run_drc_report(
    *,
    gap_um: float,
    length_um: float,
    wavelength_nm: float,
    target_xt_db: float = -30.0,
    process_metrics: Optional[list[dict[str, Any]]] = None,
    mc_samples: int = 5_000,
) -> dict[str, Any]:
    """Run a full Performance DRC report programmatically.

    Returns a structured dict suitable for JSON export or
    rendering in a Jupyter notebook with ``pd.DataFrame``.

    Example
    -------
    >>> rpt = pt.run_drc_report(
    ...     gap_um=1.2, length_um=100, wavelength_nm=1550,
    ...     target_xt_db=-30,
    ... )
    >>> rpt["crosstalk"]["pass"]
    True
    """
    xt_db = predict_crosstalk(
        gap_um=gap_um, length_um=length_um, wavelength_nm=wavelength_nm
    )
    rec_gap = min_gap_for_crosstalk(
        target_xt_db=target_xt_db, length_um=length_um, wavelength_nm=wavelength_nm
    )
    xt_pass = xt_db <= target_xt_db

    report: dict[str, Any] = {
        "crosstalk": {
            "gap_um": gap_um,
            "length_um": length_um,
            "wavelength_nm": wavelength_nm,
            "actual_xt_db": xt_db,
            "target_xt_db": target_xt_db,
            "recommended_min_gap_um": rec_gap,
            "pass": xt_pass,
        }
    }

    if process_metrics:
        yield_result = estimate_yield(
            process_metrics,
            mc_samples=mc_samples,
        )
        report["yield"] = yield_result

    report["overall_pass"] = xt_pass and (
        report.get("yield", {}).get("pass", True)
    )
    return report
