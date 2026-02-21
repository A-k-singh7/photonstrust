"""Compact SPICE subcircuit models for all PhotonTrust PIC components.

This module provides physics-informed Spice subckt definitions for every
component kind in `photonstrust.components.pic.library._LIB`.

The photonic-SPICE approach used here is the standard "Equivalent Circuit"
method: each optical waveguide/component is modelled as an electrical
transmission line segment or two-port S-parameter network represented
via voltage-controlled current sources (VCCS/G-elements in SPICE).

Signal convention
-----------------
 - Complex optical amplitude E = Re + j*Im is split into two voltages:
   V_re  and  V_im  (real and imaginary parts of the wave amplitude)
 - Nodes are named:  ``<port>_re``, ``<port>_im``, ``gnd``
 - GND is the SPICE global reference (0V)

For each component a deterministic, human-readable ``.subckt`` block is
generated and returned as a string.  These blocks are ready to be pasted
into a netlist or included via ``.include``.

Usage
-----
    from photonstrust.spice.compact_models import (
        all_spice_models,
        spice_model_for_kind,
    )

    # Get the .subckt block for a waveguide
    print(spice_model_for_kind("pic.waveguide", {"length_um": 100, "loss_db_per_cm": 2.0}))

    # Dump all models at once (useful for a component kit .lib file)
    print(all_spice_models())
"""

from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _eta(db: float) -> float:
    """dB loss -> linear amplitude factor (field, not power)."""
    return math.pow(10.0, -max(0.0, db) / 20.0)


def _deg(rad: float) -> float:
    return rad * 180.0 / math.pi


def _header(name: str, ports: list[str], description: str) -> str:
    port_str = " ".join(ports)
    lines = [
        f"* ===== {description} =====",
        f"* PhotonTrust compact model – auto-generated",
        f"* Ports: {port_str}",
        f".subckt {name} {port_str} gnd",
    ]
    return "\n".join(lines)


def _footer(name: str) -> str:
    return f".ends {name}\n"


def _two_port_transmission(
    subckt_name: str,
    t_re: float,
    t_im: float,
    description: str,
) -> str:
    """Generic 2-port forward-transmission subckt.

    Ports: in_re in_im out_re out_im gnd
    VCCS G-elements: V_out = T * V_in  (real & imaginary coupled)
    """
    # out_re = t_re * in_re  -  t_im * in_im
    # out_im = t_im * in_re  +  t_re * in_im
    ports = ["in_re", "in_im", "out_re", "out_im"]
    lines = [
        _header(subckt_name, ports, description),
        f"* T = {t_re:.6f} + j*{t_im:.6f}  (|T|={math.hypot(t_re, t_im):.4f})",
        f"",
        f"* out_re = t_re*in_re - t_im*in_im",
        f"Gout_re out_re gnd in_re gnd {t_re:.9g}",
        f"Gout_re_im out_re gnd in_im gnd {-t_im:.9g}",
        f"",
        f"* out_im = t_im*in_re + t_re*in_im",
        f"Gout_im out_im gnd in_re gnd {t_im:.9g}",
        f"Gout_im_re out_im gnd in_im gnd {t_re:.9g}",
        f"",
        _footer(subckt_name),
    ]
    return "\n".join(lines)


