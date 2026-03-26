"""Config loading and scenario expansion."""

from __future__ import annotations

import copy
import math
from pathlib import Path
from typing import Callable

import yaml
import jax

jax.config.update("jax_enable_x64", True)

from photonstrust.errors import ConfigError
from photonstrust.presets import BAND_PRESETS, get_band_preset, get_detector_preset


CURRENT_CONFIG_SCHEMA_VERSION = "0.1"
LEGACY_CONFIG_SCHEMA_VERSION = "0.0"
SUPPORTED_CONFIG_SCHEMA_VERSIONS = {CURRENT_CONFIG_SCHEMA_VERSION}


class ConfigSchemaVersionError(ValueError):
    """Raised when a scenario config schema version is unsupported."""


_ConfigMigrationFn = Callable[[dict], dict]


def _migrate_config_0_0_to_0_1(config: dict) -> dict:
    migrated = copy.deepcopy(config)
    migrated["schema_version"] = "0.1"
    return migrated


_CONFIG_SCHEMA_MIGRATIONS: dict[str, tuple[str, _ConfigMigrationFn]] = {
    LEGACY_CONFIG_SCHEMA_VERSION: (CURRENT_CONFIG_SCHEMA_VERSION, _migrate_config_0_0_to_0_1),
}


def _normalize_config_schema_version(raw: object) -> str:
    version = str(raw).strip().lower()
    if version in {"", "0", "v0", "0.0", "v0.0"}:
        return LEGACY_CONFIG_SCHEMA_VERSION
    if version in {"0.1", "v0.1", "v0_1"}:
        return "0.1"
    return str(raw).strip()


def _unsupported_schema_version_error(*, path: Path, version: str) -> ConfigSchemaVersionError:
    supported = ", ".join(sorted(SUPPORTED_CONFIG_SCHEMA_VERSIONS))
    return ConfigSchemaVersionError(
        "Unsupported scenario config schema_version "
        f"{version!r} in {path}. Supported versions: {supported}. "
        "If this is a legacy config, migrate it to schema_version '0.1' "
        "(see docs/audit/03_configuration_validation.md)."
    )


def _apply_config_schema_governance(config: object, *, path: Path) -> dict:
    if not isinstance(config, dict):
        raise ConfigSchemaVersionError(f"Config root must be a mapping in {path}")

    migrated = copy.deepcopy(config)
    raw_version = migrated.get("schema_version", LEGACY_CONFIG_SCHEMA_VERSION)
    current_version = _normalize_config_schema_version(raw_version)

    while current_version not in SUPPORTED_CONFIG_SCHEMA_VERSIONS:
        step = _CONFIG_SCHEMA_MIGRATIONS.get(current_version)
        if step is None:
            raise _unsupported_schema_version_error(path=path, version=current_version)
        next_version, migrate_fn = step
        migrated = migrate_fn(migrated)
        current_version = _normalize_config_schema_version(next_version)

    migrated["schema_version"] = current_version
    return migrated


def load_config(path: str | Path) -> dict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    return _apply_config_schema_governance(config, path=path)


def apply_source_defaults(source: dict) -> dict:
    """Public wrapper for source defaults (used by OrbitVerify templates)."""

    return _apply_source_defaults(source)


def apply_channel_defaults(channel: dict, band: str) -> dict:
    """Public wrapper for channel defaults (used by OrbitVerify templates)."""

    return _apply_channel_defaults(channel, band)


def apply_detector_defaults(detector: dict, band: str) -> dict:
    """Public wrapper for detector defaults (used by OrbitVerify templates)."""

    return _apply_detector_defaults(detector, band)


def apply_timing_defaults(timing: dict) -> dict:
    """Public wrapper for timing defaults (used by OrbitVerify templates)."""

    return _apply_timing_defaults(timing)


def resolve_band_wavelength(band: str, wavelength_nm: float | None) -> float:
    """Resolve wavelength from band preset unless explicitly provided."""

    return _resolve_band_wavelength(band, wavelength_nm)


def _expand_distance(distance):
    if isinstance(distance, (int, float)):
        return [float(distance)]
    start = float(distance["start"])
    stop = float(distance["stop"])
    step = float(distance["step"])
    if not math.isfinite(step) or step <= 0.0:
        raise ConfigError(
            f"distance_km step must be > 0, got {step!r}",
            suggestion="Use a positive step value, e.g. distance_km: {start: 0, stop: 100, step: 10}.",
        )
    if not math.isfinite(start) or not math.isfinite(stop):
        raise ConfigError(
            f"distance_km start/stop must be finite, got start={start!r} stop={stop!r}",
            suggestion="Use finite numeric values for distance_km start and stop.",
        )
    if stop < start:
        raise ConfigError(
            f"distance_km stop must be >= start, got start={start!r} stop={stop!r}",
            suggestion="Ensure stop >= start in distance_km range specification.",
        )

    # Use round() to avoid cumulative floating-point drift and ensure stop is included.
    count = int(round((stop - start) / step)) + 1
    return [round(start + i * step, 10) for i in range(count)]


