"""Orbit pass envelope semantic diagnostics (beyond JSON Schema).

This module provides backend-owned validation of OrbitVerify pass envelope configs:
- required fields and types
- known-sense physical ranges (elevation, distance, non-negativity)
- consistency checks (monotonic sample times, dt_s vs sample spacing) as warnings

It is intentionally deterministic and side-effect free.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from photonstrust.presets import BAND_PRESETS, DETECTOR_PRESETS


@dataclass(frozen=True)
class Diagnostic:
    level: str  # "error" | "warning"
    code: str
    message: str
    ref: dict[str, Any]


def _diag(level: str, code: str, message: str, ref: dict[str, Any] | None = None) -> Diagnostic:
    return Diagnostic(level=str(level), code=str(code), message=str(message), ref=dict(ref or {}))


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_orbit_pass_semantics(config: dict) -> dict[str, Any]:
    """Return semantic diagnostics for an Orbit pass envelope config dict.

    Output format:
    - errors: list[dict]
    - warnings: list[dict]
    - summary: dict
    """

    if not isinstance(config, dict):
        raise TypeError("validate_orbit_pass_semantics expects a config dict")

    errors: list[Diagnostic] = []
    warnings: list[Diagnostic] = []

    orbit_pass = config.get("orbit_pass")
    if not isinstance(orbit_pass, dict):
        errors.append(
            _diag(
                "error",
                "orbit_pass.block",
                "orbit_pass config block is required and must be an object.",
                {"path": "orbit_pass"},
            )
        )
        return _finalize(errors, warnings)

    pass_id = str(orbit_pass.get("id", "")).strip()
    if not pass_id:
        errors.append(_diag("error", "orbit_pass.id", "orbit_pass.id is required.", {"path": "orbit_pass.id"}))

    band = str(orbit_pass.get("band", "")).strip()
    if not band:
        errors.append(_diag("error", "orbit_pass.band", "orbit_pass.band is required.", {"path": "orbit_pass.band"}))
    elif band not in BAND_PRESETS:
        errors.append(
            _diag(
                "error",
                "orbit_pass.band",
                f"Unknown band {band!r}. Expected one of {sorted(BAND_PRESETS.keys())}.",
                {"path": "orbit_pass.band", "band": band},
            )
        )

    dt_raw = orbit_pass.get("dt_s")
    dt_s = None
    if dt_raw is None:
        errors.append(_diag("error", "orbit_pass.dt_s", "orbit_pass.dt_s is required.", {"path": "orbit_pass.dt_s"}))
    elif not _is_number(dt_raw):
        errors.append(
            _diag(
                "error",
                "orbit_pass.dt_s",
                f"orbit_pass.dt_s must be a number, got {type(dt_raw).__name__}.",
                {"path": "orbit_pass.dt_s"},
            )
        )
    else:
        dt_s = float(dt_raw)
        if dt_s <= 0.0:
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.dt_s",
                    f"orbit_pass.dt_s must be > 0, got {dt_raw}.",
                    {"path": "orbit_pass.dt_s"},
                )
            )

    execution_mode = orbit_pass.get("execution_mode")
    if execution_mode is not None:
        mode = str(execution_mode).strip().lower()
        if mode not in {"preview", "certification"}:
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.execution_mode",
                    "orbit_pass.execution_mode must be 'preview' or 'certification' when provided.",
                    {"path": "orbit_pass.execution_mode", "value": mode},
                )
            )

    background_model = str(
        orbit_pass.get(
            "background_model",
            ((config.get("channel") or {}).get("background_model") if isinstance(config.get("channel"), dict) else "fixed"),
        )
        or "fixed"
    ).strip().lower()
    if background_model not in {"fixed", "radiance_proxy"}:
        errors.append(
            _diag(
                "error",
                "orbit_pass.background_model",
                "orbit_pass.background_model must be one of: fixed, radiance_proxy.",
                {"path": "orbit_pass.background_model", "value": background_model},
            )
        )

    samples_cfg = orbit_pass.get("samples")
    if not isinstance(samples_cfg, list) or not samples_cfg:
        errors.append(
            _diag(
                "error",
                "orbit_pass.samples",
                "orbit_pass.samples must be a non-empty list of sample objects.",
                {"path": "orbit_pass.samples"},
            )
        )
        return _finalize(errors, warnings)

    times: list[float] = []
    for idx, item in enumerate(samples_cfg):
        path_prefix = f"orbit_pass.samples[{idx}]"
        if not isinstance(item, dict):
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.sample.type",
                    "Each orbit_pass.samples entry must be an object.",
                    {"path": path_prefix},
                )
            )
            continue

        t = item.get("t_s")
        if not _is_number(t):
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.sample.t_s",
                    f"{path_prefix}.t_s must be a number, got {type(t).__name__}.",
                    {"path": f"{path_prefix}.t_s"},
                )
            )
        else:
            t_f = float(t)
            times.append(t_f)
            if t_f < 0.0:
                warnings.append(
                    _diag(
                        "warning",
                        "orbit_pass.sample.t_s_negative",
                        f"{path_prefix}.t_s is negative ({t_f}). This is allowed but uncommon.",
                        {"path": f"{path_prefix}.t_s", "t_s": t_f},
                    )
                )

        dist = item.get("distance_km")
        if not _is_number(dist):
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.sample.distance_km",
                    f"{path_prefix}.distance_km must be a number, got {type(dist).__name__}.",
                    {"path": f"{path_prefix}.distance_km"},
                )
            )
        else:
            d = float(dist)
            if d <= 0.0:
                errors.append(
                    _diag(
                        "error",
                        "orbit_pass.sample.distance_km",
                        f"{path_prefix}.distance_km must be > 0, got {dist}.",
                        {"path": f"{path_prefix}.distance_km", "distance_km": d},
                    )
                )

        elev = item.get("elevation_deg")
        if not _is_number(elev):
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.sample.elevation_deg",
                    f"{path_prefix}.elevation_deg must be a number, got {type(elev).__name__}.",
                    {"path": f"{path_prefix}.elevation_deg"},
                )
            )
        else:
            e = float(elev)
            if e < 0.0 or e > 90.0:
                errors.append(
                    _diag(
                        "error",
                        "orbit_pass.sample.elevation_deg",
                        f"{path_prefix}.elevation_deg must be within [0, 90], got {elev}.",
                        {"path": f"{path_prefix}.elevation_deg", "elevation_deg": e},
                    )
                )

        bg = item.get("background_counts_cps")
        if bg is not None:
            if not _is_number(bg):
                errors.append(
                    _diag(
                        "error",
                        "orbit_pass.sample.background_counts_cps",
                        f"{path_prefix}.background_counts_cps must be a number, got {type(bg).__name__}.",
                        {"path": f"{path_prefix}.background_counts_cps"},
                    )
                )
            else:
                b = float(bg)
                if b < 0.0:
                    errors.append(
                        _diag(
                            "error",
                            "orbit_pass.sample.background_counts_cps",
                            f"{path_prefix}.background_counts_cps must be >= 0, got {bg}.",
                            {"path": f"{path_prefix}.background_counts_cps", "background_counts_cps": b},
                        )
                    )

        day_night = item.get("day_night")
        if day_night is not None:
            mode = str(day_night).strip().lower()
            if mode not in {"day", "night"}:
                errors.append(
                    _diag(
                        "error",
                        "orbit_pass.sample.day_night",
                        f"{path_prefix}.day_night must be 'day' or 'night' when provided.",
                        {"path": f"{path_prefix}.day_night", "value": mode},
                    )
                )

    if times:
        # If the UI provides unsorted samples, warn rather than fail.
        if times != sorted(times):
            warnings.append(
                _diag(
                    "warning",
                    "orbit_pass.samples.time_order",
                    "orbit_pass.samples are not sorted by t_s. Execution will sort them.",
                    {"path": "orbit_pass.samples"},
                )
            )

        # dt_s consistency is advisory; only warn.
        if dt_s is not None and len(times) >= 2:
            diffs = [float(sorted(times)[i + 1] - sorted(times)[i]) for i in range(len(times) - 1)]
            tol = max(1e-6, 1e-3 * float(dt_s))
            bad = [d for d in diffs if abs(d - float(dt_s)) > tol]
            if bad:
                warnings.append(
                    _diag(
                        "warning",
                        "orbit_pass.dt_s.spacing",
                        f"Sample spacing differs from dt_s={dt_s}. This may bias integration over the pass.",
                        {"path": "orbit_pass.dt_s", "dt_s": dt_s, "diffs_s": diffs},
                    )
                )

    # Availability (optional).
    availability_cfg = orbit_pass.get("availability")
    if availability_cfg is not None:
        if not isinstance(availability_cfg, dict):
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.availability",
                    "orbit_pass.availability must be an object when provided.",
                    {"path": "orbit_pass.availability"},
                )
            )
        elif "clear_fraction" in availability_cfg:
            cf = availability_cfg.get("clear_fraction")
            if cf is None:
                errors.append(
                    _diag(
                        "error",
                        "orbit_pass.availability.clear_fraction",
                        "orbit_pass.availability.clear_fraction must not be null when provided.",
                        {"path": "orbit_pass.availability.clear_fraction"},
                    )
                )
            elif not _is_number(cf):
                errors.append(
                    _diag(
                        "error",
                        "orbit_pass.availability.clear_fraction",
                        f"orbit_pass.availability.clear_fraction must be a number, got {type(cf).__name__}.",
                        {"path": "orbit_pass.availability.clear_fraction"},
                    )
                )
            else:
                cf_f = float(cf)
                if cf_f < 0.0 or cf_f > 1.0:
                    errors.append(
                        _diag(
                            "error",
                            "orbit_pass.availability.clear_fraction",
                            f"orbit_pass.availability.clear_fraction must be within [0, 1], got {cf_f}.",
                            {"path": "orbit_pass.availability.clear_fraction", "value": cf_f},
                        )
                    )

    finite_key_cfg = config.get("finite_key")
    if finite_key_cfg is not None and not isinstance(finite_key_cfg, dict):
        errors.append(
            _diag(
                "error",
                "finite_key.block",
                "finite_key must be an object when provided.",
                {"path": "finite_key"},
            )
        )
        finite_key_cfg = {}
    elif not isinstance(finite_key_cfg, dict):
        finite_key_cfg = {}

    orbit_fk_cfg = orbit_pass.get("finite_key")
    if orbit_fk_cfg is not None and not isinstance(orbit_fk_cfg, dict):
        errors.append(
            _diag(
                "error",
                "orbit_pass.finite_key",
                "orbit_pass.finite_key must be an object when provided.",
                {"path": "orbit_pass.finite_key"},
            )
        )
        orbit_fk_cfg = {}
    elif not isinstance(orbit_fk_cfg, dict):
        orbit_fk_cfg = {}

    fk = dict(finite_key_cfg)
    fk.update(dict(orbit_fk_cfg))

    if not fk:
        warnings.append(
            _diag(
                "warning",
                "orbit_pass.finite_key.defaulted",
                "Finite-key pass budgeting settings are not provided explicitly; orbit defaults will be enforced.",
                {"path": "orbit_pass.finite_key"},
            )
        )

    fk_enabled = fk.get("enabled")
    if fk_enabled is not None and not isinstance(fk_enabled, bool):
        errors.append(
            _diag(
                "error",
                "orbit_pass.finite_key.enabled",
                "orbit_pass.finite_key.enabled must be boolean when provided.",
                {"path": "orbit_pass.finite_key.enabled"},
            )
        )
    elif fk_enabled is False:
        warnings.append(
            _diag(
                "warning",
                "orbit_pass.finite_key.enforced",
                "Finite-key enabled=false will be overridden by orbit-pass enforcement semantics.",
                {"path": "orbit_pass.finite_key.enabled", "value": False},
            )
        )

    _validate_positive_number(
        fk,
        "security_epsilon",
        errors,
        code="orbit_pass.finite_key.security_epsilon",
        path="orbit_pass.finite_key.security_epsilon",
        required=False,
    )
    _validate_unit_interval(
        fk,
        "parameter_estimation_fraction",
        errors,
        code="orbit_pass.finite_key.parameter_estimation_fraction",
        path="orbit_pass.finite_key.parameter_estimation_fraction",
    )
    if _is_number(fk.get("parameter_estimation_fraction")):
        pe = float(fk.get("parameter_estimation_fraction"))
        if pe > 0.9:
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.finite_key.parameter_estimation_fraction",
                    "orbit_pass.finite_key.parameter_estimation_fraction must be <= 0.9.",
                    {"path": "orbit_pass.finite_key.parameter_estimation_fraction", "value": pe},
                )
            )

    _validate_positive_number(
        fk,
        "pass_duty_cycle",
        errors,
        code="orbit_pass.finite_key.pass_duty_cycle",
        path="orbit_pass.finite_key.pass_duty_cycle",
        required=False,
    )
    if _is_number(fk.get("pass_duty_cycle")) and float(fk.get("pass_duty_cycle")) > 1.0:
        errors.append(
            _diag(
                "error",
                "orbit_pass.finite_key.pass_duty_cycle",
                "orbit_pass.finite_key.pass_duty_cycle must be within (0, 1].",
                {"path": "orbit_pass.finite_key.pass_duty_cycle", "value": float(fk.get("pass_duty_cycle"))},
            )
        )

    _validate_positive_number(
        fk,
        "detection_probability",
        errors,
        code="orbit_pass.finite_key.detection_probability",
        path="orbit_pass.finite_key.detection_probability",
        required=False,
    )
    if _is_number(fk.get("detection_probability")) and float(fk.get("detection_probability")) > 1.0:
        errors.append(
            _diag(
                "error",
                "orbit_pass.finite_key.detection_probability",
                "orbit_pass.finite_key.detection_probability must be within (0, 1].",
                {
                    "path": "orbit_pass.finite_key.detection_probability",
                    "value": float(fk.get("detection_probability")),
                },
            )
        )

    _validate_positive_number(
        fk,
        "signals_per_block",
        errors,
        code="orbit_pass.finite_key.signals_per_block",
        path="orbit_pass.finite_key.signals_per_block",
        required=False,
    )
    _validate_positive_number(
        fk,
        "max_signals_per_block",
        errors,
        code="orbit_pass.finite_key.max_signals_per_block",
        path="orbit_pass.finite_key.max_signals_per_block",
        required=False,
    )

    eps_keys = [
        "epsilon_correctness",
        "epsilon_secrecy",
        "epsilon_parameter_estimation",
        "epsilon_error_correction",
        "epsilon_privacy_amplification",
    ]
    eps_total = 0.0
    any_eps = False
    for key in eps_keys:
        _validate_positive_number(
            fk,
            key,
            errors,
            code=f"orbit_pass.finite_key.{key}",
            path=f"orbit_pass.finite_key.{key}",
            required=False,
        )
        if _is_number(fk.get(key)):
            any_eps = True
            eps_total += float(fk.get(key))
    if any_eps and _is_number(fk.get("security_epsilon")):
        sec = float(fk.get("security_epsilon"))
        if eps_total > sec:
            warnings.append(
                _diag(
                    "warning",
                    "orbit_pass.finite_key.epsilon_budget",
                    "Sum of epsilon budget fields is greater than security_epsilon; effective security epsilon may be increased.",
                    {
                        "path": "orbit_pass.finite_key",
                        "epsilon_total": eps_total,
                        "security_epsilon": sec,
                    },
                )
            )

    # Channel checks (free-space required).
    channel = config.get("channel")
    if not isinstance(channel, dict):
        errors.append(_diag("error", "channel.block", "channel block is required and must be an object.", {"path": "channel"}))
    else:
        model = str(channel.get("model", "")).strip().lower()
        if model != "free_space":
            errors.append(
                _diag(
                    "error",
                    "channel.model",
                    f"orbit_pass requires channel.model='free_space', got {model!r}.",
                    {"path": "channel.model", "model": model},
                )
            )
        _validate_nonneg_number(channel, "connector_loss_db", errors, code="channel.connector_loss_db", path="channel.connector_loss_db")
        _validate_positive_number(channel, "tx_aperture_m", errors, code="channel.tx_aperture_m", path="channel.tx_aperture_m")
        _validate_positive_number(channel, "rx_aperture_m", errors, code="channel.rx_aperture_m", path="channel.rx_aperture_m")
        _validate_optional_positive_number(
            channel, "beam_divergence_urad", errors, code="channel.beam_divergence_urad", path="channel.beam_divergence_urad"
        )
        _validate_nonneg_number(channel, "pointing_jitter_urad", errors, code="channel.pointing_jitter_urad", path="channel.pointing_jitter_urad")
        _validate_nonneg_number(
            channel,
            "atmospheric_extinction_db_per_km",
            errors,
            code="channel.atmospheric_extinction_db_per_km",
            path="channel.atmospheric_extinction_db_per_km",
        )
        _validate_nonneg_number(channel, "background_counts_cps", errors, code="channel.background_counts_cps", path="channel.background_counts_cps")

        channel_background_model = str(channel.get("background_model", background_model) or background_model).strip().lower()
        if channel_background_model not in {"fixed", "radiance_proxy"}:
            errors.append(
                _diag(
                    "error",
                    "channel.background_model",
                    "channel.background_model must be one of: fixed, radiance_proxy.",
                    {"path": "channel.background_model", "value": channel_background_model},
                )
            )
        channel_day_night = str(channel.get("background_day_night", "night") or "night").strip().lower()
        if channel_day_night not in {"day", "night"}:
            errors.append(
                _diag(
                    "error",
                    "channel.background_day_night",
                    "channel.background_day_night must be 'day' or 'night' when provided.",
                    {"path": "channel.background_day_night", "value": channel_day_night},
                )
            )

        if channel_background_model == "radiance_proxy":
            _validate_positive_number(
                channel,
                "background_fov_urad",
                errors,
                code="channel.background_fov_urad",
                path="channel.background_fov_urad",
                required=False,
            )
            _validate_positive_number(
                channel,
                "background_filter_bandwidth_nm",
                errors,
                code="channel.background_filter_bandwidth_nm",
                path="channel.background_filter_bandwidth_nm",
                required=False,
            )
            _validate_positive_number(
                channel,
                "background_detector_gate_ns",
                errors,
                code="channel.background_detector_gate_ns",
                path="channel.background_detector_gate_ns",
                required=False,
            )
            _validate_unit_interval(
                channel,
                "background_site_light_pollution",
                errors,
                code="channel.background_site_light_pollution",
                path="channel.background_site_light_pollution",
            )

            has_sample_day_night = any(
                isinstance(item, dict) and str(item.get("day_night", "")).strip().lower() in {"day", "night"}
                for item in (samples_cfg or [])
            )
            if channel_day_night not in {"day", "night"} and not has_sample_day_night:
                warnings.append(
                    _diag(
                        "warning",
                        "orbit_pass.sample.day_night",
                        "radiance_proxy background model is active but no explicit day/night context was provided; defaults may apply.",
                        {"path": "orbit_pass.samples[].day_night"},
                    )
                )

        path_model = str(channel.get("atmosphere_path_model", "effective_thickness") or "effective_thickness").strip().lower()
        if path_model not in {"effective_thickness", "slant_range", "legacy_slant_range"}:
            errors.append(
                _diag(
                    "error",
                    "channel.atmosphere_path_model",
                    "channel.atmosphere_path_model must be one of: effective_thickness, slant_range, legacy_slant_range.",
                    {"path": "channel.atmosphere_path_model", "value": path_model},
                )
            )
        _validate_positive_number(
            channel,
            "atmosphere_effective_thickness_km",
            errors,
            code="channel.atmosphere_effective_thickness_km",
            path="channel.atmosphere_effective_thickness_km",
            required=False,
        )

        pointing_model = str(channel.get("pointing_model", "deterministic") or "deterministic").strip().lower()
        if pointing_model not in {"deterministic", "none", "gaussian", "distribution"}:
            errors.append(
                _diag(
                    "error",
                    "channel.pointing_model",
                    "channel.pointing_model must be one of: deterministic, gaussian, distribution.",
                    {"path": "channel.pointing_model", "value": pointing_model},
                )
            )

        turbulence_model = str(channel.get("turbulence_model", "deterministic") or "deterministic").strip().lower()
        if turbulence_model not in {"deterministic", "none", "lognormal", "gamma_gamma", "gammagamma"}:
            errors.append(
                _diag(
                    "error",
                    "channel.turbulence_model",
                    "channel.turbulence_model must be one of: deterministic, lognormal, gamma_gamma.",
                    {"path": "channel.turbulence_model", "value": turbulence_model},
                )
            )

        tsi = channel.get("turbulence_scintillation_index")
        if tsi is not None:
            if not _is_number(tsi):
                errors.append(
                    _diag(
                        "error",
                        "channel.turbulence_scintillation_index",
                        f"channel.turbulence_scintillation_index must be a number, got {type(tsi).__name__}.",
                        {"path": "channel.turbulence_scintillation_index"},
                    )
                )
            else:
                tsi_f = float(tsi)
                if tsi_f < 0.0:
                    errors.append(
                        _diag(
                            "error",
                            "channel.turbulence_scintillation_index",
                            f"channel.turbulence_scintillation_index must be >= 0, got {tsi_f}.",
                            {"path": "channel.turbulence_scintillation_index", "value": tsi_f},
                        )
                    )
                elif tsi_f > 1.0:
                    warnings.append(
                        _diag(
                            "warning",
                            "channel.turbulence_scintillation_index",
                            f"channel.turbulence_scintillation_index is > 1 ({tsi_f}). Ensure this is intended.",
                            {"path": "channel.turbulence_scintillation_index", "value": tsi_f},
                        )
                    )

        mode = str(orbit_pass.get("execution_mode", "preview") or "preview").strip().lower()
        if mode == "certification":
            if turbulence_model in {"deterministic", "none"}:
                warnings.append(
                    _diag(
                        "warning",
                        "channel.turbulence_model",
                        "certification mode with deterministic turbulence_model may understate outage risk.",
                        {"path": "channel.turbulence_model", "value": turbulence_model},
                    )
                )
            if pointing_model in {"deterministic", "none"}:
                warnings.append(
                    _diag(
                        "warning",
                        "channel.pointing_model",
                        "certification mode with deterministic pointing_model may understate tracking outage risk.",
                        {"path": "channel.pointing_model", "value": pointing_model},
                    )
                )

    # Source checks (type required; ranges are best-effort).
    source = config.get("source")
    if not isinstance(source, dict):
        errors.append(_diag("error", "source.block", "source block is required and must be an object.", {"path": "source"}))
    else:
        st = str(source.get("type", "")).strip()
        if not st:
            errors.append(_diag("error", "source.type", "source.type is required.", {"path": "source.type"}))
        elif st not in {"emitter_cavity", "spdc"}:
            errors.append(
                _diag(
                    "error",
                    "source.type",
                    f"Unknown source.type {st!r}. Expected 'emitter_cavity' or 'spdc'.",
                    {"path": "source.type", "type": st},
                )
            )
        _validate_positive_number(
            source, "rep_rate_mhz", errors, code="source.rep_rate_mhz", path="source.rep_rate_mhz", required=False
        )
        _validate_unit_interval(
            source,
            "collection_efficiency",
            errors,
            code="source.collection_efficiency",
            path="source.collection_efficiency",
        )
        _validate_unit_interval(
            source,
            "coupling_efficiency",
            errors,
            code="source.coupling_efficiency",
            path="source.coupling_efficiency",
        )
        _validate_unit_interval(source, "g2_0", errors, code="source.g2_0", path="source.g2_0")

    # Detector checks (class required; ranges are best-effort).
    detector = config.get("detector")
    if not isinstance(detector, dict):
        errors.append(_diag("error", "detector.block", "detector block is required and must be an object.", {"path": "detector"}))
    else:
        cls = str(detector.get("class", "")).strip()
        if not cls:
            errors.append(_diag("error", "detector.class", "detector.class is required.", {"path": "detector.class"}))
        elif cls not in DETECTOR_PRESETS:
            errors.append(
                _diag(
                    "error",
                    "detector.class",
                    f"Unknown detector.class {cls!r}. Expected one of {sorted(DETECTOR_PRESETS.keys())}.",
                    {"path": "detector.class", "class": cls},
                )
            )
        _validate_unit_interval(detector, "pde", errors, code="detector.pde", path="detector.pde")
        _validate_nonneg_number(detector, "dark_counts_cps", errors, code="detector.dark_counts_cps", path="detector.dark_counts_cps")
        _validate_positive_number(
            detector, "jitter_ps_fwhm", errors, code="detector.jitter_ps_fwhm", path="detector.jitter_ps_fwhm", required=False
        )
        _validate_nonneg_number(detector, "dead_time_ns", errors, code="detector.dead_time_ns", path="detector.dead_time_ns")
        _validate_unit_interval(
            detector,
            "afterpulsing_prob",
            errors,
            code="detector.afterpulsing_prob",
            path="detector.afterpulsing_prob",
        )

    # Timing checks (optional block).
    timing = config.get("timing")
    if timing is not None and not isinstance(timing, dict):
        errors.append(_diag("error", "timing.block", "timing must be an object if provided.", {"path": "timing"}))
    elif isinstance(timing, dict):
        _validate_nonneg_number(timing, "sync_drift_ps_rms", errors, code="timing.sync_drift_ps_rms", path="timing.sync_drift_ps_rms")
        _validate_positive_number(
            timing,
            "coincidence_window_ps",
            errors,
            code="timing.coincidence_window_ps",
            path="timing.coincidence_window_ps",
            required=False,
        )

    # Protocol checks (optional; name is advisory only for v0.1 orbit pass).
    protocol = config.get("protocol")
    if protocol is not None and not isinstance(protocol, dict):
        errors.append(_diag("error", "protocol.block", "protocol must be an object if provided.", {"path": "protocol"}))
    elif isinstance(protocol, dict):
        if "name" not in protocol:
            warnings.append(
                _diag(
                    "warning",
                    "protocol.name",
                    "protocol.name is not set. This is allowed for OrbitVerify v0.1 but reduces provenance clarity.",
                    {"path": "protocol.name"},
                )
            )

    # Cases (optional).
    cases_cfg = orbit_pass.get("cases")
    if cases_cfg is not None:
        if not isinstance(cases_cfg, list):
            errors.append(
                _diag(
                    "error",
                    "orbit_pass.cases",
                    "orbit_pass.cases must be a list of objects when provided.",
                    {"path": "orbit_pass.cases"},
                )
            )
        else:
            seen: set[str] = set()
            for idx, case in enumerate(cases_cfg):
                cpath = f"orbit_pass.cases[{idx}]"
                if not isinstance(case, dict):
                    errors.append(_diag("error", "orbit_pass.case.type", "Each case must be an object.", {"path": cpath}))
                    continue
                cid = str(case.get("id", "")).strip()
                if not cid:
                    errors.append(_diag("error", "orbit_pass.case.id", "orbit_pass.cases[].id is required.", {"path": f"{cpath}.id"}))
                elif cid in seen:
                    errors.append(
                        _diag(
                            "error",
                            "orbit_pass.case.duplicate_id",
                            f"Duplicate orbit_pass.cases[].id {cid!r}.",
                            {"path": f"{cpath}.id", "case_id": cid},
                        )
                    )
                else:
                    seen.add(cid)

                overrides = case.get("channel_overrides")
                if overrides is not None and not isinstance(overrides, dict):
                    errors.append(
                        _diag(
                            "error",
                            "orbit_pass.case.channel_overrides",
                            "channel_overrides must be an object when provided.",
                            {"path": f"{cpath}.channel_overrides"},
                        )
                    )
                elif isinstance(overrides, dict):
                    _validate_nonneg_number(
                        overrides,
                        "atmospheric_extinction_db_per_km",
                        errors,
                        code="orbit_pass.case.atmospheric_extinction_db_per_km",
                        path=f"{cpath}.channel_overrides.atmospheric_extinction_db_per_km",
                    )
                    _validate_nonneg_number(
                        overrides,
                        "pointing_jitter_urad",
                        errors,
                        code="orbit_pass.case.pointing_jitter_urad",
                        path=f"{cpath}.channel_overrides.pointing_jitter_urad",
                    )
                    _validate_nonneg_number(
                        overrides,
                        "turbulence_scintillation_index",
                        errors,
                        code="orbit_pass.case.turbulence_scintillation_index",
                        path=f"{cpath}.channel_overrides.turbulence_scintillation_index",
                    )
                    _validate_positive_number(
                        overrides,
                        "background_counts_cps_scale",
                        errors,
                        code="orbit_pass.case.background_counts_cps_scale",
                        path=f"{cpath}.channel_overrides.background_counts_cps_scale",
                        required=False,
                    )

    return _finalize(errors, warnings)


def _validate_nonneg_number(obj: dict, key: str, errors: list[Diagnostic], *, code: str, path: str, required: bool = False) -> None:
    if key not in obj:
        if required:
            errors.append(_diag("error", code, f"{path} is required.", {"path": path}))
        return
    v = obj.get(key)
    if v is None:
        return
    if not _is_number(v):
        errors.append(_diag("error", code, f"{path} must be a number, got {type(v).__name__}.", {"path": path}))
        return
    if float(v) < 0.0:
        errors.append(_diag("error", code, f"{path} must be >= 0, got {v}.", {"path": path, "value": float(v)}))


def _validate_positive_number(obj: dict, key: str, errors: list[Diagnostic], *, code: str, path: str, required: bool = False) -> None:
    if key not in obj:
        if required:
            errors.append(_diag("error", code, f"{path} is required.", {"path": path}))
        return
    v = obj.get(key)
    if v is None:
        return
    if not _is_number(v):
        errors.append(_diag("error", code, f"{path} must be a number, got {type(v).__name__}.", {"path": path}))
        return
    if float(v) <= 0.0:
        errors.append(_diag("error", code, f"{path} must be > 0, got {v}.", {"path": path, "value": float(v)}))


def _validate_optional_positive_number(
    obj: dict,
    key: str,
    errors: list[Diagnostic],
    *,
    code: str,
    path: str,
) -> None:
    if key not in obj:
        return
    v = obj.get(key)
    if v is None:
        return
    _validate_positive_number(obj, key, errors, code=code, path=path, required=False)


def _validate_unit_interval(obj: dict, key: str, errors: list[Diagnostic], *, code: str, path: str) -> None:
    if key not in obj:
        return
    v = obj.get(key)
    if v is None:
        return
    if not _is_number(v):
        errors.append(_diag("error", code, f"{path} must be a number, got {type(v).__name__}.", {"path": path}))
        return
    f = float(v)
    if f < 0.0 or f > 1.0:
        errors.append(_diag("error", code, f"{path} must be within [0, 1], got {v}.", {"path": path, "value": f}))


def _finalize(errors: list[Diagnostic], warnings: list[Diagnostic]) -> dict[str, Any]:
    def sort_key(d: Diagnostic) -> tuple:
        ref = d.ref or {}
        return (
            str(d.level),
            str(d.code),
            str(ref.get("path", "")),
            str(ref.get("case_id", "")),
            str(ref.get("band", "")),
            str(d.message),
        )

    errors.sort(key=sort_key)
    warnings.sort(key=sort_key)
    return {
        "domain": "orbit_pass_envelope",
        "errors": [d.__dict__ for d in errors],
        "warnings": [d.__dict__ for d in warnings],
        "summary": {"error_count": len(errors), "warning_count": len(warnings)},
    }
