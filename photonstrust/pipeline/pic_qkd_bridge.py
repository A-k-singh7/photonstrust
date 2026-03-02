"""Bridge helpers from PIC simulation outputs into QKD sweep scenarios."""

from __future__ import annotations

import math
from typing import Any, Iterable


def extract_eta_chip_channels(sim_result: dict[str, Any], wavelength_nm: float) -> list[dict[str, Any]]:
    """Extract per-output eta channels from DAG external outputs.

    Returns deterministic rows sorted by ``(node, port, source_index)``.
    Rows include:
      - ``channel_id``: stable identifier for this output
      - ``node`` / ``port``: normalized endpoint names when available
      - ``eta``: clamped output power interpreted as transmission efficiency
    """

    selected = _select_wavelength_point(sim_result, wavelength_nm=wavelength_nm)
    dag_solver = selected.get("dag_solver") if isinstance(selected.get("dag_solver"), dict) else {}
    external_outputs = dag_solver.get("external_outputs")
    if not isinstance(external_outputs, list):
        return []

    rows: list[dict[str, Any]] = []
    for idx, raw in enumerate(external_outputs):
        if not isinstance(raw, dict):
            continue
        power = _as_finite_float(raw.get("power"))
        if power is None:
            continue
        node = str(raw.get("node") or "").strip()
        port = str(raw.get("port") or "").strip()
        row = {
            "channel_id": f"{node}.{port}" if node or port else f"output_{idx:04d}",
            "node": node,
            "port": port,
            "eta": _clamp01(max(0.0, power)),
            "_source_index": int(idx),
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            str(row.get("node", "")).lower(),
            str(row.get("port", "")).lower(),
            int(row.get("_source_index", 0)),
        )
    )
    for row in rows:
        row.pop("_source_index", None)
    return rows


def extract_eta_chip(sim_result: dict[str, Any], wavelength_nm: float) -> float:
    """Extract chip transmission efficiency from PIC simulation outputs.

    Priority order:
      1) dag_solver.external_outputs[*].power sum
      2) chain_solver.eta_total
      3) chain_solver.total_loss_db
    """

    dag_channels = extract_eta_chip_channels(sim_result, wavelength_nm=wavelength_nm)
    if dag_channels:
        return _clamp01(sum(float(row.get("eta", 0.0) or 0.0) for row in dag_channels))

    selected = _select_wavelength_point(sim_result, wavelength_nm=wavelength_nm)

    chain_solver = selected.get("chain_solver") if isinstance(selected.get("chain_solver"), dict) else {}
    eta_total = _as_finite_float(chain_solver.get("eta_total"))
    if eta_total is not None:
        return _clamp01(eta_total)

    total_loss_db = _as_finite_float(chain_solver.get("total_loss_db"))
    if total_loss_db is not None:
        return _clamp01(10.0 ** (-total_loss_db / 10.0))

    return 0.0


def pdk_coupler_efficiency(pdk: Any) -> float:
    """Estimate aggregate coupler efficiency from PDK component metadata."""

    component_cells = _component_cells_from_pdk(pdk)
    if not component_cells:
        return 1.0

    ordered_cells = sorted(
        component_cells,
        key=lambda cell: (
            str((cell or {}).get("name", "")).lower(),
            str((cell or {}).get("cell", "")).lower(),
            str((cell or {}).get("library", "")).lower(),
        ),
    )

    il_db_values: list[float] = []
    for cell in ordered_cells:
        if not isinstance(cell, dict):
            continue
        if not _looks_like_io_coupler_cell(cell):
            continue
        il_db = _extract_il_db(cell)
        if il_db is None or il_db < 0.0:
            continue
        il_db_values.append(il_db)

    if not il_db_values:
        return 1.0

    # Deterministic aggregate for multi-cell manifests.
    mean_il_db = float(sum(il_db_values) / len(il_db_values))
    return _clamp01(10.0 ** (-mean_il_db / 10.0))


