"""Free-space and satellite-oriented channel models."""

from __future__ import annotations

import math
import warnings

import numpy as np


def total_free_space_efficiency(
    distance_km: float,
    wavelength_nm: float,
    channel_cfg: dict,
) -> dict[str, object]:
    """Compute free-space channel efficiency with diagnostic decomposition."""
    distance_km = max(0.0, float(distance_km))
    wavelength_nm = max(1.0, float(wavelength_nm))
    tx_aperture_m = max(1e-6, float(channel_cfg.get("tx_aperture_m", 0.12)))
    rx_aperture_m = max(1e-6, float(channel_cfg.get("rx_aperture_m", 0.30)))
    elevation_deg = float(channel_cfg.get("elevation_deg", 45.0))
    extinction_db_per_km = max(
        0.0, float(channel_cfg.get("atmospheric_extinction_db_per_km", 0.02))
    )
    atmosphere_effective_thickness_km = max(
        1e-6, float(channel_cfg.get("atmosphere_effective_thickness_km", 20.0) or 20.0)
    )
    atmosphere_path_model = str(channel_cfg.get("atmosphere_path_model", "effective_thickness") or "effective_thickness").strip().lower()
    pointing_jitter_urad = max(0.0, float(channel_cfg.get("pointing_jitter_urad", 1.5)))
    turbulence_scintillation_index = max(
        0.0, float(channel_cfg.get("turbulence_scintillation_index", 0.15))
    )
    connector_loss_db = max(0.0, float(channel_cfg.get("connector_loss_db", 1.0)))

    beam_divergence_urad = channel_cfg.get("beam_divergence_urad")
    if beam_divergence_urad is None:
        # Diffraction-limited half-angle proxy.
        wavelength_m = wavelength_nm * 1e-9
        beam_divergence_rad = 1.22 * wavelength_m / tx_aperture_m
        beam_divergence_urad = max(beam_divergence_rad * 1e6, 1e-6)
    else:
        beam_divergence_urad = max(1e-6, float(beam_divergence_urad))

    eta_geom = geometric_efficiency(
        distance_km=distance_km,
        rx_aperture_m=rx_aperture_m,
        beam_divergence_urad=beam_divergence_urad,
    )

    atmosphere_path_km, airmass = atmospheric_path_length_km(
        distance_km=distance_km,
        elevation_deg=elevation_deg,
        atmosphere_effective_thickness_km=atmosphere_effective_thickness_km,
        path_model=atmosphere_path_model,
    )

    eta_atm, airmass = atmospheric_transmission(
        distance_km=distance_km,
        elevation_deg=elevation_deg,
        extinction_db_per_km=extinction_db_per_km,
        atmosphere_effective_thickness_km=atmosphere_effective_thickness_km,
        path_model=atmosphere_path_model,
    )

    pointing_diag = pointing_diagnostics(
        pointing_jitter_urad=pointing_jitter_urad,
        beam_divergence_urad=beam_divergence_urad,
        model=str(channel_cfg.get("pointing_model", "deterministic") or "deterministic"),
        sample_count=int(channel_cfg.get("pointing_sample_count", 256) or 256),
        seed=channel_cfg.get("pointing_seed"),
        bias_urad=float(channel_cfg.get("pointing_bias_urad", 0.0) or 0.0),
        outage_threshold_eta=float(channel_cfg.get("pointing_outage_threshold_eta", 0.1) or 0.1),
    )

    turbulence_diag = turbulence_diagnostics(
        scintillation_index=turbulence_scintillation_index,
        model=str(channel_cfg.get("turbulence_model", "deterministic") or "deterministic"),
        sample_count=int(channel_cfg.get("turbulence_sample_count", 256) or 256),
        seed=channel_cfg.get("turbulence_seed"),
        outage_threshold_eta=float(channel_cfg.get("turbulence_outage_threshold_eta", 0.1) or 0.1),
    )

    eta_point = float(pointing_diag["eta_expected"])
    eta_turb = float(turbulence_diag["eta_expected"])

    eta_conn = 10 ** (-connector_loss_db / 10.0)
    eta_total = _clamp(eta_geom * eta_atm * eta_point * eta_turb * eta_conn, 0.0, 1.0)
    total_loss_db = _linear_to_db_loss(eta_total)

    eta_threshold = _clamp(float(channel_cfg.get("outage_eta_threshold", 1e-6) or 1e-6), 0.0, 1.0)
    outage_prob = _combined_outage_probability(
        eta_geom=eta_geom,
        eta_atm=eta_atm,
        eta_conn=eta_conn,
        eta_threshold=eta_threshold,
        point_samples=pointing_diag.get("samples"),
        turb_samples=turbulence_diag.get("samples"),
        eta_point=eta_point,
        eta_turb=eta_turb,
    )
    atmospheric_loss_db = max(0.0, float(extinction_db_per_km) * float(atmosphere_path_km))
    background_diag = resolve_background_counts(channel_cfg)

    return {
        "eta_channel": eta_total,
        "total_loss_db": total_loss_db,
        "eta_geometric": eta_geom,
        "eta_atmospheric": eta_atm,
        "eta_pointing": eta_point,
        "eta_turbulence": eta_turb,
        "eta_connector": eta_conn,
        "airmass": airmass,
        "atmosphere_path_model": atmosphere_path_model,
        "atmosphere_effective_thickness_km": atmosphere_effective_thickness_km,
        "atmosphere_path_km": float(atmosphere_path_km),
        "atmospheric_loss_db": float(atmospheric_loss_db),
        "beam_divergence_urad": beam_divergence_urad,
        "pointing_diagnostics": {
            key: value
            for key, value in pointing_diag.items()
            if key != "samples"
        },
        "turbulence_diagnostics": {
            key: value
            for key, value in turbulence_diag.items()
            if key != "samples"
        },
        "outage_threshold_eta": float(eta_threshold),
        "outage_probability": float(outage_prob),
        "background_counts_cps": float(background_diag["background_counts_cps"]),
        "background_model": str(background_diag["background_model"]),
        "background_day_night": str(background_diag["day_night"]),
        "background_uncertainty_cps": dict(background_diag["uncertainty_cps"]),
    }


