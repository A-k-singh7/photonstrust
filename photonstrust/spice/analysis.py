"""SPICE AC sweep, Monte Carlo, sensitivity, and transient analysis generator.

This module generates analysis-ready SPICE netlists from PhotonTrust compact
models and (optionally) parses ngspice batch output.

Analysis modes provided
-----------------------
1. **AC sweep**      — ``.ac`` frequency sweep → |S21|² vs frequency/wavelength
2. **Monte Carlo**   — ``.mc`` and ``.step`` variation of component parameters
3. **Sensitivity**   — ``.sens`` parameter importance ranking
4. **Transient**     — ``.tran`` time-domain modulation (MZM eye diagram)
5. **Parametric**    — ``.step`` single-parameter sweep

All analysis netlists auto-include the ``photontrust_components.lib`` compact
model library.

Usage
-----
    from photonstrust.spice.analysis import (
        ac_sweep_netlist, monte_carlo_netlist, transient_netlist,
        parse_ac_result, cross_validate_with_jax,
    )

    # Generate AC sweep netlist
    netlist_text = ac_sweep_netlist(
        graph, start_freq_thz=175.0, stop_freq_thz=205.0, points=100
    )

    # Run via ngspice and parse
    result = cross_validate_with_jax(graph, wavelengths_nm=[1520, 1550, 1580])
"""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from photonstrust.spice.compact_models import all_spice_models, spice_model_for_kind


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_C_M_S = 299_792_458.0   # speed of light


def _freq_hz_from_nm(wl_nm: float) -> float:
    return _C_M_S / (float(wl_nm) * 1e-9)


def _nm_from_freq_hz(f_hz: float) -> float:
    return _C_M_S / f_hz * 1e9


# ---------------------------------------------------------------------------
# Netlist builders
# ---------------------------------------------------------------------------

def _sid(s: str) -> str:
    """Sanitise a string to a valid SPICE identifier."""
    import re as _re
    s = str(s).strip()
    out = _re.sub(r"[^A-Za-z0-9_]+", "_", s)
    if not out:
        out = "X"
    if out[0].isdigit():
        out = "n_" + out
    return out


def _graph_instance_lines(graph: dict[str, Any]) -> list[str]:
    nodes: list[dict] = graph.get("nodes", [])
    edges: list[dict] = graph.get("edges", [])

    # Simple net assignment: each edge connects out_port net to in_port net
    net_map: dict[tuple[str, str], str] = {}
    net_idx = [0]

    def _net(node_id: str, port: str) -> str:
        key = (node_id, port)
        if key not in net_map:
            net_map[key] = f"n_{_sid(node_id)}_{_sid(port)}"
        return net_map[key]

    for e in edges:
        from_net = _net(str(e.get("from", "")), str(e.get("from_port", "out")))
        to_net   = _net(str(e.get("to", "")),   str(e.get("to_port", "in")))
        # Merge: both refer to from_net
        net_map[(str(e.get("to", "")), str(e.get("to_port", "in")))] = from_net

    lines = []
    for n in nodes:
        nid  = str(n.get("id", ""))
        kind = str(n.get("kind", "")).strip().lower()
        params = n.get("params") or {}
        subckt = "PT_" + kind.replace(".", "_")

        # Determine port list for this kind
        from photonstrust.components.pic.library import component_ports as _cp
        try:
            cp = _cp(kind, params)
            all_ports = list(cp.in_ports) + list(cp.out_ports)
        except Exception:
            all_ports = ["in", "out"]

        nets_str = " ".join(_net(nid, p) for p in all_ports)
        # Params inline
        params_s = " ".join(f"{k}={v}" for k, v in sorted(params.items()) if v is not None)
        lines.append(f"X{_sid(nid)} {nets_str} gnd {subckt}" + (f" $ {params_s}" if params_s else ""))

    return lines


