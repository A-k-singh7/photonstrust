"""Unified channel engine for fiber, free-space, and satellite links."""

from __future__ import annotations

import math
from typing import Any

from photonstrust.channels.coexistence import compute_raman_counts_cps
from photonstrust.channels.fiber import apply_fiber_loss, polarization_drift
from photonstrust.channels.free_space import total_free_space_efficiency
from photonstrust.utils import clamp


def compute_channel_diagnostics(
    *,
    distance_km: float,
    wavelength_nm: float,
    channel_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Compute channel efficiency/loss with decomposition across supported models."""

    distance_km = max(0.0, float(distance_km))
    wavelength_nm = max(1.0, float(wavelength_nm))
    channel_cfg = dict(channel_cfg or {})
    model = str(channel_cfg.get("model", "fiber")).strip().lower()

    if model == "free_space":
        return _free_space_diag(distance_km=distance_km, wavelength_nm=wavelength_nm, channel_cfg=channel_cfg)
    if model == "satellite":
        return _satellite_diag(distance_km=distance_km, wavelength_nm=wavelength_nm, channel_cfg=channel_cfg)
    return _fiber_diag(distance_km=distance_km, channel_cfg=channel_cfg)


def _fiber_diag(*, distance_km: float, channel_cfg: dict[str, Any]) -> dict[str, Any]:
    alpha_db_per_km = max(0.0, float(channel_cfg.get("fiber_loss_db_per_km", 0.0) or 0.0))
    connector_loss_db = max(0.0, float(channel_cfg.get("connector_loss_db", 0.0) or 0.0))

    eta_fiber = apply_fiber_loss(distance_km, alpha_db_per_km)
    eta_connector = 10 ** (-connector_loss_db / 10.0)

    coherence_length = channel_cfg.get("polarization_coherence_length_km")
    if coherence_length is None:
        eta_polarization = 1.0
    else:
        eta_polarization = polarization_drift(distance_km, float(coherence_length))

    # Polarization decoherence is modeled as a visibility/QBER penalty in the
    # protocol layers, not as optical attenuation in the channel loss budget.
    eta_channel = clamp(float(eta_fiber * eta_connector), 0.0, 1.0)
    total_loss_db = _linear_to_db_loss(eta_channel)

    background_counts_cps = max(0.0, float(channel_cfg.get("background_counts_cps", 0.0) or 0.0))
    raman_counts_cps = max(
        0.0,
        float(
            compute_raman_counts_cps(
                distance_km,
                channel_cfg.get("coexistence"),
                fiber_loss_db_per_km=alpha_db_per_km,
            )
        ),
    )

    return {
        "model": "fiber",
        "eta_channel": float(eta_channel),
        "total_loss_db": float(total_loss_db),
        "background_counts_cps": float(background_counts_cps),
        "raman_counts_cps": float(raman_counts_cps),
        "decomposition": {
            "eta_fiber": float(clamp(eta_fiber, 0.0, 1.0)),
            "eta_connector": float(clamp(eta_connector, 0.0, 1.0)),
            "eta_polarization": float(clamp(eta_polarization, 0.0, 1.0)),
        },
    }


def _free_space_diag(*, distance_km: float, wavelength_nm: float, channel_cfg: dict[str, Any]) -> dict[str, Any]:
    fs = total_free_space_efficiency(distance_km=distance_km, wavelength_nm=wavelength_nm, channel_cfg=channel_cfg)
    return {
        "model": "free_space",
        "eta_channel": float(fs["eta_channel"]),
        "total_loss_db": float(fs["total_loss_db"]),
        "background_counts_cps": float(fs.get("background_counts_cps", 0.0) or 0.0),
        "background_model": str(fs.get("background_model", "fixed") or "fixed"),
        "background_day_night": str(fs.get("background_day_night", "night") or "night"),
        "background_uncertainty_cps": dict(fs.get("background_uncertainty_cps", {}) or {}),
        "raman_counts_cps": 0.0,
        "outage_probability": float(fs.get("outage_probability", 0.0) or 0.0),
        "outage_threshold_eta": float(fs.get("outage_threshold_eta", 0.0) or 0.0),
        "decomposition": {
            "eta_geometric": float(fs.get("eta_geometric", 1.0) or 1.0),
            "eta_atmospheric": float(fs.get("eta_atmospheric", 1.0) or 1.0),
            "eta_pointing": float(fs.get("eta_pointing", 1.0) or 1.0),
            "eta_turbulence": float(fs.get("eta_turbulence", 1.0) or 1.0),
            "eta_connector": float(fs.get("eta_connector", 1.0) or 1.0),
            "airmass": float(fs.get("airmass", 1.0) or 1.0),
            "atmosphere_path_km": float(fs.get("atmosphere_path_km", 0.0) or 0.0),
            "atmosphere_effective_thickness_km": float(fs.get("atmosphere_effective_thickness_km", 0.0) or 0.0),
            "atmosphere_path_model": str(fs.get("atmosphere_path_model", "effective_thickness") or "effective_thickness"),
            "atmospheric_loss_db": float(fs.get("atmospheric_loss_db", 0.0) or 0.0),
            "background_model": str(fs.get("background_model", "fixed") or "fixed"),
            "background_day_night": str(fs.get("background_day_night", "night") or "night"),
            "background_uncertainty_cps": dict(fs.get("background_uncertainty_cps", {}) or {}),
            "pointing_diagnostics": fs.get("pointing_diagnostics", {}),
            "turbulence_diagnostics": fs.get("turbulence_diagnostics", {}),
        },
    }


def _satellite_diag(*, distance_km: float, wavelength_nm: float, channel_cfg: dict[str, Any]) -> dict[str, Any]:
    split = float(channel_cfg.get("satellite_uplink_fraction", 0.5) or 0.5)
    split = clamp(split, 0.0, 1.0)

    d_up = distance_km * split
    d_down = max(0.0, distance_km - d_up)

    cfg_up = dict(channel_cfg)
    cfg_dn = dict(channel_cfg)
    cfg_up["connector_loss_db"] = 0.0
    cfg_dn["connector_loss_db"] = 0.0
    if "uplink_elevation_deg" in channel_cfg:
        cfg_up["elevation_deg"] = channel_cfg["uplink_elevation_deg"]
    if "downlink_elevation_deg" in channel_cfg:
        cfg_dn["elevation_deg"] = channel_cfg["downlink_elevation_deg"]

    up = total_free_space_efficiency(distance_km=d_up, wavelength_nm=wavelength_nm, channel_cfg=cfg_up)
    dn = total_free_space_efficiency(distance_km=d_down, wavelength_nm=wavelength_nm, channel_cfg=cfg_dn)

    eta_connector = 10 ** (-max(0.0, float(channel_cfg.get("connector_loss_db", 0.0) or 0.0)) / 10.0)
    eta_channel = clamp(float(up["eta_channel"] * dn["eta_channel"] * eta_connector), 0.0, 1.0)

    bg_up = float(up.get("background_counts_cps", 0.0) or 0.0)
    bg_dn = float(dn.get("background_counts_cps", 0.0) or 0.0)
    bg_ref = up if bg_up >= bg_dn else dn

    return {
        "model": "satellite",
        "eta_channel": float(eta_channel),
        "total_loss_db": float(_linear_to_db_loss(eta_channel)),
        "background_counts_cps": float(max(bg_up, bg_dn)),
        "background_model": str(bg_ref.get("background_model", "fixed") or "fixed"),
        "background_day_night": str(bg_ref.get("background_day_night", "night") or "night"),
        "background_uncertainty_cps": dict(bg_ref.get("background_uncertainty_cps", {}) or {}),
        "raman_counts_cps": 0.0,
        "outage_probability": float(max(float(up.get("outage_probability", 0.0) or 0.0), float(dn.get("outage_probability", 0.0) or 0.0))),
        "outage_threshold_eta": float(channel_cfg.get("outage_eta_threshold", 1e-6) or 1e-6),
        "decomposition": {
            "eta_uplink": float(clamp(up["eta_channel"], 0.0, 1.0)),
            "eta_downlink": float(clamp(dn["eta_channel"], 0.0, 1.0)),
            "eta_connector": float(clamp(eta_connector, 0.0, 1.0)),
            "eta_uplink_pointing": float(clamp(up.get("eta_pointing", 1.0), 0.0, 1.0)),
            "eta_downlink_pointing": float(clamp(dn.get("eta_pointing", 1.0), 0.0, 1.0)),
            "eta_uplink_atmospheric": float(clamp(up.get("eta_atmospheric", 1.0), 0.0, 1.0)),
            "eta_downlink_atmospheric": float(clamp(dn.get("eta_atmospheric", 1.0), 0.0, 1.0)),
            "uplink_atmosphere_path_km": float(up.get("atmosphere_path_km", 0.0) or 0.0),
            "downlink_atmosphere_path_km": float(dn.get("atmosphere_path_km", 0.0) or 0.0),
            "uplink_airmass": float(up.get("airmass", 1.0) or 1.0),
            "downlink_airmass": float(dn.get("airmass", 1.0) or 1.0),
            "background_model": str(bg_ref.get("background_model", "fixed") or "fixed"),
            "background_day_night": str(bg_ref.get("background_day_night", "night") or "night"),
            "background_uncertainty_cps": dict(bg_ref.get("background_uncertainty_cps", {}) or {}),
            "uplink_pointing_diagnostics": up.get("pointing_diagnostics", {}),
            "downlink_pointing_diagnostics": dn.get("pointing_diagnostics", {}),
            "uplink_turbulence_diagnostics": up.get("turbulence_diagnostics", {}),
            "downlink_turbulence_diagnostics": dn.get("turbulence_diagnostics", {}),
        },
        "segments_km": {
            "uplink": float(d_up),
            "downlink": float(d_down),
        },
    }


def _linear_to_db_loss(eta: float) -> float:
    eta = max(float(eta), 1e-15)
    return -10.0 * math.log10(eta)