def resolve_background_counts(channel_cfg: dict) -> dict:
    model = str(channel_cfg.get("background_model", "fixed") or "fixed").strip().lower()
    scale = max(0.0, float(channel_cfg.get("background_counts_cps_scale", 1.0) or 1.0))

    if model == "fixed":
        counts = max(0.0, float(channel_cfg.get("background_counts_cps", 0.0) or 0.0)) * scale
        rel_unc = _clamp(float(channel_cfg.get("background_uncertainty_rel", 0.05) or 0.05), 0.0, 1.0)
        sigma = counts * rel_unc
        return {
            "background_counts_cps": float(counts),
            "background_model": "fixed",
            "day_night": _normalize_day_night(channel_cfg.get("background_day_night", "night")),
            "uncertainty_cps": {
                "low": float(max(0.0, counts - sigma)),
                "high": float(counts + sigma),
                "sigma": float(sigma),
                "relative": float(rel_unc),
            },
        }

    if model != "radiance_proxy":
        raise ValueError(f"Unsupported background_model: {model!r}")

    day_night = _normalize_day_night(channel_cfg.get("background_day_night", "night"))
    fov_urad = max(1e-6, float(channel_cfg.get("background_fov_urad", 100.0) or 100.0))
    filter_bandwidth_nm = max(1e-6, float(channel_cfg.get("background_filter_bandwidth_nm", 1.0) or 1.0))
    detector_gate_ns = max(1e-6, float(channel_cfg.get("background_detector_gate_ns", 1.0) or 1.0))
    site_light_pollution = _clamp(float(channel_cfg.get("background_site_light_pollution", 0.2) or 0.2), 0.0, 1.0)
    base_night_cps = max(1e-9, float(channel_cfg.get("background_base_night_cps", 250.0) or 250.0))
    day_factor = max(1.0, float(channel_cfg.get("background_day_factor", 9.0) or 9.0))

    regime_factor = day_factor if day_night == "day" else 1.0
    optics_scale = (fov_urad / 100.0) * (filter_bandwidth_nm / 1.0) * (detector_gate_ns / 1.0)
    pollution_scale = 1.0 + 2.0 * site_light_pollution
    counts = max(0.0, base_night_cps * regime_factor * optics_scale * pollution_scale * scale)

    rel_unc = _clamp(0.15 + 0.15 * (1.0 if day_night == "day" else 0.0) + 0.10 * site_light_pollution, 0.05, 0.60)
    sigma = counts * rel_unc
    return {
        "background_counts_cps": float(counts),
        "background_model": "radiance_proxy",
        "day_night": day_night,
        "uncertainty_cps": {
            "low": float(max(0.0, counts - sigma)),
            "high": float(counts + sigma),
            "sigma": float(sigma),
            "relative": float(rel_unc),
        },
    }