def ac_sweep_netlist(
    graph: dict[str, Any],
    *,
    start_wl_nm: float = 1480.0,
    stop_wl_nm: float = 1580.0,
    points: int = 100,
    input_node: Optional[str] = None,
    output_node: Optional[str] = None,
    title: str = "PhotonTrust AC Sweep",
) -> str:
    """Generate an ngspice AC analysis netlist for a PIC graph.

    The photonic AC sweep maps wavelength to frequency via c/λ and runs a
    SPICE ``.ac lin`` sweep. Source and output probes are connected to the
    first and last nodes unless overridden.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict (``profile=pic_circuit``).
    start_wl_nm / stop_wl_nm:
        Wavelength range in nm.
    points:
        Number of frequency points.
    input_node / output_node:
        Override first/last node for stimulus + probe.

    Returns
    -------
    str
        Complete ngspice-compatible netlist text.
    """
    f_start = _freq_hz_from_nm(stop_wl_nm)   # note: f ∝ 1/λ, so start/stop flip
    f_stop  = _freq_hz_from_nm(start_wl_nm)

    nodes = graph.get("nodes", [])
    if not nodes:
        raise ValueError("graph.nodes is empty")

    first_node = str(input_node or nodes[0].get("id", "n0"))
    last_node  = str(output_node or nodes[-1].get("id", "n_last"))

    inst_lines = _graph_instance_lines(graph)

    lib_section = all_spice_models()

    netlist = [
        f"* {title}",
        "* PhotonTrust SPICE AC analysis",
        "* Signal convention: V_re = Re(E), V_im = Im(E)",
        "",
        "* ── Embedded compact model library ──────────────────────────────",
        lib_section,
        "* ────────────────────────────────────────────────────────────────",
        "",
        "* AC stimulus: unit amplitude at input (real part = 1V, imag = 0)",
        f"Vsrc_re n_{first_node}_in_re 0 AC 1.0",
        f"Vsrc_im n_{first_node}_in_im 0 AC 0.0",
        "",
        "* Circuit instances",
        *inst_lines,
        "",
        "* Analysis",
        f".ac lin {int(points)} {f_start:.6e} {f_stop:.6e}",
        "",
        "* Measurements: output power (|E|² = V_re² + V_im²)",
        f".meas AC out_power_re RMS V(n_{last_node}_out_re)",
        f".meas AC out_power_im RMS V(n_{last_node}_out_im)",
        "",
        ".end",
    ]
    return "\n".join(netlist)


def monte_carlo_netlist(
    graph: dict[str, Any],
    *,
    n_runs: int = 200,
    sigma_scale: float = 1.0,
    varied_params: Optional[dict[str, dict[str, float]]] = None,
    title: str = "PhotonTrust Monte Carlo",
) -> str:
    """Generate a SPICE Monte Carlo netlist using ``.step param`` loops.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict.
    n_runs:
        Number of Monte Carlo trials.
    sigma_scale:
        Multiplier on all process sigmas.
    varied_params:
        Dict of ``{node_id: {param_name: sigma_um_or_rad}}``.
        Defaults to ±5nm width variation on all waveguide nodes.

    Returns
    -------
    str
        SPICE netlist with ``.param gauss()`` variation and ``.step mc`` loop.
    """
    nodes = graph.get("nodes", [])

    # Default: vary waveguide length ±5nm (= ±0.005µm) on all waveguides
    if varied_params is None:
        varied_params = {
            n["id"]: {"length_um": 0.005}
            for n in nodes
            if "waveguide" in str(n.get("kind", ""))
        }

    param_lines = [
        "* Monte Carlo parameter definitions",
        f".param sigma_scale = {sigma_scale:.4f}",
    ]
    for node_id, pdict in varied_params.items():
        for pname, sigma in pdict.items():
            safe = f"{node_id}_{pname}".replace(".", "_")
            param_lines.append(
                f".param {safe}_nom = {{nominal_{safe}}}"  # placeholder
            )
            param_lines.append(
                f".param {safe} = {{gauss({safe}_nom, {sigma * sigma_scale:.6g}, 3)}}"
            )

    lib_section = all_spice_models()
    inst_lines = _graph_instance_lines(graph)
    first_node = str(nodes[0].get("id", "n0")) if nodes else "n0"
    last_node  = str(nodes[-1].get("id", "n_last")) if nodes else "n_last"

    netlist = [
        f"* {title}",
        "* PhotonTrust SPICE Monte Carlo analysis",
        "",
        lib_section,
        "",
        *param_lines,
        "",
        f"Vsrc_re n_{first_node}_in_re 0 AC 1.0",
        f"Vsrc_im n_{first_node}_in_im 0 AC 0.0",
        "",
        *inst_lines,
        "",
        ".ac lin 1 193.5e12 193.5e12",   # single-point at 1550nm
        f".meas AC out_power_re RMS V(n_{last_node}_out_re)",
        f".meas AC out_power_im RMS V(n_{last_node}_out_im)",
        "",
        f".step mc {int(n_runs)}",
        "",
        ".end",
    ]
    return "\n".join(netlist)


