"""PIC process-parameter perturbation utilities."""

from __future__ import annotations

import copy
import math
import random
from collections.abc import Mapping
from typing import Any


def perturb_netlist(netlist: dict, process_params: dict, *, pdk: Any) -> dict:
    """Return a perturbed copy of a PIC netlist."""

    if not isinstance(netlist, dict):
        raise TypeError("netlist must be an object")
    if not isinstance(process_params, dict):
        process_params = {}

    perturbed = copy.deepcopy(netlist)
    nodes = perturbed.get("nodes")
    if not isinstance(nodes, list):
        return perturbed

    min_width_um = _design_rule_value(pdk, "min_waveguide_width_um", 0.45)
    min_gap_um = _design_rule_value(pdk, "min_waveguide_gap_um", 0.20)

    waveguide_width_nm = _first_numeric(
        process_params,
        ("waveguide_width_nm", "delta_waveguide_width_nm", "width_nm_delta", "width_delta_nm"),
    )
    propagation_loss_db_per_cm = _first_numeric(
        process_params,
        ("propagation_loss_db_per_cm", "waveguide_loss_db_per_cm", "loss_db_per_cm"),
    )
    coupler_gap_nm = _first_numeric(
        process_params,
        ("coupler_gap_nm", "gap_nm", "coupling_gap_nm", "delta_coupling_gap_nm", "gap_delta_nm"),
    )
    ring_width_nm = _first_numeric(
        process_params,
        ("ring_width_nm", "ring_resonator_width_nm", "delta_ring_width_nm"),
    )
    if ring_width_nm is None:
        ring_width_nm = waveguide_width_nm

    coupling_ratio_per_gap_um = _sensitivity_value(
        pdk,
        key="coupling_ratio_per_gap_um",
        default=-2.0,
    )
    ring_resonance_nm_per_width_nm = _sensitivity_value(
        pdk,
        key="ring_resonance_nm_per_width_nm",
        default=-0.01,
    )

    for node in nodes:
        if not isinstance(node, dict):
            continue
        params = node.get("params")
        if not isinstance(params, dict):
            params = {}
            node["params"] = params

        kind = str(node.get("kind", "")).strip().lower()
        is_waveguide_like = ("waveguide" in kind) or ("delay_line" in kind)
        is_coupler_like = ("coupler" in kind) or ("mmi" in kind)
        is_ring_like = ("ring" in kind)

        if is_waveguide_like:
            if waveguide_width_nm is not None:
                base_width_um = _first_numeric(
                    params,
                    ("width_um", "waveguide_width_um"),
                    fallback=min_width_um,
                )
                updated_width_um = max(0.01, float(base_width_um) + float(waveguide_width_nm) * 1.0e-3)
                params["width_um"] = float(updated_width_um)
                if "waveguide_width_um" in params:
                    params["waveguide_width_um"] = float(updated_width_um)

            if propagation_loss_db_per_cm is not None:
                loss_db_per_cm = max(0.0, float(propagation_loss_db_per_cm))
                params["loss_db_per_cm"] = loss_db_per_cm
                length_um = _first_numeric(params, ("length_um",), fallback=0.0)
                length_cm = max(0.0, float(length_um)) / 1.0e4
                insertion_loss_db = max(0.0, loss_db_per_cm * length_cm)
                params["insertion_loss_db"] = insertion_loss_db
                params["propagation_loss_db"] = insertion_loss_db

        if is_coupler_like and coupler_gap_nm is not None:
            base_gap_um = _first_numeric(params, ("gap_um",), fallback=min_gap_um)
            updated_gap_um = max(0.01, float(base_gap_um) + float(coupler_gap_nm) * 1.0e-3)
            params["gap_um"] = float(updated_gap_um)

            base_ratio = _clamp01(_first_numeric(params, ("coupling_ratio",), fallback=0.5))
            delta_gap_um = float(updated_gap_um) - float(base_gap_um)
            updated_ratio = base_ratio * math.exp(float(coupling_ratio_per_gap_um) * delta_gap_um)
            params["coupling_ratio"] = _clamp01(updated_ratio)

        if is_ring_like and ring_width_nm is not None:
            base_width_um_ring = _first_numeric(params, ("width_um", "waveguide_width_um"))
            if base_width_um_ring is not None:
                updated_width_um_ring = max(0.01, float(base_width_um_ring) + float(ring_width_nm) * 1.0e-3)
                params["width_um"] = float(updated_width_um_ring)
                if "waveguide_width_um" in params:
                    params["waveguide_width_um"] = float(updated_width_um_ring)

            base_resonance_nm = _first_numeric(params, ("resonance_nm",))
            if base_resonance_nm is not None:
                params["resonance_nm"] = float(
                    float(base_resonance_nm)
                    + float(ring_resonance_nm_per_width_nm) * float(ring_width_nm)
                )

    return perturbed


