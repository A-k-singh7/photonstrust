"""Entanglement-based QKD performance model."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

from photonstrust.channels.engine import compute_channel_diagnostics
from photonstrust.physics.emitter import get_emitter_stats
from photonstrust.qkd_protocols.registry import resolve_protocol_module
from photonstrust.qkd_types import QKDResult
from photonstrust.utils import clamp


def compute_sweep(scenario: dict, include_uncertainty: bool = True) -> dict:
    mode_settings = _mode_settings(scenario)
    t0 = time.perf_counter()
    results = []
    for distance in scenario["distances_km"]:
        results.append(compute_point(scenario, distance, runtime_overrides=mode_settings))

    uncertainty = None
    if include_uncertainty:
        uncertainty = _compute_uncertainty(
            scenario,
            samples=mode_settings["uncertainty_samples"],
            runtime_overrides=mode_settings,
        )
    elapsed_s = time.perf_counter() - t0
    return {
        "results": results,
        "uncertainty": uncertainty,
        "performance": {
            "execution_mode": mode_settings["execution_mode"],
            "uncertainty_samples": mode_settings["uncertainty_samples"],
            "uncertainty_workers": mode_settings["uncertainty_workers"],
            "detector_sample_scale": mode_settings["detector_sample_scale"],
            "elapsed_s": elapsed_s,
        },
    }


def compute_point(
    scenario: dict,
    distance_km: float,
    runtime_overrides: dict | None = None,
) -> QKDResult:
    protocol_cfg = (scenario or {}).get("protocol", {}) or {}
    module = resolve_protocol_module(protocol_cfg.get("name"))
    applicability = module.applicability(scenario)
    if applicability.status == "fail":
        reason = "; ".join(applicability.reasons) if applicability.reasons else "unsupported configuration"
        raise ValueError(f"Protocol applicability failed for {module.protocol_id!r}: {reason}")

    result = module.evaluate_point(scenario, float(distance_km), runtime_overrides=runtime_overrides)
    if not str(getattr(result, "protocol_name", "") or "").strip():
        result.protocol_name = module.protocol_id
    return result


def _compute_uncertainty(
    scenario: dict,
    samples: int = 200,
    runtime_overrides: dict | None = None,
) -> dict | None:
    uncertainty = scenario.get("uncertainty", {})
    if not uncertainty:
        return None

    base = scenario
    distances = base["distances_km"]
    seed_raw = (uncertainty or {}).get("seed", scenario.get("seed", 42))
    try:
        seed_base = int(seed_raw)
    except (TypeError, ValueError):
        seed_base = 42
    if seed_base < 0:
        # numpy requires non-negative integer seeds
        seed_base = 0

    workers = int((runtime_overrides or {}).get("uncertainty_workers", 1))
    workers = max(1, workers)

    if workers == 1:
        sample_rows = [
            _compute_uncertainty_sample(base, uncertainty, seed_base, sample_idx, runtime_overrides)
            for sample_idx in range(samples)
        ]
    else:
        sample_rows = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(_compute_uncertainty_sample, base, uncertainty, seed_base, sample_idx, runtime_overrides)
                for sample_idx in range(samples)
            ]
            for future in as_completed(futures):
                sample_rows.append(future.result())
        sample_rows.sort(key=lambda row: row["sample_idx"])

    key_rate_samples = {distance: [] for distance in distances}
    channel_eta_samples = {distance: [] for distance in distances}
    channel_loss_samples = {distance: [] for distance in distances}
    decomposition_samples = {distance: {} for distance in distances}

    for row in sample_rows:
        for distance in distances:
            distance_stats = row["by_distance"][distance]
            key_rate_samples[distance].append(distance_stats["key_rate_bps"])
            channel_eta_samples[distance].append(distance_stats["eta_channel"])
            channel_loss_samples[distance].append(distance_stats["total_loss_db"])
            for key, value in distance_stats["decomposition"].items():
                decomposition_samples[distance].setdefault(key, []).append(value)

    ci = {}
    outage_threshold = float(scenario.get("protocol", {}).get("key_rate_floor_bps", 0.0))
    for distance, values in key_rate_samples.items():
        values_arr = np.array(values)
        item = {
            "low": float(np.quantile(values_arr, 0.05)),
            "high": float(np.quantile(values_arr, 0.95)),
            "outage_probability": float(np.mean(values_arr <= outage_threshold)),
            "channel_interval": {
                "eta_channel": _interval(channel_eta_samples[distance]),
                "total_loss_db": _interval(channel_loss_samples[distance]),
                "decomposition": {
                    key: _interval(samples_v)
                    for key, samples_v in decomposition_samples[distance].items()
                    if samples_v
                },
            },
        }
        ci[distance] = item
    return ci


def _compute_uncertainty_sample(
    base: dict,
    uncertainty: dict,
    seed_base: int,
    sample_idx: int,
    runtime_overrides: dict | None,
) -> dict:
    rng = np.random.default_rng(seed_base + sample_idx)
    varied = _apply_uncertainty(base, uncertainty, rng)
    by_distance = {}

    for distance in base["distances_km"]:
        point = compute_point(varied, distance, runtime_overrides=runtime_overrides)
        ch = compute_channel_diagnostics(
            distance_km=float(distance),
            wavelength_nm=float(varied.get("wavelength_nm", base.get("wavelength_nm", 1550.0)) or 1550.0),
            channel_cfg=varied.get("channel", {}),
        )
        decomposition = {}
        for key, value in (ch.get("decomposition", {}) or {}).items():
            try:
                decomposition[str(key)] = float(value)
            except (TypeError, ValueError):
                continue

        by_distance[distance] = {
            "key_rate_bps": point.key_rate_bps,
            "eta_channel": float(ch.get("eta_channel", 0.0) or 0.0),
            "total_loss_db": float(ch.get("total_loss_db", 0.0) or 0.0),
            "decomposition": decomposition,
        }

    return {
        "sample_idx": sample_idx,
        "by_distance": by_distance,
    }


def _apply_uncertainty(base: dict, uncertainty: dict, rng: np.random.Generator) -> dict:
    scenario = {key: copy_value(value) for key, value in base.items()}
    channel = scenario["channel"]
    detector = scenario["detector"]
    source = scenario["source"]

    if "fiber_loss_db_per_km" in uncertainty and "fiber_loss_db_per_km" in channel:
        span = uncertainty["fiber_loss_db_per_km"]
        channel["fiber_loss_db_per_km"] = max(
            0.0,
            channel["fiber_loss_db_per_km"] + rng.uniform(-span, span),
        )
    if "connector_loss_db" in uncertainty and "connector_loss_db" in channel:
        span = uncertainty["connector_loss_db"]
        channel["connector_loss_db"] = max(0.0, channel["connector_loss_db"] + rng.uniform(-span, span))
    if "atmospheric_extinction_db_per_km" in uncertainty and "atmospheric_extinction_db_per_km" in channel:
        span = uncertainty["atmospheric_extinction_db_per_km"]
        channel["atmospheric_extinction_db_per_km"] = max(
            0.0,
            channel["atmospheric_extinction_db_per_km"] + rng.uniform(-span, span),
        )
    if "pointing_jitter_urad" in uncertainty and "pointing_jitter_urad" in channel:
        frac = uncertainty["pointing_jitter_urad"]
        channel["pointing_jitter_urad"] = max(
            0.0,
            channel["pointing_jitter_urad"] * rng.uniform(1 - frac, 1 + frac),
        )
    if "turbulence_scintillation_index" in uncertainty and "turbulence_scintillation_index" in channel:
        frac = uncertainty["turbulence_scintillation_index"]
        channel["turbulence_scintillation_index"] = max(
            0.0,
            channel["turbulence_scintillation_index"] * rng.uniform(1 - frac, 1 + frac),
        )
    if "pde" in uncertainty:
        frac = uncertainty["pde"]
        detector["pde"] = clamp(detector["pde"] * rng.uniform(1 - frac, 1 + frac), 0.0, 1.0)
    if "dark_counts" in uncertainty:
        factor = 2 ** uncertainty["dark_counts"]
        detector["dark_counts_cps"] = detector["dark_counts_cps"] * rng.uniform(1 / factor, factor)
    if "jitter" in uncertainty:
        frac = uncertainty["jitter"]
        detector["jitter_ps_fwhm"] = max(0.0, detector["jitter_ps_fwhm"] * rng.uniform(1 - frac, 1 + frac))
    if "g2_0" in uncertainty and source["type"] == "emitter_cavity":
        frac = uncertainty["g2_0"]
        source["g2_0"] = max(0.0, source["g2_0"] * rng.uniform(1 - frac, 1 + frac))
    if "mu" in uncertainty and source["type"] == "spdc":
        frac = uncertainty["mu"]
        source["mu"] = max(0.0, source["mu"] * rng.uniform(1 - frac, 1 + frac))
    return scenario


def _interval(values: list[float]) -> dict[str, float]:
    arr = np.array(values, dtype=float)
    return {
        "low": float(np.quantile(arr, 0.05)),
        "high": float(np.quantile(arr, 0.95)),
    }


def copy_value(value):
    if isinstance(value, dict):
        return {k: copy_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [copy_value(v) for v in value]
    return value


def _mode_settings(scenario: dict) -> dict:
    mode = str(scenario.get("execution_mode", "standard")).strip().lower()
    if mode not in {"standard", "preview", "certification"}:
        mode = "standard"

    settings = {
        "execution_mode": mode,
        "uncertainty_samples": 200,
        "uncertainty_workers": int(scenario.get("uncertainty_workers", 1)),
        "detector_sample_scale": 1.0,
    }
    if mode == "preview":
        settings["uncertainty_samples"] = int(scenario.get("preview_uncertainty_samples", 40))
        settings["uncertainty_workers"] = int(
            scenario.get("preview_uncertainty_workers", scenario.get("uncertainty_workers", 1))
        )
        settings["detector_sample_scale"] = float(scenario.get("preview_detector_sample_scale", 0.25))
    elif mode == "certification":
        settings["uncertainty_samples"] = int(scenario.get("certification_uncertainty_samples", 400))
        settings["uncertainty_workers"] = int(
            scenario.get("certification_uncertainty_workers", scenario.get("uncertainty_workers", 1))
        )
        settings["detector_sample_scale"] = float(scenario.get("certification_detector_sample_scale", 1.5))

    settings["uncertainty_samples"] = max(10, settings["uncertainty_samples"])
    settings["uncertainty_workers"] = max(1, settings["uncertainty_workers"])
    settings["detector_sample_scale"] = max(0.05, settings["detector_sample_scale"])
    return settings