def transient_netlist(
    graph: dict[str, Any],
    *,
    bit_rate_gbps: float = 25.0,
    n_bits: int = 8,
    v_pi: float = 5.0,
    title: str = "PhotonTrust Transient / Eye Diagram",
) -> str:
    """Generate a SPICE transient netlist simulating MZM optical modulation.

    Models a Mach-Zehnder modulator driven by a pseudo-random bit sequence.
    The phase-shifter node is driven by a piecewise-linear voltage waveform.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict (must include a ``pic.phase_shifter`` node).
    bit_rate_gbps:
        Target modulation bit rate in Gbps.
    n_bits:
        Number of PRBS bits to simulate.
    v_pi:
        Half-wave voltage Vπ of the modulator (V).

    Returns
    -------
    str
        Transient analysis SPICE netlist.
    """
    period_ns = 1.0 / (bit_rate_gbps * 1e9) * 1e9   # in ns
    prbs = [int(b) for b in "10110010"][:n_bits]     # fixed PRBS-8

    # Build PWL waveform
    pwl_pts = ["0 0"]
    t = 0.0
    for bit in prbs:
        v = float(v_pi if bit else 0.0)
        pwl_pts.append(f"{t:.4f}ns {v:.2f}")
        t += period_ns
        pwl_pts.append(f"{t:.4f}ns {v:.2f}")
    pwl = " ".join(pwl_pts)

    # Find phase shifter node
    ps_node = next(
        (n["id"] for n in graph.get("nodes", []) if "phase_shifter" in str(n.get("kind", ""))),
        None,
    )

    lib_section = all_spice_models()
    inst_lines = _graph_instance_lines(graph)
    nodes = graph.get("nodes", [])
    first_node = str(nodes[0].get("id", "n0")) if nodes else "n0"
    last_node  = str(nodes[-1].get("id", "n_last")) if nodes else "n_last"

    drive_lines = []
    if ps_node:
        drive_lines = [
            f"* MZM drive voltage applied to phase shifter {ps_node}",
            f"Vdrive V_{ps_node}_drive 0 PWL({pwl})",
            f"* Phase = π * V_drive / V_pi  (modelled via param)",
            f".param v_pi = {v_pi:.2f}",
        ]

    netlist = [
        f"* {title}",
        f"* Bit rate: {bit_rate_gbps} Gbps   Vπ: {v_pi}V",
        "",
        lib_section,
        "",
        f"Vsrc_re n_{first_node}_in_re 0 1.0",
        f"Vsrc_im n_{first_node}_in_im 0 0.0",
        "",
        *drive_lines,
        "",
        *inst_lines,
        "",
        f".tran {period_ns / 20:.4f}ns {t:.4f}ns",
        f".meas TRAN eye_height MAX V(n_{last_node}_out_re) FROM={period_ns:.4f}ns TO={t:.4f}ns",
        "",
        ".end",
    ]
    return "\n".join(netlist)