def _four_port_coupler(
    subckt_name: str,
    t: float,
    k: float,
    eta: float,
    description: str,
) -> str:
    """Symmetric 2x2 directional coupler (4-port).

    S-matrix (field):
      out1 = eta*(t*in1 + j*k*in2)
      out2 = eta*(j*k*in1 + t*in2)

    Ports: in1_re in1_im in2_re in2_im out1_re out1_im out2_re out2_im gnd
    """
    ports = ["in1_re", "in1_im", "in2_re", "in2_im",
             "out1_re", "out1_im", "out2_re", "out2_im"]
    et = eta * t
    ek = eta * k  # multiplied by j => re gets -ek*im contribution

    lines = [
        _header(subckt_name, ports, description),
        f"* t={t:.4f}  k={k:.4f}  eta={eta:.4f}",
        f"",
        f"* out1_re = et*in1_re - ek*in2_im",
        f"G1r_in1 out1_re gnd in1_re gnd {et:.9g}",
        f"G1r_in2 out1_re gnd in2_im gnd {-ek:.9g}",
        f"",
        f"* out1_im = et*in1_im + ek*in2_re",
        f"G1i_in1 out1_im gnd in1_im gnd {et:.9g}",
        f"G1i_in2 out1_im gnd in2_re gnd {ek:.9g}",
        f"",
        f"* out2_re = et*in2_re - ek*in1_im",
        f"G2r_in2 out2_re gnd in2_re gnd {et:.9g}",
        f"G2r_in1 out2_re gnd in1_im gnd {-ek:.9g}",
        f"",
        f"* out2_im = et*in2_im + ek*in1_re",
        f"G2i_in2 out2_im gnd in2_im gnd {et:.9g}",
        f"G2i_in1 out2_im gnd in1_re gnd {ek:.9g}",
        f"",
        _footer(subckt_name),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Per-component model generators
# ---------------------------------------------------------------------------

def _model_waveguide(params: dict[str, Any], name: str) -> str:
    length_um = float(params.get("length_um", 100.0) or 100.0)
    loss_db_per_cm = float(params.get("loss_db_per_cm", 3.0) or 3.0)
    n_g = float(params.get("n_g", 4.0) or 4.0)
    wavelength_nm = float(params.get("wavelength_nm", 1550.0) or 1550.0)

    length_cm = length_um / 1e4
    loss_db = loss_db_per_cm * length_cm
    eta = _eta(loss_db)

    lam_m = wavelength_nm * 1e-9
    L_m = length_um * 1e-6
    phi = (2.0 * math.pi * n_g * L_m) / lam_m  # propagation phase
    t_re = eta * math.cos(phi)
    t_im = eta * math.sin(phi)

    desc = f"Waveguide L={length_um:.1f}µm loss={loss_db_per_cm}dB/cm ng={n_g}"
    return _two_port_transmission(name, t_re, t_im, desc)


def _model_insertion_loss_2port(params: dict[str, Any], name: str, label: str) -> str:
    loss_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    eta = _eta(loss_db)
    t_re = eta
    t_im = 0.0
    return _two_port_transmission(name, t_re, t_im, f"{label} IL={loss_db}dB")


def _model_phase_shifter(params: dict[str, Any], name: str) -> str:
    phase_rad = float(params.get("phase_rad", 0.0) or 0.0)
    loss_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    eta = _eta(loss_db)
    t_re = eta * math.cos(phase_rad)
    t_im = eta * math.sin(phase_rad)
    desc = f"PhaseShifter φ={_deg(phase_rad):.2f}° IL={loss_db}dB"
    return _two_port_transmission(name, t_re, t_im, desc)


def _model_ring(params: dict[str, Any], name: str) -> str:
    """All-pass ring resonator compact model via 2-port amplitude transfer."""
    kappa = float(params.get("coupling_ratio", 0.002) or 0.002)
    r = math.sqrt(max(0.0, 1.0 - kappa))

    radius_um = float(params.get("radius_um", 10.0) or 10.0)
    L_rt_um = float(params.get("round_trip_length_um") or (2.0 * math.pi * radius_um))
    n_eff = float(params.get("n_eff", 2.4) or 2.4)
    loss_db_per_cm = float(params.get("loss_db_per_cm", 3.0) or 3.0)
    wavelength_nm = float(params.get("wavelength_nm", 1550.0) or 1550.0)

    length_cm = L_rt_um / 1e4
    a_rt = _eta(loss_db_per_cm * length_cm)

    lam_m = wavelength_nm * 1e-9
    L_m = L_rt_um * 1e-6
    phi = 2.0 * math.pi * n_eff * L_m / lam_m
    e_re = math.cos(phi)
    e_im = -math.sin(phi)   # exp(-j*phi)

    # H = (r - a*e) / (1 - r*a*e)
    num_re = r - a_rt * e_re
    num_im = -a_rt * e_im
    den_re = 1.0 - r * a_rt * e_re
    den_im = -r * a_rt * e_im
    denom_sq = den_re ** 2 + den_im ** 2
    if denom_sq < 1e-30:
        t_re, t_im = 0.0, 0.0
    else:
        t_re = (num_re * den_re + num_im * den_im) / denom_sq
        t_im = (num_im * den_re - num_re * den_im) / denom_sq

    desc = f"RingResonator κ={kappa:.4f} R={radius_um}µm neff={n_eff} λ={wavelength_nm}nm"
    return _two_port_transmission(name, t_re, t_im, desc)


def _model_coupler(params: dict[str, Any], name: str) -> str:
    kappa = float(params.get("coupling_ratio", 0.5) or 0.5)
    kappa = min(1.0, max(0.0, kappa))
    loss_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    eta = _eta(loss_db)
    t = math.sqrt(1.0 - kappa)
    k = math.sqrt(kappa)
    desc = f"DirectionalCoupler κ={kappa:.3f} IL={loss_db}dB"
    return _four_port_coupler(name, t, k, eta, desc)


def _model_isolator(params: dict[str, Any], name: str) -> str:
    il_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    iso_db = float(params.get("isolation_db", 30.0) or 30.0)
    eta_fwd = _eta(il_db)
    eta_rev = _eta(il_db + iso_db)

    ports = ["in_re", "in_im", "out_re", "out_im"]
    lines = [
        _header(name, ports, f"Isolator IL={il_db}dB ISO={iso_db}dB"),
        f"* Forward: eta_fwd={eta_fwd:.6f}  Reverse: eta_rev={eta_rev:.6f}",
        f"* Forward path (in -> out)",
        f"Gfwd_re out_re gnd in_re gnd {eta_fwd:.9g}",
        f"Gfwd_im out_im gnd in_im gnd {eta_fwd:.9g}",
        f"* NOTE: reverse direction is isolated; no back-coupling VCCS by design.",
        f"",
        _footer(name),
    ]
    return "\n".join(lines)


def _model_grating_coupler(params: dict[str, Any], name: str) -> str:
    return _model_insertion_loss_2port(params, name, "GratingCoupler")


def _model_edge_coupler(params: dict[str, Any], name: str) -> str:
    return _model_insertion_loss_2port(params, name, "EdgeCoupler")


def _model_touchstone_stub(params: dict[str, Any], name: str, kind: str) -> str:
    """Return a documented stub for Touchstone components (no analytic params)."""
    path = params.get("touchstone_path") or params.get("path") or "<not-provided>"
    ports = ["in_re", "in_im", "out_re", "out_im"]
    lines = [
        _header(name, ports, f"Touchstone component – {kind}"),
        f"* Source file: {path}",
        f"* This stub maps to a VCCS unity transfer (no-loss placeholder).",
        f"* Replace with a foundry-provided subckt or import .sp block.",
        f"Gre out_re gnd in_re gnd 1.0",
        f"Gim out_im gnd in_im gnd 1.0",
        f"",
        _footer(name),
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

#: Map kind → (generator_fn, default_params)
_KIND_MODELS: dict[str, Any] = {
    "pic.waveguide":        (_model_waveguide,          {"length_um": 100.0, "loss_db_per_cm": 3.0, "n_g": 4.0, "wavelength_nm": 1550.0}),
    "pic.grating_coupler":  (_model_grating_coupler,    {"insertion_loss_db": 1.5}),
    "pic.edge_coupler":     (_model_edge_coupler,       {"insertion_loss_db": 0.5}),
    "pic.phase_shifter":    (_model_phase_shifter,      {"phase_rad": 0.0, "insertion_loss_db": 0.5}),
    "pic.isolator_2port":   (_model_isolator,           {"insertion_loss_db": 0.5, "isolation_db": 30.0}),
    "pic.ring":             (_model_ring,               {"coupling_ratio": 0.002, "radius_um": 10.0, "n_eff": 2.4, "loss_db_per_cm": 3.0, "wavelength_nm": 1550.0}),
    "pic.coupler":          (_model_coupler,            {"coupling_ratio": 0.5, "insertion_loss_db": 0.0}),
    "pic.touchstone_2port": (_model_touchstone_stub,    {}),
    "pic.touchstone_nport": (_model_touchstone_stub,    {}),
}


def supported_kinds() -> list[str]:
    """Return the list of component kinds with SPICE compact models."""
    return sorted(_KIND_MODELS.keys())


def spice_model_for_kind(
    kind: str,
    params: dict[str, Any] | None = None,
    *,
    subckt_name: str | None = None,
) -> str:
    """Generate a SPICE .subckt block for a given component kind.

    Parameters
    ----------
    kind:
        PhotonTrust component kind string, e.g. ``"pic.waveguide"``.
    params:
        Component parameter overrides applied on top of defaults.
    subckt_name:
        Override the generated subckt name (default: derived from kind).

    Returns
    -------
    str
        Complete ``.subckt ... .ends`` text block.

    Raises
    ------
    KeyError
        If ``kind`` is not in the supported component library.
    """
    k = str(kind).strip().lower()
    if k not in _KIND_MODELS:
        raise KeyError(
            f"No SPICE compact model for kind={kind!r}. "
            f"Supported: {supported_kinds()}"
        )

    fn, defaults = _KIND_MODELS[k]
    merged = {**defaults, **(params or {})}
    name = subckt_name or ("PT_" + k.replace(".", "_"))

    # Touchstone kinds get the kind label as context
    if "touchstone" in k:
        return fn(merged, name, k)
    return fn(merged, name)


def all_spice_models(
    params_by_kind: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Generate a full SPICE component library `.lib` file for all kinds.

    Parameters
    ----------
    params_by_kind:
        Optional per-kind parameter overrides, e.g.
        ``{"pic.waveguide": {"loss_db_per_cm": 2.5}}``.

    Returns
    -------
    str
        Complete multi-subckt SPICE library text (suitable for ``.include``).
    """
    overrides = params_by_kind or {}
    sections = [
        "* PhotonTrust Photonic Component SPICE Library",
        "* Generated by photonstrust.spice.compact_models",
        "* Signal convention: optical amplitude split into V_re + j*V_im",
        "",
    ]
    for kind in supported_kinds():
        sections.append(spice_model_for_kind(kind, overrides.get(kind, {})))

    return "\n".join(sections)


def write_component_library(
    output_path: str,
    params_by_kind: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Write the full SPICE component library to a ``.lib`` file.

    Parameters
    ----------
    output_path:
        Path to write the ``.lib`` file (e.g. ``photontrust_components.lib``).
    """
    from pathlib import Path
    text = all_spice_models(params_by_kind)
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