def geometric_efficiency(
    distance_km: float,
    rx_aperture_m: float,
    beam_divergence_urad: float,
) -> float:
    distance_m = max(0.0, float(distance_km)) * 1000.0
    rx_aperture_m = max(1e-6, float(rx_aperture_m))
    beam_divergence_rad = max(1e-12, float(beam_divergence_urad) * 1e-6)

    if distance_m <= 0:
        return 1.0

    beam_radius_m = max(1e-9, 0.5 * beam_divergence_rad * distance_m)
    beam_area = math.pi * beam_radius_m * beam_radius_m
    rx_area = math.pi * (0.5 * rx_aperture_m) ** 2
    return _clamp(rx_area / beam_area, 0.0, 1.0)


def atmospheric_transmission(
    distance_km: float,
    elevation_deg: float,
    extinction_db_per_km: float,
    *,
    atmosphere_effective_thickness_km: float = 20.0,
    path_model: str = "effective_thickness",
) -> tuple[float, float]:
    elevation_deg = _clamp(float(elevation_deg), 0.0, 90.0)
    if elevation_deg < 5.0:
        warnings.warn(
            f"Elevation {elevation_deg:.2f} deg is below 5 deg. Atmospheric loss estimates "
            "are highly sensitive at low elevations; ensure this is intended.",
            stacklevel=2,
        )

    atmosphere_path_km, airmass = atmospheric_path_length_km(
        distance_km=distance_km,
        elevation_deg=elevation_deg,
        atmosphere_effective_thickness_km=atmosphere_effective_thickness_km,
        path_model=path_model,
    )
    effective_loss_db = max(0.0, float(extinction_db_per_km)) * max(0.0, float(atmosphere_path_km))
    return 10 ** (-effective_loss_db / 10.0), airmass


def atmospheric_path_length_km(
    *,
    distance_km: float,
    elevation_deg: float,
    atmosphere_effective_thickness_km: float,
    path_model: str = "effective_thickness",
) -> tuple[float, float]:
    elevation_deg = _clamp(float(elevation_deg), 0.0, 90.0)
    airmass = max(1.0, _kasten_young_airmass(elevation_deg))
    model = str(path_model or "effective_thickness").strip().lower()
    if model in {"slant_range", "legacy_slant_range"}:
        return max(0.0, float(distance_km)) * airmass, airmass
    thickness_km = max(1e-6, float(atmosphere_effective_thickness_km))
    return thickness_km * airmass, airmass


def pointing_efficiency(pointing_jitter_urad: float, beam_divergence_urad: float) -> float:
    sigma = max(0.0, float(pointing_jitter_urad))
    theta = max(1e-6, float(beam_divergence_urad))
    return _clamp(math.exp(-((sigma / theta) ** 2)), 0.0, 1.0)


def turbulence_efficiency(scintillation_index: float) -> float:
    return _clamp(math.exp(-max(0.0, float(scintillation_index))), 0.0, 1.0)


def turbulence_diagnostics(
    *,
    scintillation_index: float,
    model: str = "deterministic",
    sample_count: int = 256,
    seed: int | None = None,
    outage_threshold_eta: float = 0.1,
) -> dict:
    scint = max(0.0, float(scintillation_index))
    base_eta = turbulence_efficiency(scint)
    threshold = _clamp(float(outage_threshold_eta), 0.0, 1.0)
    name = str(model or "deterministic").strip().lower()
    if name in {"deterministic", "none"}:
        return {
            "model": "deterministic",
            "regime": _scintillation_regime(scint),
            "eta_expected": float(base_eta),
            "outage_probability": float(1.0 if base_eta < threshold else 0.0),
            "sample_count": 0,
            "seed": None,
            "samples": None,
        }

    n = max(16, int(sample_count))
    rng = np.random.default_rng(None if seed is None else int(seed))

    if name == "lognormal":
        sigma_ln = math.sqrt(math.log1p(scint)) if scint > 0.0 else 0.0
        mu_ln = -0.5 * sigma_ln * sigma_ln
        fade = rng.lognormal(mean=mu_ln, sigma=sigma_ln, size=n)
    elif name in {"gamma_gamma", "gammagamma"}:
        alpha = max(1e-3, 1.0 / max(1e-3, scint))
        beta = max(1e-3, 1.0 / max(1e-3, 0.75 * scint + 0.05))
        x = rng.gamma(shape=alpha, scale=1.0 / alpha, size=n)
        y = rng.gamma(shape=beta, scale=1.0 / beta, size=n)
        fade = x * y
    else:
        raise ValueError(f"Unsupported turbulence_model: {model!r}")

    eta_samples = np.clip(base_eta * fade, 0.0, 1.0)
    outage = float(np.mean(eta_samples < threshold))
    return {
        "model": name,
        "regime": _scintillation_regime(scint),
        "eta_expected": float(np.mean(eta_samples)),
        "outage_probability": outage,
        "sample_count": int(n),
        "seed": int(seed) if seed is not None else None,
        "samples": eta_samples,
    }