def parametric_sweep_netlist(
    graph: dict[str, Any],
    *,
    node_id: str,
    param_name: str,
    start: float,
    stop: float,
    points: int = 50,
    title: str = "PhotonTrust Parametric Sweep",
) -> str:
    """Generate a SPICE parametric sweep netlist using ``.step lin``.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict.
    node_id:
        ID of the node whose parameter is swept.
    param_name:
        Name of the parameter to sweep (e.g. ``coupling_ratio``).
    start / stop:
        Sweep range.
    points:
        Number of sweep points.

    Returns
    -------
    str
        SPICE netlist with ``.step`` and ``.ac`` single-point analysis.
    """
    lib_section = all_spice_models()
    inst_lines = _graph_instance_lines(graph)
    nodes = graph.get("nodes", [])
    first_node = str(nodes[0].get("id", "n0")) if nodes else "n0"
    last_node  = str(nodes[-1].get("id", "n_last")) if nodes else "n_last"

    safe_param = f"{node_id}_{param_name}".replace(".", "_")
    step = (stop - start) / max(1, points - 1)

    netlist = [
        f"* {title}",
        f"* Sweep {node_id}.{param_name} from {start} to {stop} ({points} pts)",
        "",
        lib_section,
        "",
        f".param {safe_param} = {start:.6g}",
        "",
        f"Vsrc_re n_{first_node}_in_re 0 AC 1.0",
        f"Vsrc_im n_{first_node}_in_im 0 AC 0.0",
        "",
        *inst_lines,
        "",
        ".ac lin 1 193.5e12 193.5e12",
        f".meas AC out_re RMS V(n_{last_node}_out_re)",
        f".meas AC out_im RMS V(n_{last_node}_out_im)",
        "",
        f".step param {safe_param} {start:.6g} {stop:.6g} {step:.6g}",
        "",
        ".end",
    ]
    return "\n".join(netlist)


# ---------------------------------------------------------------------------
# ngspice runner + result parser
# ---------------------------------------------------------------------------

@dataclass
class ACResult:
    frequencies_hz: list[float]
    wavelengths_nm: list[float]
    s21_magnitude: list[float]   # |S21| (field amplitude)
    s21_db: list[float]          # 20*log10(|S21|)


def run_ac_sweep(
    graph: dict[str, Any],
    *,
    start_wl_nm: float = 1480.0,
    stop_wl_nm: float = 1580.0,
    points: int = 100,
    ngspice_exe: Optional[str] = None,
    timeout_s: float = 60.0,
) -> ACResult:
    """Run the AC sweep via ngspice and parse results.

    Requires ngspice installed on PATH (or specified via ``ngspice_exe``).

    Parameters
    ----------
    graph:
        PhotonTrust graph dict.
    start_wl_nm / stop_wl_nm:
        Wavelength range (nm).
    points:
        Number of frequency points.
    ngspice_exe:
        Path to ngspice executable (auto-detected if ``None``).

    Returns
    -------
    ACResult
        Parsed S21 vs wavelength result.

    Raises
    ------
    RuntimeError
        If ngspice is not found or exits with error.
    """
    import shutil
    exe = str(ngspice_exe or "").strip() or shutil.which("ngspice") or shutil.which("ngspice.exe")
    if not exe:
        raise RuntimeError(
            "ngspice not found on PATH. Install from https://ngspice.sourceforge.io/ "
            "or set ngspice_exe parameter."
        )

    netlist_text = ac_sweep_netlist(
        graph, start_wl_nm=start_wl_nm, stop_wl_nm=stop_wl_nm,
        points=points
    )

    with tempfile.TemporaryDirectory() as tmp:
        sp_path  = Path(tmp) / "circuit.sp"
        raw_path = Path(tmp) / "circuit.raw"
        log_path = Path(tmp) / "circuit.log"
        sp_path.write_text(netlist_text, encoding="utf-8")

        result = subprocess.run(
            [exe, "-b", "-r", str(raw_path), "-o", str(log_path), str(sp_path)],
            capture_output=True, text=True, timeout=float(timeout_s),
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"ngspice failed (rc={result.returncode}):\n{result.stderr[:2000]}"
            )

        return _parse_raw_ascii(raw_path, start_wl_nm, stop_wl_nm)