def _apply_source_defaults(source):
    source = copy.deepcopy(source)
    source.setdefault("rep_rate_mhz", 100)
    source.setdefault("collection_efficiency", 0.35)
    source.setdefault("coupling_efficiency", 0.60)
    source.setdefault("physics_backend", "analytic")
    source.setdefault("emission_mode", "steady_state")
    if source["type"] == "emitter_cavity":
        source.setdefault("radiative_lifetime_ns", 1.0)
        source.setdefault("purcell_factor", 5)
        source.setdefault("dephasing_rate_per_ns", 0.5)
        source.setdefault("g2_0", 0.02)
        source.setdefault("drive_strength", 0.05)
        source.setdefault("pulse_window_ns", 5.0 * source["radiative_lifetime_ns"])
        source.setdefault("transient_steps", 64)
    elif source["type"] == "spdc":
        source.setdefault("mu", 0.05)
    return source


def _apply_channel_defaults(channel, band):
    channel = copy.deepcopy(channel)
    model = str(channel.get("model", "fiber")).lower()
    channel["model"] = model

    if model in {"free_space", "satellite"}:
        channel.setdefault("connector_loss_db", 1.0)
        channel.setdefault("dispersion_ps_per_km", 0.0)
        channel.setdefault("elevation_deg", 45.0)
        channel.setdefault("tx_aperture_m", 0.12)
        channel.setdefault("rx_aperture_m", 0.30)
        channel.setdefault("beam_divergence_urad", None)
        channel.setdefault("atmosphere_path_model", "effective_thickness")
        channel.setdefault("atmosphere_effective_thickness_km", 20.0)
        channel.setdefault("pointing_jitter_urad", 1.5)
        channel.setdefault("pointing_model", "deterministic")
        channel.setdefault("pointing_bias_urad", 0.0)
        channel.setdefault("pointing_sample_count", 256)
        channel.setdefault("pointing_seed", None)
        channel.setdefault("pointing_outage_threshold_eta", 0.1)
        channel.setdefault("atmospheric_extinction_db_per_km", 0.02)
        channel.setdefault("turbulence_scintillation_index", 0.15)
        channel.setdefault("turbulence_model", "deterministic")
        channel.setdefault("turbulence_sample_count", 256)
        channel.setdefault("turbulence_seed", None)
        channel.setdefault("turbulence_outage_threshold_eta", 0.1)
        channel.setdefault("outage_eta_threshold", 1.0e-6)
        channel.setdefault("background_counts_cps", 0.0)
        channel.setdefault("background_model", "fixed")
        channel.setdefault("background_day_night", "night")
        channel.setdefault("background_fov_urad", 100.0)
        channel.setdefault("background_filter_bandwidth_nm", 1.0)
        channel.setdefault("background_detector_gate_ns", 1.0)
        channel.setdefault("background_site_light_pollution", 0.2)
        channel.setdefault("background_base_night_cps", 250.0)
        channel.setdefault("background_day_factor", 9.0)
        channel.setdefault("background_uncertainty_rel", 0.05)
        channel.setdefault("background_counts_cps_scale", 1.0)
        channel.setdefault("fiber_loss_db_per_km", 0.0)
        if model == "satellite":
            channel.setdefault("satellite_uplink_fraction", 0.5)
            channel.setdefault("uplink_elevation_deg", channel.get("elevation_deg", 45.0))
            channel.setdefault("downlink_elevation_deg", channel.get("elevation_deg", 45.0))
        return channel

    band_preset = get_band_preset(band)
    if channel.get("fiber_loss_db_per_km") is None:
        channel["fiber_loss_db_per_km"] = band_preset["fiber_loss_db_per_km"]
    if channel.get("dispersion_ps_per_km") is None:
        channel["dispersion_ps_per_km"] = band_preset["dispersion_ps_per_km"]
    channel.setdefault("connector_loss_db", 1.5)
    return channel


def _apply_detector_defaults(detector, band):
    detector = copy.deepcopy(detector)
    detector_class = detector["class"]
    preset = get_detector_preset(detector_class, band)
    detector.setdefault("physics_backend", "analytic")
    detector.setdefault("sample_count", 500)
    detector.setdefault("time_bin_ps", 10.0)
    detector.setdefault("afterpulse_delay_ns", 50.0)
    for key, value in preset.items():
        if detector.get(key) is None:
            detector[key] = value
    return detector


def _apply_timing_defaults(timing):
    timing = copy.deepcopy(timing)
    timing.setdefault("sync_drift_ps_rms", 10)
    return timing


def _resolve_band_wavelength(band, wavelength_nm):
    preset = get_band_preset(band)
    return wavelength_nm if wavelength_nm is not None else preset["wavelength_nm"]


def build_scenarios(config: dict) -> list[dict]:
    if "matrix_sweep" in config:
        return _build_matrix_scenarios(config["matrix_sweep"])
    return _build_single_scenarios(config)