def pointing_diagnostics(
    *,
    pointing_jitter_urad: float,
    beam_divergence_urad: float,
    model: str = "deterministic",
    sample_count: int = 256,
    seed: int | None = None,
    bias_urad: float = 0.0,
    outage_threshold_eta: float = 0.1,
) -> dict:
    sigma = max(0.0, float(pointing_jitter_urad))
    theta = max(1e-6, float(beam_divergence_urad))
    threshold = _clamp(float(outage_threshold_eta), 0.0, 1.0)
    name = str(model or "deterministic").strip().lower()

    if name in {"deterministic", "none"}:
        eta = pointing_efficiency(pointing_jitter_urad=sigma, beam_divergence_urad=theta)
        return {
            "model": "deterministic",
            "eta_expected": float(eta),
            "outage_probability": float(1.0 if eta < threshold else 0.0),
            "sample_count": 0,
            "seed": None,
            "bias_urad": float(max(0.0, bias_urad)),
            "samples": None,
        }

    if name not in {"gaussian", "distribution"}:
        raise ValueError(f"Unsupported pointing_model: {model!r}")

    n = max(16, int(sample_count))
    rng = np.random.default_rng(None if seed is None else int(seed))
    bx = max(0.0, float(bias_urad))
    x = rng.normal(loc=bx, scale=sigma, size=n)
    y = rng.normal(loc=0.0, scale=sigma, size=n)
    radial = np.sqrt(x * x + y * y)
    eta_samples = np.clip(np.exp(-((radial / theta) ** 2)), 0.0, 1.0)
    outage = float(np.mean(eta_samples < threshold))
    return {
        "model": name,
        "eta_expected": float(np.mean(eta_samples)),
        "outage_probability": outage,
        "sample_count": int(n),
        "seed": int(seed) if seed is not None else None,
        "bias_urad": float(bx),
        "samples": eta_samples,
    }


def _combined_outage_probability(
    *,
    eta_geom: float,
    eta_atm: float,
    eta_conn: float,
    eta_threshold: float,
    point_samples,
    turb_samples,
    eta_point: float,
    eta_turb: float,
) -> float:
    if point_samples is None and turb_samples is None:
        eta_channel = _clamp(float(eta_geom) * float(eta_atm) * float(eta_conn) * float(eta_point) * float(eta_turb), 0.0, 1.0)
        return float(1.0 if eta_channel < eta_threshold else 0.0)

    if point_samples is None:
        p = np.full_like(turb_samples, float(eta_point), dtype=float)
    else:
        p = np.asarray(point_samples, dtype=float)
    if turb_samples is None:
        t = np.full_like(p, float(eta_turb), dtype=float)
    else:
        t = np.asarray(turb_samples, dtype=float)
        if t.shape[0] != p.shape[0]:
            n = min(int(p.shape[0]), int(t.shape[0]))
            p = p[:n]
            t = t[:n]

    eta_samples = np.clip(float(eta_geom) * float(eta_atm) * float(eta_conn) * p * t, 0.0, 1.0)
    return float(np.mean(eta_samples < float(eta_threshold)))


def _normalize_day_night(value) -> str:
    text = str(value or "night").strip().lower()
    if text in {"day", "night"}:
        return text
    return "night"


def _scintillation_regime(scintillation_index: float) -> str:
    s = max(0.0, float(scintillation_index))
    if s < 0.1:
        return "weak"
    if s < 0.3:
        return "moderate"
    return "strong"


def _kasten_young_airmass(elevation_deg: float) -> float:
    """Optical airmass via Kasten & Young (1989).

    This approximation remains finite near the horizon and is commonly used in
    link-budget calculations when a full atmospheric radiative transfer model is
    not warranted.
    """

    h = _clamp(float(elevation_deg), 0.0, 90.0)
    sin_h = math.sin(math.radians(h))
    denom = sin_h + 0.50572 * (h + 6.07995) ** -1.6364
    return 1.0 / max(1e-6, denom)


def _linear_to_db_loss(eta: float) -> float:
    eta = max(float(eta), 1e-15)
    return -10.0 * math.log10(eta)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(float(value), hi))