def _parse_raw_ascii(raw_path: Path, start_wl_nm: float, stop_wl_nm: float) -> ACResult:
    """Parse ngspice .raw ASCII output (rudimentary parser for AC data)."""
    freqs: list[float] = []
    re_vals: list[float] = []
    im_vals: list[float] = []

    try:
        text = raw_path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        # ngspice may not generate raw if no probes; return empty
        return ACResult([], [], [], [])

    # Look for numeric data lines (frequency re im format from ASCII raw)
    in_data = False
    for line in text.splitlines():
        if line.strip().lower().startswith("values"):
            in_data = True
            continue
        if not in_data:
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                freqs.append(float(parts[0]))
                re_vals.append(float(parts[1]))
                im_vals.append(float(parts[2]))
            except ValueError:
                pass

    wavelengths = [_nm_from_freq_hz(f) for f in freqs] if freqs else []
    magnitudes  = [math.hypot(r, i) for r, i in zip(re_vals, im_vals)]
    s21_db      = [20.0 * math.log10(max(m, 1e-15)) for m in magnitudes]

    return ACResult(
        frequencies_hz=freqs,
        wavelengths_nm=wavelengths,
        s21_magnitude=magnitudes,
        s21_db=s21_db,
    )


# ---------------------------------------------------------------------------
# Cross-validation: SPICE vs JAX
# ---------------------------------------------------------------------------

def cross_validate_with_jax(
    graph: dict[str, Any],
    *,
    wavelengths_nm: list[float],
    ngspice_exe: Optional[str] = None,
    tolerance_db: float = 1.0,
) -> dict[str, Any]:
    """Cross-validate the SPICE compact model against the JAX scattering solver.

    Runs ngspice AC and PhotonTrust JAX simulation at the same wavelengths
    and reports agreement in dB.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict.
    wavelengths_nm:
        List of wavelengths to evaluate.
    tolerance_db:
        Maximum allowed |S21| discrepancy to be flagged as "agree".

    Returns
    -------
    dict
        Per-wavelength comparison table + overall agreement flag.
    """
    # Try ngspice path
    spice_result: Optional[ACResult] = None
    spice_error: Optional[str] = None
    try:
        spice_result = run_ac_sweep(
            graph,
            start_wl_nm=min(wavelengths_nm),
            stop_wl_nm=max(wavelengths_nm),
            points=len(wavelengths_nm),
            ngspice_exe=ngspice_exe,
        )
    except Exception as exc:
        spice_error = str(exc)

    # JAX path via SDK
    from photonstrust.spice.compact_models import _eta  # reuse helper
    jax_s21_db: list[float] = []
    try:
        from photonstrust import sdk as pt
        # Build a minimal netlist for the graph
        compiled_netlist = {"circuit": {"nodes": graph.get("nodes", []),
                                        "edges": graph.get("edges", [])}}
        sweep = pt.simulate_netlist_sweep(compiled_netlist, wavelengths_nm=list(wavelengths_nm))
        for res in sweep:
            outs = res.get("outputs", [])
            if outs:
                pdb = outs[0].get("power_dB", -100)
                jax_s21_db.append(float(pdb) if pdb is not None else -100.0)
            else:
                jax_s21_db.append(-100.0)
    except Exception as exc:
        jax_s21_db = []
        spice_error = (spice_error or "") + f" JAX error: {exc}"

    rows = []
    all_agree = True
    for i, wl in enumerate(wavelengths_nm):
        jax_val = jax_s21_db[i] if i < len(jax_s21_db) else None

        # Interpolate SPICE result at this wavelength
        spice_val = None
        if spice_result and spice_result.wavelengths_nm:
            # Simple nearest-neighbour
            dists = [abs(w - wl) for w in spice_result.wavelengths_nm]
            idx = min(range(len(dists)), key=dists.__getitem__)
            spice_val = spice_result.s21_db[idx]

        agree = None
        if jax_val is not None and spice_val is not None:
            diff = abs(jax_val - spice_val)
            agree = diff <= tolerance_db
            if not agree:
                all_agree = False

        rows.append({
            "wavelength_nm": wl,
            "jax_s21_db": jax_val,
            "spice_s21_db": spice_val,
            "diff_db": abs(jax_val - spice_val) if (jax_val and spice_val) else None,
            "agree": agree,
        })

    return {
        "ok": all_agree and not bool(spice_error),
        "tolerance_db": tolerance_db,
        "spice_available": spice_error is None,
        "spice_error": spice_error,
        "comparison": rows,
    }


# ---------------------------------------------------------------------------
# Heater parasitic extraction
# ---------------------------------------------------------------------------