def build_qkd_scenario_from_pic(
    *,
    graph: dict[str, Any] | None,
    distances_km: Iterable[float],
    wavelength_nm: float,
    protocol: str = "BB84_DECOY",
    eta_chip: float = 1.0,
    eta_coupler: float = 1.0,
) -> dict[str, Any]:
    """Build a valid QKD scenario payload from PIC context."""

    graph_id = str((graph or {}).get("graph_id") or "pic_certification").strip() or "pic_certification"
    normalized_protocol = str(protocol or "BB84_DECOY").strip().upper() or "BB84_DECOY"

    sorted_distances = sorted({_non_negative_float(v) for v in distances_km if _non_negative_float(v) is not None})
    if not sorted_distances:
        sorted_distances = [0.0]

    effective_coupling = _clamp01(_clamp01(eta_chip) * _clamp01(eta_coupler))
    if effective_coupling <= 0.0:
        effective_coupling = 1e-12

    scenario = {
        "scenario_id": f"{graph_id}_pic_qkd_certificate",
        "band": "c_1550",
        "wavelength_nm": float(wavelength_nm),
        "distances_km": sorted_distances,
        "source": {
            "type": "wcp",
            "rep_rate_mhz": 200.0,
            "collection_efficiency": 1.0,
            "coupling_efficiency": float(effective_coupling),
        },
        "channel": {
            "model": "fiber",
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.0,
            "dispersion_ps_per_km": 0.0,
            "background_counts_cps": 0.0,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.75,
            "dark_counts_cps": 50.0,
            "background_counts_cps": 0.0,
            "jitter_ps_fwhm": 30.0,
            "dead_time_ns": 20.0,
            "afterpulsing_prob": 0.0,
        },
        "timing": {
            "sync_drift_ps_rms": 5.0,
            "coincidence_window_ps": 300.0,
        },
        "protocol": {
            "name": normalized_protocol,
            "sifting_factor": 0.5,
            "ec_efficiency": 1.16,
        },
        "uncertainty": {},
    }

    if normalized_protocol == "BB84_DECOY":
        scenario["protocol"].update(
            {
                "mu": 0.5,
                "nu": 0.1,
                "omega": 0.0,
                "misalignment_prob": 0.015,
            }
        )
    elif normalized_protocol == "BBM92":
        scenario["source"] = {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100.0,
            "collection_efficiency": 0.35,
            "coupling_efficiency": float(effective_coupling),
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5.0,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "physics_backend": "analytic",
        }

    return scenario


def _select_wavelength_point(sim_result: dict[str, Any], *, wavelength_nm: float) -> dict[str, Any]:
    if not isinstance(sim_result, dict):
        return {}

    sweep = sim_result.get("sweep") if isinstance(sim_result.get("sweep"), dict) else {}
    points = sweep.get("points")
    if not isinstance(points, list) or not points:
        return sim_result

    best_row: dict[str, Any] | None = None
    best_delta = float("inf")
    target = float(wavelength_nm)
    for row in points:
        if not isinstance(row, dict):
            continue
        row_wavelength = _as_finite_float(row.get("wavelength_nm"))
        if row_wavelength is None:
            continue
        delta = abs(row_wavelength - target)
        if delta < best_delta:
            best_delta = delta
            best_row = row

    return best_row if isinstance(best_row, dict) else sim_result


def _component_cells_from_pdk(pdk: Any) -> list[dict[str, Any]]:
    if isinstance(pdk, dict):
        cells = pdk.get("component_cells")
        return [dict(row) for row in cells] if isinstance(cells, list) else []

    cells = getattr(pdk, "component_cells", None)
    if isinstance(cells, list):
        out: list[dict[str, Any]] = []
        for row in cells:
            if isinstance(row, dict):
                out.append(dict(row))
        return out
    return []


def _looks_like_io_coupler_cell(cell: dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            str(cell.get("name") or ""),
            str(cell.get("cell") or ""),
            str(cell.get("library") or ""),
            str(cell.get("kind") or ""),
            str((cell.get("metadata") or {}).get("name") or "") if isinstance(cell.get("metadata"), dict) else "",
        ]
    ).strip().lower()
    if not haystack:
        return False

    has_coupler = "coupler" in haystack or "gc" in haystack or "ec" in haystack
    has_io_hint = "grating" in haystack or "edge" in haystack
    return bool(has_coupler and has_io_hint)


def _extract_il_db(cell: dict[str, Any]) -> float | None:
    for key in ("nominal_il_db", "insertion_loss_db"):
        value = _as_finite_float(cell.get(key))
        if value is not None:
            return value

    metadata = cell.get("metadata")
    if isinstance(metadata, dict):
        for key in ("nominal_il_db", "insertion_loss_db"):
            value = _as_finite_float(metadata.get(key))
            if value is not None:
                return value
    return None


def _as_finite_float(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def _non_negative_float(value: Any) -> float | None:
    out = _as_finite_float(value)
    if out is None or out < 0.0:
        return None
    return float(out)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
