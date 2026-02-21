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
    # SPICE
    "export_spice",
    "export_component_library",
    "spice_model_for_kind",
    "all_spice_models",
    # KLayout / GDS
    "export_gds",
    "component_gds_cell",
    "netlist_to_gdl",
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


# ---------------------------------------------------------------------------
# SPICE Integration
# ---------------------------------------------------------------------------

def spice_model_for_kind(
    kind: str,
    params: Optional[dict[str, Any]] = None,
    *,
    subckt_name: Optional[str] = None,
) -> str:
    """Generate a SPICE .subckt compact model for a single component kind.

    Parameters
    ----------
    kind:
        PhotonTrust component kind, e.g. ``"pic.waveguide"``.
    params:
        Component parameter overrides (e.g. ``{"length_um": 150}``),
        applied on top of physics defaults.
    subckt_name:
        Optional override for the ``.subckt`` name.

    Returns
    -------
    str
        Complete SPICE ``.subckt ... .ends`` block ready for simulation.

    Example
    -------
    >>> print(pt.spice_model_for_kind("pic.phase_shifter", {"phase_rad": 1.57}))
    * ===== PhaseShifter phiphi=90.0deg ...
    .subckt PT_pic_phase_shifter in_re in_im out_re out_im gnd
    ...
    """
    from photonstrust.spice.compact_models import spice_model_for_kind as _fn
    return _fn(kind, params, subckt_name=subckt_name)


def all_spice_models(
    params_by_kind: Optional[dict[str, dict[str, Any]]] = None,
) -> str:
    """Generate a full SPICE `.lib` file for all PIC component kinds.

    Parameters
    ----------
    params_by_kind:
        Optional per-kind parameter overrides.

    Returns
    -------
    str
        Multi-subckt SPICE library text (ready for ``.include`` in a netlist).

    Example
    -------
    >>> lib = pt.all_spice_models({"pic.waveguide": {"loss_db_per_cm": 1.5}})
    >>> print(lib[:200])
    * PhotonTrust Photonic Component SPICE Library ...
    """
    from photonstrust.spice.compact_models import all_spice_models as _fn
    return _fn(params_by_kind)


def export_spice(
    graph: dict[str, Any],
    output_dir: str,
    *,
    top_name: str = "PT_TOP",
    include_compact_models: bool = True,
    require_schema: bool = False,
) -> dict[str, Any]:
    """Export a PIC graph to a SPICE netlist with real compact models.

    When ``include_compact_models=True`` (default), a companion
    ``photontrust_components.lib`` is written alongside ``netlist.sp``,
    containing physics-derived VCCS models for every component in the design.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict (``profile=pic_circuit``).
    output_dir:
        Directory to write artifacts into.
    top_name:
        SPICE top-level subckt name.
    include_compact_models:
        Write the companion ``.lib`` file with compact model bodies.
    require_schema:
        Fail if jsonschema is unavailable.

    Returns
    -------
    dict
        Artifact paths + summary (matches ``photonstrust.pic_spice_export.v0`` schema).

    Example
    -------
    >>> result = pt.export_spice(graph, "results/spice")
    >>> print(result["artifacts"]["netlist_path"])
    netlist.sp
    """
    import pathlib
    from photonstrust.spice.export import export_pic_graph_to_spice_artifacts
    from photonstrust.spice.compact_models import write_component_library

    out = pathlib.Path(output_dir)
    result = export_pic_graph_to_spice_artifacts(
        {"graph": graph, "settings": {"top_name": top_name}},
        out,
        require_schema=require_schema,
    )

    if include_compact_models:
        lib_path = out / "photontrust_components.lib"
        write_component_library(str(lib_path))
        result["artifacts"]["compact_models_lib"] = lib_path.name
        # Prepend .include directive into the netlist
        netlist_path = out / result["artifacts"]["netlist_path"]
        existing = netlist_path.read_text(encoding="utf-8")
        netlist_path.write_text(
            f".include {lib_path.name}\n" + existing,
            encoding="utf-8"
        )

    return result


