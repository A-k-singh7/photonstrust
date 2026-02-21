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
    # DRC + LVS
    "run_layout_drc",
    "run_layout_lvs",
    "run_layout_drc_lvs",
    # SPICE analysis
    "ac_sweep_netlist",
    "monte_carlo_netlist",
    "transient_netlist",
    "parametric_sweep_netlist",
    "extract_heater_parasitics",
    "cross_validate_spice_jax",
    # PCell
    "export_pcell_library",
    "pcell_instance",
    "register_klayout_pcells",
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


# ---------------------------------------------------------------------------
# Layout DRC + LVS
# ---------------------------------------------------------------------------

def run_layout_drc(
    netlist: dict[str, Any],
    rules: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Run full DRC on a compiled netlist's auto-generated layout.

    Generates the GDL layout internally and checks all DRC rules.

    Parameters
    ----------
    netlist:
        Compiled PIC netlist dict.
    rules:
        Dict of rule overrides, e.g.
        ``{"wg_min_gap_um": 0.25, "wire_max_length_um": 2000}``.

    Returns
    -------
    dict
        DRC report with ``ok``, ``violations``, ``stats`` keys.

    Example
    -------
    >>> rpt = pt.run_layout_drc(netlist, rules={"wg_min_gap_um": 0.2})
    >>> rpt["ok"]
    True
    """
    from photonstrust.layout.pic.drc_lvs import run_drc, DRCRuleSet
    from photonstrust.layout.pic.klayout_cell import netlist_to_gdl
    gdl = netlist_to_gdl(netlist)
    ruleset = DRCRuleSet.from_dict(rules) if rules else DRCRuleSet()
    return run_drc(gdl, ruleset).to_dict()


def run_layout_lvs(
    netlist: dict[str, Any],
) -> dict[str, Any]:
    """Run LVS (Layout vs. Schematic) on a compiled netlist.

    Compares the GDL wire connectivity against the netlist edge list.

    Parameters
    ----------
    netlist:
        Compiled PIC netlist dict.

    Returns
    -------
    dict
        LVS result with ``ok``, ``matched_count``, ``extra_connections``,
        ``missing_connections``.

    Example
    -------
    >>> result = pt.run_layout_lvs(netlist)
    >>> result["missing_connections"]
    []
    """
    from photonstrust.layout.pic.drc_lvs import run_lvs
    from photonstrust.layout.pic.klayout_cell import netlist_to_gdl
    gdl = netlist_to_gdl(netlist)
    return run_lvs(gdl, netlist).to_dict()


def run_layout_drc_lvs(
    netlist: dict[str, Any],
    rules: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """One-shot DRC + LVS from a compiled netlist.

    Returns
    -------
    dict
        ``{"drc": ..., "lvs": ..., "overall_pass": bool}``
    """
    from photonstrust.layout.pic.drc_lvs import run_drc_lvs
    return run_drc_lvs(netlist, rules)


# ---------------------------------------------------------------------------
# SPICE Analysis netlists
# ---------------------------------------------------------------------------

def ac_sweep_netlist(
    graph: dict[str, Any],
    *,
    start_wl_nm: float = 1480.0,
    stop_wl_nm: float = 1580.0,
    points: int = 100,
) -> str:
    """Generate an ngspice AC sweep netlist for a PIC graph.

    Maps wavelength range to frequency via c/λ and generates a
    ``.ac lin`` SPICE analysis with VCCS compact models embedded.

    Example
    -------
    >>> sp = pt.ac_sweep_netlist(graph, start_wl_nm=1510, stop_wl_nm=1590)
    >>> sp.count(".subckt")
    9
    """
    from photonstrust.spice.analysis import ac_sweep_netlist as _fn
    return _fn(graph, start_wl_nm=start_wl_nm, stop_wl_nm=stop_wl_nm, points=points)


def monte_carlo_netlist(
    graph: dict[str, Any],
    *,
    n_runs: int = 200,
    sigma_scale: float = 1.0,
) -> str:
    """Generate a SPICE Monte Carlo analysis netlist.

    Wraps ``.step mc`` and ``.param gauss()`` variation across all
    waveguide length parameters by default.

    Example
    -------
    >>> sp = pt.monte_carlo_netlist(graph, n_runs=500, sigma_scale=1.5)
    >>> ".step mc" in sp
    True
    """
    from photonstrust.spice.analysis import monte_carlo_netlist as _fn
    return _fn(graph, n_runs=n_runs, sigma_scale=sigma_scale)


def transient_netlist(
    graph: dict[str, Any],
    *,
    bit_rate_gbps: float = 25.0,
    n_bits: int = 8,
    v_pi: float = 5.0,
) -> str:
    """Generate a SPICE transient netlist for MZM eye-diagram simulation.

    The phase-shifter node is driven by a PRBS PWL waveform at the
    specified bit rate. Use ``.meas TRAN`` to extract eye height.

    Example
    -------
    >>> sp = pt.transient_netlist(graph, bit_rate_gbps=50.0, v_pi=3.5)
    >>> ".tran" in sp
    True
    """
    from photonstrust.spice.analysis import transient_netlist as _fn
    return _fn(graph, bit_rate_gbps=bit_rate_gbps, n_bits=n_bits, v_pi=v_pi)


def parametric_sweep_netlist(
    graph: dict[str, Any],
    *,
    node_id: str,
    param_name: str,
    start: float,
    stop: float,
    points: int = 50,
) -> str:
    """Generate a SPICE parametric sweep netlist.

    Sweeps one component parameter using ``.step param`` + single-point
    AC analysis.

    Example
    -------
    >>> sp = pt.parametric_sweep_netlist(
    ...     graph, node_id="c1", param_name="coupling_ratio",
    ...     start=0.1, stop=0.9, points=20
    ... )
    >>> ".step param" in sp
    True
    """
    from photonstrust.spice.analysis import parametric_sweep_netlist as _fn
    return _fn(graph, node_id=node_id, param_name=param_name,
               start=start, stop=stop, points=points)


def extract_heater_parasitics(
    netlist: dict[str, Any],
    *,
    sheet_resistance_ohm_sq: float = 100.0,
) -> list[dict[str, Any]]:
    """Extract metal heater parasitic R and C from the netlist layout.

    Generates the GDL internally, then extracts METAL_LAYER shapes and
    computes series resistance from sheet resistance and geometry.

    Parameters
    ----------
    netlist:
        Compiled PIC netlist dict.
    sheet_resistance_ohm_sq:
        Metal sheet resistance in Ω/□.

    Returns
    -------
    list[dict]
        Per-heater: ``length_um``, ``width_um``, ``resistance_ohm``,
        ``capacitance_fF``, ``rc_ps``.

    Example
    -------
    >>> parasitics = pt.extract_heater_parasitics(netlist)
    >>> parasitics[0]["resistance_ohm"]
    2500.0
    """
    from photonstrust.layout.pic.klayout_cell import netlist_to_gdl
    from photonstrust.spice.analysis import extract_heater_parasitics as _fn
    gdl = netlist_to_gdl(netlist)
    return _fn(gdl, sheet_resistance_ohm_sq=sheet_resistance_ohm_sq)


def cross_validate_spice_jax(
    graph: dict[str, Any],
    *,
    wavelengths_nm: list[float],
    tolerance_db: float = 1.0,
) -> dict[str, Any]:
    """Cross-validate SPICE compact model against JAX scattering solver.

    Runs ngspice AC (if installed) and PhotonTrust JAX simulation at the
    same wavelengths and reports per-wavelength agreement in dB.

    When ngspice is not available, returns ``spice_available=False`` with
    only JAX results populated.

    Example
    -------
    >>> result = pt.cross_validate_spice_jax(graph, wavelengths_nm=[1530, 1550, 1570])
    >>> result["spice_available"]  # False if ngspice not installed
    False
    """
    from photonstrust.spice.analysis import cross_validate_with_jax
    return cross_validate_with_jax(graph, wavelengths_nm=wavelengths_nm,
                                   tolerance_db=tolerance_db)


# ---------------------------------------------------------------------------
# PCell API
# ---------------------------------------------------------------------------

def pcell_instance(
    kind: str,
    params: Optional[dict[str, Any]] = None,
    *,
    x: float = 0.0,
    y: float = 0.0,
    rotation_deg: float = 0.0,
    instance_name: Optional[str] = None,
) -> dict[str, Any]:
    """Create a parametric PCell instance dict for any PIC component.

    Returns a JSON-serialisable dict with placement, params, and
    GDL geometry — suitable for KLayout import or Streamlit rendering.

    Example
    -------
    >>> inst = pt.pcell_instance("pic.ring", {"radius_um": 5}, x=100, y=50)
    >>> inst["placement"]
    {'x': 100.0, 'y': 50.0, 'rotation_deg': 0.0}
    """
    from photonstrust.layout.pic.pcell import pcell_instance as _fn
    return _fn(kind, params, x=x, y=y, rotation_deg=rotation_deg,
               instance_name=instance_name)


def export_pcell_library(
    output_path: str,
    *,
    include_geometry: bool = True,
) -> str:
    """Export the full PCell library as a JSON file.

    Contains parameter schemas, defaults, and GDL geometry previews for
    all 9 PIC component kinds. Compatible with the KLayout macro loader.

    Example
    -------
    >>> pt.export_pcell_library("results/pcell_library.json")
    'C:/Users/.../results/pcell_library.json'
    """
    from photonstrust.layout.pic.pcell import export_pcell_library_json
    p = export_pcell_library_json(output_path, include_geometry=include_geometry)
    return str(p)


def register_klayout_pcells(layout: Any = None) -> bool:
    """Register all PhotonTrust PCells with KLayout.

    Requires the ``klayout`` Python package (``pip install klayout``).
    Returns ``False`` (no error) if klayout is not installed.

    Parameters
    ----------
    layout:
        Optional ``klayout.db.Layout`` instance. If ``None``, registers
        globally via ``klayout.db.Library``.

    Example
    -------
    >>> import klayout.db as db
    >>> layout = db.Layout()
    >>> pt.register_klayout_pcells(layout)
    True
    """
    from photonstrust.layout.pic.pcell import register_all_pcells
    return register_all_pcells(layout)