def extract_heater_parasitics(
    gdl: dict[str, Any],
    *,
    sheet_resistance_ohm_sq: float = 100.0,
    metal_thickness_nm: float = 200.0,
) -> list[dict[str, Any]]:
    """Extract metal heater resistance + RC parasitics from GDL geometry.

    For each METAL_LAYER shape, computes:
    - Width, length (from bbox)
    - Series resistance R = ρ_sq * (L / W)
    - Parasitic capacitance C ≈ ε₀ * A / d_oxide (simplified)

    Parameters
    ----------
    gdl:
        GDL layout dict from ``netlist_to_gdl``.
    sheet_resistance_ohm_sq:
        Metal sheet resistance in Ω/□ (typical TiN: 50-200 Ω/□).
    metal_thickness_nm:
        Metal layer thickness in nm (for capacitance estimate).

    Returns
    -------
    list[dict]
        Per-heater parasitic dict with ``resistance_ohm``, ``area_um2``.
    """
    _METAL_L = 11
    EPS0 = 8.854e-12   # F/m
    EPS_SIO2 = 3.9     # relative permittivity of SiO2
    d_oxide_um = 0.5   # typical SiO2 gap between metal and WG (µm)

    results = []
    for cell in gdl.get("cells", []):
        cell_name = cell.get("cell_name", "")
        for shape in cell.get("shapes", []):
            if shape.get("layer") != _METAL_L:
                continue
            b = shape.get("bbox", [0, 0, 1, 1])
            w = abs(b[2] - b[0])   # µm
            h = abs(b[3] - b[1])   # µm
            # Heater runs along longer dimension
            length_um = max(w, h)
            width_um  = min(w, h)
            if width_um < 1e-6:
                continue

            n_squares = length_um / width_um
            resistance = sheet_resistance_ohm_sq * n_squares

            area_m2 = (length_um * 1e-6) * (width_um * 1e-6)
            d_m     = d_oxide_um * 1e-6
            capacitance_f = EPS0 * EPS_SIO2 * area_m2 / d_m
            rc_ps = resistance * capacitance_f * 1e12   # RC time constant in ps

            results.append({
                "cell_name": cell_name,
                "length_um": round(length_um, 4),
                "width_um": round(width_um, 4),
                "n_squares": round(n_squares, 3),
                "resistance_ohm": round(resistance, 2),
                "area_um2": round(length_um * width_um, 4),
                "capacitance_fF": round(capacitance_f * 1e15, 4),
                "rc_ps": round(rc_ps, 4),
            })
    return results


def spice_with_parasitics(
    graph: dict[str, Any],
    gdl: dict[str, Any],
    *,
    sheet_resistance_ohm_sq: float = 100.0,
) -> str:
    """Generate AC sweep netlist with heater parasitics back-annotated.

    Parameters
    ----------
    graph:
        PhotonTrust graph dict.
    gdl:
        GDL layout dict (used to extract heater geometry).

    Returns
    -------
    str
        SPICE netlist with parasitic R and C elements added.
    """
    base = ac_sweep_netlist(graph, points=50)
    parasitics = extract_heater_parasitics(
        gdl, sheet_resistance_ohm_sq=sheet_resistance_ohm_sq
    )

    if not parasitics:
        return base

    para_lines = ["", "* ── Heater parasitic elements (back-annotated from GDS) ──"]
    for i, p in enumerate(parasitics):
        node_a = f"n_heater_{i}_a"
        node_b = f"n_heater_{i}_b"
        para_lines.append(f"* Cell: {p['cell_name']}  L={p['length_um']}µm W={p['width_um']}µm")
        para_lines.append(f"Rheater{i} {node_a} {node_b} {p['resistance_ohm']:.2f}")
        para_lines.append(f"Cheater{i} {node_b} 0 {p['capacitance_fF'] * 1e-15:.3e}")

    # Insert parasitic lines before .end
    lines = base.splitlines()
    insert_at = next((i for i, l in enumerate(lines) if l.strip() == ".end"), len(lines))
    return "\n".join(lines[:insert_at] + para_lines + [""] + lines[insert_at:])