def export_component_library(
    output_path: str,
    params_by_kind: Optional[dict[str, dict[str, Any]]] = None,
) -> str:
    """Write a full SPICE component library ``.lib`` file.

    Parameters
    ----------
    output_path:
        Destination file path (e.g. ``"components.lib"`` or ``"pt_lib.sp"``).
    params_by_kind:
        Optional per-kind parameter overrides.

    Returns
    -------
    str
        Absolute path of the written file.

    Example
    -------
    >>> pt.export_component_library("my_project/pt_components.lib")
    'C:/Users/.../my_project/pt_components.lib'
    """
    from photonstrust.spice.compact_models import write_component_library
    from pathlib import Path
    write_component_library(output_path, params_by_kind)
    return str(Path(output_path).resolve())


# ---------------------------------------------------------------------------
# KLayout / GDS Integration
# ---------------------------------------------------------------------------

def component_gds_cell(
    kind: str,
    params: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Generate a GDS cell geometry dict for a single PIC component.

    Returns a JSON-serialisable dict with ``cell_name``, ``shapes``, and
    ``ports`` – suitable for visualisation, downstream GDS-II export, or
    manual inspection.

    Parameters
    ----------
    kind:
        PhotonTrust component kind, e.g. ``"pic.ring"``.
    params:
        Component parameter overrides.

    Example
    -------
    >>> cell = pt.component_gds_cell("pic.ring", {"radius_um": 5, "n_eff": 2.4})
    >>> cell["ports"]
    [{'type': 'port', 'name': 'in', ...}, {'type': 'port', 'name': 'out', ...}]
    """
    from photonstrust.layout.pic.klayout_cell import component_gdl_cell
    return component_gdl_cell(kind, params)


def netlist_to_gdl(netlist: dict[str, Any]) -> dict[str, Any]:
    """Convert a compiled PIC netlist into a GDL layout dict.

    Auto-places every component node and generates wire annotations between
    connected ports. Output is JSON-serialisable and can be passed to
    ``write_gds_via_klayout()`` or rendered in the Streamlit topology viewer.

    Example
    -------
    >>> gdl = pt.netlist_to_gdl(netlist)
    >>> len(gdl["instances"])
    5
    """
    from photonstrust.layout.pic.klayout_cell import netlist_to_gdl as _fn
    return _fn(netlist)


def export_gds(
    netlist: dict[str, Any],
    output_path: str,
    *,
    format: str = "gdl",
    top_cell_name: str = "PT_TOP",
) -> str:
    """Export a PIC netlist to GDS layout.

    Parameters
    ----------
    netlist:
        Compiled PIC netlist dict.
    output_path:
        Destination file path.
    format:
        ``"gdl"`` (JSON, always available) or ``"gds"`` (binary GDS-II,
        requires ``pip install klayout``).
    top_cell_name:
        Top-level GDS cell name (only used for ``format="gds"``).

    Returns
    -------
    str
        Absolute path of the written file.

    Example
    -------
    >>> pt.export_gds(netlist, "results/chip.gdl.json", format="gdl")
    'C:/Users/.../results/chip.gdl.json'
    >>> pt.export_gds(netlist, "results/chip.gds", format="gds")
    'C:/Users/.../results/chip.gds'
    """
    from photonstrust.layout.pic.klayout_cell import write_gdl, write_gds_via_klayout
    from pathlib import Path

    fmt = str(format).strip().lower()
    if fmt == "gdl":
        p = write_gdl(output_path, netlist)
    elif fmt == "gds":
        p = write_gds_via_klayout(output_path, netlist, top_cell_name=top_cell_name)
    else:
        raise ValueError(f"Unknown format: {format!r}. Use 'gdl' or 'gds'.")
    return str(p)
