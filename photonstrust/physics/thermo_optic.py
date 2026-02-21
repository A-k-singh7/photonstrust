"""Thermo-optic co-simulation for PhotonTrust phase shifters.

Closes the physical loop:

    V_heater → P_heater → ΔT_waveguide → Δn_eff → Δφ

Physics used
------------
- Ohmic heating:  P = V² / R_heater
- Thermal model:  ΔT = P × R_th  (lumped resistor model, calibratable)
- Thermo-optic:   Δn_eff = dn/dT × ΔT   (Si: 1.86e-4 K⁻¹, SiN: 2.5e-5 K⁻¹)
- Phase:          Δφ = (2π / λ) × Δn_eff × L

This module can be used standalone or integrated with the SPICE netlist
generator to produce physically-accurate transient simulations.

Usage
-----
    from photonstrust.physics.thermo_optic import (
        compute_thermo_optic_phase,
        heater_drive_curve,
        ThermoOpticMaterial,
    )

    result = compute_thermo_optic_phase(
        voltage_v=3.0,
        heater_resistance_ohm=500.0,
        thermal_resistance_k_per_w=5e4,
        thermo_optic_coeff=1.86e-4,   # Silicon
        waveguide_length_um=50.0,
        wavelength_nm=1550.0,
    )
    print(result["phase_rad"])  # e.g. 1.57 (π/2)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Material database
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThermoOpticMaterial:
    """Thermo-optic material parameters."""
    name: str
    n_eff_room_temp: float        # effective index at 300 K
    dn_dT: float                  # thermo-optic coefficient (K⁻¹)
    specific_heat_j_per_kg_k: float
    density_kg_per_m3: float

    def delta_n_eff(self, delta_T_K: float) -> float:
        return self.dn_dT * delta_T_K


SILICON = ThermoOpticMaterial(
    name="silicon",
    n_eff_room_temp=2.4,
    dn_dT=1.86e-4,
    specific_heat_j_per_kg_k=700.0,
    density_kg_per_m3=2329.0,
)

SILICON_NITRIDE = ThermoOpticMaterial(
    name="silicon_nitride",
    n_eff_room_temp=1.98,
    dn_dT=2.5e-5,
    specific_heat_j_per_kg_k=700.0,
    density_kg_per_m3=3100.0,
)

LITHIUM_NIOBATE = ThermoOpticMaterial(
    name="lithium_niobate",
    n_eff_room_temp=2.21,
    dn_dT=4.0e-5,
    specific_heat_j_per_kg_k=610.0,
    density_kg_per_m3=4628.0,
)

MATERIAL_DB: dict[str, ThermoOpticMaterial] = {
    "silicon": SILICON,
    "si": SILICON,
    "silicon_nitride": SILICON_NITRIDE,
    "sin": SILICON_NITRIDE,
    "lithium_niobate": LITHIUM_NIOBATE,
    "ln": LITHIUM_NIOBATE,
}


# ---------------------------------------------------------------------------
# Core thermo-optic calculator
# ---------------------------------------------------------------------------

def compute_thermo_optic_phase(
    *,
    voltage_v: float,
    heater_resistance_ohm: float = 500.0,
    thermal_resistance_k_per_w: float = 5e4,
    thermo_optic_coeff: float = 1.86e-4,
    waveguide_length_um: float = 50.0,
    wavelength_nm: float = 1550.0,
    ambient_temp_k: float = 300.0,
    material: str | ThermoOpticMaterial | None = None,
) -> dict[str, Any]:
    """Compute thermo-optic phase shift from heater voltage.

    Physics chain:  V → P_ohm → ΔT → Δn_eff → Δφ

    Parameters
    ----------
    voltage_v:
        Applied heater voltage (V).
    heater_resistance_ohm:
        Heater series resistance (Ω). Typical TiN heater: 200-1000 Ω.
    thermal_resistance_k_per_w:
        Lumped thermal resistance from heater to waveguide core (K/W).
        Typical value for a buried SiO₂ cladding: 4×10⁴ – 1×10⁵ K/W.
    thermo_optic_coeff:
        dn/dT of the waveguide material (K⁻¹). Overridden by ``material``.
    waveguide_length_um:
        Phase shifter length (µm).
    wavelength_nm:
        Operating wavelength (nm).
    ambient_temp_k:
        Ambient temperature (K).
    material:
        Material name (``"silicon"``, ``"silicon_nitride"``, ``"lithium_niobate"``)
        or a :class:`ThermoOpticMaterial` instance. If provided, overrides
        ``thermo_optic_coeff``.

    Returns
    -------
    dict
        ``{"phase_rad", "delta_T_K", "delta_n_eff", "power_mw",
           "temperature_k", "voltage_v", "v_pi_v"}``

    Example
    -------
    >>> result = compute_thermo_optic_phase(voltage_v=3.0, waveguide_length_um=50)
    >>> result["phase_rad"]
    0.73...
    """
    mat: ThermoOpticMaterial | None = None
    if material is not None:
        if isinstance(material, str):
            mat = MATERIAL_DB.get(str(material).strip().lower())
            if mat is None:
                raise ValueError(
                    f"Unknown material: {material!r}. "
                    f"Use one of: {sorted(MATERIAL_DB.keys())}"
                )
        else:
            mat = material

    dn_dT = mat.dn_dT if mat else float(thermo_optic_coeff)

    V = float(voltage_v)
    R = float(heater_resistance_ohm)
    R_th = float(thermal_resistance_k_per_w)
    L_m = float(waveguide_length_um) * 1e-6
    lam_m = float(wavelength_nm) * 1e-9

    # Ohmic dissipation
    power_w = (V ** 2) / R if R > 0 else 0.0
    power_mw = power_w * 1e3

    # Temperature rise
    delta_T = power_w * R_th
    T_wg = ambient_temp_k + delta_T

    # Refractive index change
    delta_n = dn_dT * delta_T

    # Phase shift
    delta_phi = (2.0 * math.pi * delta_n * L_m) / lam_m

    # Vπ: voltage for π phase shift (Δφ = π)
    # π = (2π/λ) × dn/dT × (V²/R × R_th) × L
    # Vπ² = π × λ × R / (2π × dn/dT × R_th × L)
    v_pi_sq = (math.pi * lam_m * R) / (2.0 * math.pi * dn_dT * R_th * L_m) if (dn_dT * R_th * L_m) > 0 else float("inf")
    v_pi = math.sqrt(max(0.0, v_pi_sq))

    return {
        "voltage_v": round(V, 4),
        "power_mw": round(power_mw, 4),
        "delta_T_K": round(delta_T, 4),
        "temperature_k": round(T_wg, 4),
        "delta_n_eff": round(delta_n, 8),
        "phase_rad": round(delta_phi, 6),
        "phase_deg": round(math.degrees(delta_phi), 4),
        "v_pi_v": round(v_pi, 4),
        "material": mat.name if mat else "custom",
        "wavelength_nm": wavelength_nm,
        "waveguide_length_um": waveguide_length_um,
    }


def heater_drive_curve(
    *,
    heater_resistance_ohm: float = 500.0,
    thermal_resistance_k_per_w: float = 5e4,
    thermo_optic_coeff: float = 1.86e-4,
    waveguide_length_um: float = 50.0,
    wavelength_nm: float = 1550.0,
    v_min: float = 0.0,
    v_max: float = 5.0,
    n_points: int = 50,
    material: str | ThermoOpticMaterial | None = None,
) -> dict[str, Any]:
    """Compute the full V → Δφ drive curve for a heater.

    Parameters
    ----------
    v_min / v_max:
        Voltage sweep range (V).
    n_points:
        Number of voltage points.

    Returns
    -------
    dict
        ``{"voltages_v": [...], "phases_rad": [...], "delta_T_K": [...],
           "v_pi_v": float, "power_mw": [...]}``

    Example
    -------
    >>> curve = heater_drive_curve(waveguide_length_um=50, v_max=5.0)
    >>> import matplotlib.pyplot as plt
    >>> plt.plot(curve["voltages_v"], curve["phases_rad"])
    """
    step = (v_max - v_min) / max(1, n_points - 1)
    voltages = [v_min + i * step for i in range(n_points)]

    phases, delta_ts, powers = [], [], []
    v_pi = None
    for v in voltages:
        r = compute_thermo_optic_phase(
            voltage_v=v,
            heater_resistance_ohm=heater_resistance_ohm,
            thermal_resistance_k_per_w=thermal_resistance_k_per_w,
            thermo_optic_coeff=thermo_optic_coeff,
            waveguide_length_um=waveguide_length_um,
            wavelength_nm=wavelength_nm,
            material=material,
        )
        phases.append(r["phase_rad"])
        delta_ts.append(r["delta_T_K"])
        powers.append(r["power_mw"])
        if v_pi is None:
            v_pi = r["v_pi_v"]

    return {
        "voltages_v": [round(v, 4) for v in voltages],
        "phases_rad": [round(p, 6) for p in phases],
        "phases_deg": [round(math.degrees(p), 4) for p in phases],
        "delta_T_K": [round(t, 4) for t in delta_ts],
        "power_mw": [round(p, 4) for p in powers],
        "v_pi_v": v_pi,
        "wavelength_nm": wavelength_nm,
        "waveguide_length_um": waveguide_length_um,
    }


def update_netlist_with_thermal(
    netlist: dict[str, Any],
    heater_voltages: dict[str, float],
    *,
    heater_resistance_ohm: float = 500.0,
    thermal_resistance_k_per_w: float = 5e4,
    material: str = "silicon",
) -> dict[str, Any]:
    """Apply heater voltages to phase-shifter nodes in a netlist.

    Converts each heater voltage to a phase shift and injects it into
    the corresponding ``phase_rad`` parameter.

    Parameters
    ----------
    netlist:
        Compiled PIC netlist dict.
    heater_voltages:
        Dict mapping node_id → applied voltage (V).

    Returns
    -------
    dict
        Updated netlist with ``phase_rad`` values set from thermal physics.

    Example
    -------
    >>> updated = update_netlist_with_thermal(
    ...     netlist, {"ps1": 3.0, "ps2": 1.5}
    ... )
    """
    import copy
    updated = copy.deepcopy(netlist)
    circuit = updated.get("circuit", updated)
    nodes = circuit.get("nodes", [])

    for node in nodes:
        nid = str(node.get("id", ""))
        if nid not in heater_voltages:
            continue
        kind = str(node.get("kind", "")).lower()
        if "phase_shifter" not in kind:
            continue

        params = node.get("params") or {}
        length_um = float(params.get("length_um", 50.0) or 50.0)

        result = compute_thermo_optic_phase(
            voltage_v=heater_voltages[nid],
            heater_resistance_ohm=heater_resistance_ohm,
            thermal_resistance_k_per_w=thermal_resistance_k_per_w,
            waveguide_length_um=length_um,
            material=material,
        )
        node.setdefault("params", {})["phase_rad"] = result["phase_rad"]
        node["params"]["_thermo_delta_T_K"] = result["delta_T_K"]
        node["params"]["_thermo_power_mw"] = result["power_mw"]

    return updated