def sample_process_parameters(pdk: Any, *, seed: int, sigma_multiplier: float = 1.0) -> dict:
    """Sample process parameters using PDK corner metadata."""

    rng = random.Random(int(seed))
    scale = max(0.0, float(sigma_multiplier))
    stats = _parameter_statistics_from_pdk(pdk)

    out: dict[str, float] = {}
    for key in sorted(stats.keys()):
        center = float(stats[key]["center"])
        sigma = max(0.0, float(stats[key]["sigma"])) * scale
        sample = center if sigma <= 0.0 else rng.gauss(center, sigma)
        out[str(key)] = float(sample)
    return out


def _parameter_statistics_from_pdk(pdk: Any) -> dict[str, dict[str, float]]:
    corners = _process_corners_from_pdk(pdk)
    value_lists: dict[str, list[float]] = {}
    tt_values: dict[str, float] = {}

    for corner_name, payload in corners.items():
        if not isinstance(payload, Mapping):
            continue
        flattened = _flatten_numeric_mapping(payload)
        for key, value in flattened.items():
            value_lists.setdefault(key, []).append(float(value))
            if str(corner_name).strip().upper() == "TT":
                tt_values[str(key)] = float(value)

    if not value_lists:
        return {
            "waveguide_width_nm": {"center": 0.0, "sigma": 1.0},
            "propagation_loss_db_per_cm": {"center": 0.0, "sigma": 0.05},
            "coupler_gap_nm": {"center": 0.0, "sigma": 2.0},
            "ring_width_nm": {"center": 0.0, "sigma": 1.0},
        }

    stats: dict[str, dict[str, float]] = {}
    for key in sorted(value_lists.keys()):
        values = value_lists[key]
        center = float(tt_values.get(key, _mean(values)))
        sigma = float(_stddev_population(values))
        if sigma <= 0.0:
            sigma = _fallback_sigma_for_param(key=key, center=center)
        stats[str(key)] = {"center": center, "sigma": sigma}
    return stats


def _fallback_sigma_for_param(*, key: str, center: float) -> float:
    norm = str(key).strip().lower()
    if norm.endswith("_nm"):
        return 1.0
    if "loss" in norm and "db_per_cm" in norm:
        return 0.05
    if "coupling_ratio" in norm:
        return 0.02
    return max(1.0e-6, abs(float(center)) * 0.10)


def _process_corners_from_pdk(pdk: Any) -> dict[str, Any]:
    payload: Any = None
    if isinstance(pdk, Mapping):
        payload = pdk.get("process_corners")
    else:
        payload = getattr(pdk, "process_corners", None)
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _design_rule_value(pdk: Any, key: str, default: float) -> float:
    rules: Any = {}
    if isinstance(pdk, Mapping):
        rules = pdk.get("design_rules")
    else:
        rules = getattr(pdk, "design_rules", None)
    if isinstance(rules, Mapping):
        parsed = _to_float(rules.get(key))
        if parsed is not None:
            return float(parsed)
    return float(default)


def _sensitivity_value(pdk: Any, *, key: str, default: float) -> float:
    coeffs: Any = {}
    if isinstance(pdk, Mapping):
        coeffs = pdk.get("sensitivity_coefficients")
    else:
        coeffs = getattr(pdk, "sensitivity_coefficients", None)
    if isinstance(coeffs, Mapping):
        flattened = _flatten_numeric_mapping(coeffs)
        value = flattened.get(key)
        if value is not None:
            return float(value)
    return float(default)


def _flatten_numeric_mapping(payload: Mapping[str, Any], *, prefix: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    for raw_key in sorted(payload.keys(), key=lambda v: str(v)):
        key = str(raw_key)
        value = payload[raw_key]
        full_key = key if not prefix else f"{prefix}.{key}"
        parsed = _to_float(value)
        if parsed is not None:
            out[full_key] = float(parsed)
            if "." in full_key:
                out[key] = float(parsed)
            continue
        if isinstance(value, Mapping):
            nested = _flatten_numeric_mapping(value, prefix=full_key)
            for nested_key, nested_value in nested.items():
                out[nested_key] = float(nested_value)
    return out


def _first_numeric(payload: dict[str, Any], keys: tuple[str, ...], fallback: float | None = None) -> float | None:
    for key in keys:
        value = _to_float(payload.get(key))
        if value is not None:
            return float(value)
    return float(fallback) if fallback is not None else None


def _to_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return float(parsed)


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _stddev_population(values: list[float]) -> float:
    if len(values) <= 1:
        return 0.0
    mu = _mean(values)
    variance = sum((float(v) - mu) ** 2 for v in values) / len(values)
    return float(math.sqrt(max(0.0, variance)))