def _build_single_scenarios(config: dict) -> list[dict]:
    scenario = config["scenario"]
    bands = scenario.get("band")
    if bands is None:
        bands = list(BAND_PRESETS.keys())
    elif isinstance(bands, str):
        bands = [bands]

    distances = _expand_distance(scenario["distance_km"])
    execution_mode = str(scenario.get("execution_mode", "standard"))
    preview_uncertainty_samples = int(scenario.get("preview_uncertainty_samples", 40))
    preview_detector_sample_scale = float(scenario.get("preview_detector_sample_scale", 0.25))
    certification_uncertainty_samples = int(scenario.get("certification_uncertainty_samples", 400))
    certification_detector_sample_scale = float(
        scenario.get("certification_detector_sample_scale", 1.5)
    )
    finite_key = copy.deepcopy(config.get("finite_key", {}))
    reliability_card_version = scenario.get("reliability_card_version")
    if reliability_card_version is None:
        reliability_card_version = scenario.get("card_version")
    scenarios = []
    for band in bands:
        band_wavelength = _resolve_band_wavelength(band, scenario.get("wavelength_nm"))
        source = _apply_source_defaults(config["source"])
        channel = _apply_channel_defaults(config["channel"], band)
        detector = _apply_detector_defaults(config["detector"], band)
        timing = _apply_timing_defaults(config["timing"])
        scenarios.append(
            {
                "scenario_id": scenario["id"],
                "band": band,
                "wavelength_nm": band_wavelength,
                "distances_km": distances,
                "source": source,
                "channel": channel,
                "detector": detector,
                "timing": timing,
                "protocol": config["protocol"],
                "uncertainty": config["uncertainty"],
                "finite_key": finite_key,
                "reliability_card_version": reliability_card_version,
                "execution_mode": execution_mode,
                "preview_uncertainty_samples": preview_uncertainty_samples,
                "preview_detector_sample_scale": preview_detector_sample_scale,
                "certification_uncertainty_samples": certification_uncertainty_samples,
                "certification_detector_sample_scale": certification_detector_sample_scale,
            }
        )
    return scenarios


def _build_matrix_scenarios(matrix: dict) -> list[dict]:
    distances = _expand_distance(matrix["distance_km"])
    scenarios = []
    band_presets = matrix["band_presets"]
    detector_presets = matrix["detector_presets"]
    overrides = matrix.get("overrides", {})
    detector_adjustments = matrix.get("detector_adjustments", {})
    realism_filters = matrix.get("realism_filters", {})
    compatibility = matrix.get("compatibility", {})

    band_detector_pairs = matrix.get("band_detector_pairs")
    if band_detector_pairs:
        pairs = [(entry["band"], entry["detector"]) for entry in band_detector_pairs]
    else:
        pairs = [(band, det) for band in matrix["bands"] for det in matrix["detectors"]]

    for band, detector_class in pairs:
        if realism_filters.get("enforce_detector_band_match"):
            allowed = compatibility.get(band, [])
            if allowed and detector_class not in allowed:
                continue
        for source_type in matrix["sources"]:
            scenario_id = matrix["naming"]["scenario_id_format"].format(
                band=band, detector=detector_class, source=source_type
            )
            band_preset = band_presets[band]
            detector_preset = detector_presets[detector_class]

            source = copy.deepcopy(overrides.get("source", {}))
            source["type"] = source_type
            source = _apply_source_defaults(source)

            channel = copy.deepcopy(overrides.get("channel", {}))
            channel.setdefault("fiber_loss_db_per_km", band_preset["fiber_loss_db_per_km"])
            channel.setdefault("dispersion_ps_per_km", band_preset["dispersion_ps_per_km"])
            channel.setdefault("connector_loss_db", 1.5)

            detector = copy.deepcopy(overrides.get("detector", {}))
            detector["class"] = detector_class
            for key, value in detector_preset.items():
                detector.setdefault(key, value)
            adjustments = detector_adjustments.get(band, {}).get(detector_class)
            if adjustments:
                detector["pde"] = max(0.0, min(1.0, detector["pde"] + adjustments.get("pde_delta", 0.0)))
                detector["dark_counts_cps"] *= adjustments.get("dark_scale", 1.0)
            min_pde = realism_filters.get("min_pde")
            if min_pde is not None and detector["pde"] < min_pde:
                continue

            timing = copy.deepcopy(overrides.get("timing", {}))
            timing = _apply_timing_defaults(timing)

            output_root = matrix.get("output_dir", "results/demo1_matrix")
            scenarios.append(
                {
                    "scenario_id": scenario_id,
                    "band": band,
                    "wavelength_nm": band_preset["wavelength_nm"],
                    "distances_km": distances,
                    "source": source,
                    "channel": channel,
                    "detector": detector,
                    "timing": timing,
                    "protocol": overrides.get("protocol", {}),
                    "uncertainty": overrides.get("uncertainty", {}),
                    "finite_key": overrides.get("finite_key", {}),
                    "output_dir": f"{output_root}/{scenario_id}",
                }
            )
    max_total = matrix.get("run_limits", {}).get("max_total_runs")
    if max_total:
        return scenarios[: int(max_total)]
    return scenarios
