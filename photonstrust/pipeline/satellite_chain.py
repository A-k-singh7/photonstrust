"""Satellite-to-ground PIC digital-twin orchestration (M5)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.evidence.signing import sign_bytes_ed25519
from photonstrust.orbit import annual_pass_count, generate_elevation_profile, simulate_orbit_pass
from photonstrust.pdk.registry import get_pdk
from photonstrust.pipeline.certify import run_certify
from photonstrust.pipeline.pic_qkd_bridge import pdk_coupler_efficiency
from photonstrust.utils import hash_dict
from photonstrust.workflow.schema import (
    satellite_qkd_chain_certificate_schema_path,
    satellite_qkd_chain_schema_path,
)


def run_satellite_chain(
    config: dict[str, Any],
    *,
    output_dir: Path | str | None = None,
    signing_key: Path | str | None = None,
) -> dict[str, Any]:
    """Run an integrated satellite-to-ground-PIC QKD chain and return a certificate."""

    if not isinstance(config, dict):
        raise TypeError("run_satellite_chain expects config as dict")

    _validate_chain_config_schema_if_available(config)
    sat_cfg = config.get("satellite_qkd_chain")
    if not isinstance(sat_cfg, dict):
        raise ValueError("config.satellite_qkd_chain is required")

    mission_id = str(sat_cfg.get("id") or "satellite_chain").strip() or "satellite_chain"
    out_root = Path(output_dir).expanduser().resolve() if output_dir is not None else None
    if out_root is not None:
        out_root.mkdir(parents=True, exist_ok=True)

    eta_chip, pic_cert_meta = _resolve_eta_chip(sat_cfg=sat_cfg, output_dir=out_root)
    orbit_cfg, eta_ground_terminal = _build_orbit_pass_config(sat_cfg=sat_cfg, eta_chip=eta_chip)
    orbit_result = simulate_orbit_pass(orbit_cfg)

    pass_metrics = _accumulate_pass_metrics(orbit_result)
    annual = _estimate_annual_yield(sat_cfg=sat_cfg, pass_metrics=pass_metrics)
    signoff = _build_signoff(pass_metrics=pass_metrics, annual=annual)

    certificate: dict[str, Any] = {
        "schema_version": "0.1",
        "kind": "satellite_qkd_chain_certificate",
        "run_id": _run_id_for(mission_id=mission_id, payload={"orbit": orbit_result, "pass": pass_metrics}),
        "generated_at": _now_iso(),
        "mission": mission_id,
        "inputs": {
            "config_hash": hash_dict(config),
            "protocol": str(sat_cfg.get("protocol") or "BB84_decoy"),
            "output_dir": str(out_root) if out_root is not None else None,
            "signing_key": str(Path(signing_key).expanduser().resolve()) if signing_key is not None else None,
        },
        "ground_station": {
            "latitude_deg": float(((sat_cfg.get("ground_station") or {}).get("latitude_deg") or 0.0)),
            "pic_cert_run_id": pic_cert_meta.get("run_id"),
            "eta_chip": float(eta_chip),
            "eta_ground_terminal": float(eta_ground_terminal),
        },
        "pass": {
            "altitude_km": float(((sat_cfg.get("satellite") or {}).get("altitude_km") or 0.0)),
            "elevation_min_deg": float(((sat_cfg.get("pass_geometry") or {}).get("elevation_min_deg") or 0.0)),
            "pass_duration_s": float(pass_metrics["pass_duration_s"]),
            "samples_evaluated": int(pass_metrics["samples_evaluated"]),
            "samples_with_positive_key_rate": int(pass_metrics["samples_with_positive_key_rate"]),
            "key_bits_accumulated": float(pass_metrics["key_bits_accumulated"]),
            "mean_key_rate_bps": float(pass_metrics["mean_key_rate_bps"]),
            "peak_key_rate_bps": float(pass_metrics["peak_key_rate_bps"]),
            "peak_elevation_deg": float(pass_metrics["peak_elevation_deg"]),
        },
        "annual_estimate": annual,
        "signoff": signoff,
        "signature": None,
        "artifacts": {
            "orbit_pass_id": orbit_result.get("pass_id"),
            "orbit_case_id": pass_metrics.get("case_id"),
            "pic_certificate_path": pic_cert_meta.get("certificate_path"),
        },
    }

    if signing_key is not None:
        key_path = Path(signing_key).expanduser().resolve()
        unsigned = dict(certificate)
        unsigned["signature"] = None
        message = _canonical_json_bytes(unsigned)
        certificate["signature"] = {
            "algorithm": "ed25519",
            "key_path": str(key_path),
            "signature_b64": sign_bytes_ed25519(private_key_pem_path=key_path, message=message),
            "message_sha256": hashlib.sha256(message).hexdigest(),
        }

    _validate_chain_certificate_schema_if_available(certificate)

    output_path: str | None = None
    if out_root is not None:
        cert_path = out_root / "satellite_qkd_chain_certificate.json"
        cert_path.write_text(json.dumps(certificate, indent=2), encoding="utf-8")
        output_path = str(cert_path)

    return {
        "decision": str(signoff["decision"]),
        "certificate": certificate,
        "output_path": output_path,
        "key_bits_accumulated": float(certificate["pass"]["key_bits_accumulated"]),
        "mean_key_rate_bps": float(certificate["pass"]["mean_key_rate_bps"]),
    }


def _resolve_eta_chip(*, sat_cfg: dict[str, Any], output_dir: Path | None) -> tuple[float, dict[str, Any]]:
    ground = sat_cfg.get("ground_station") or {}
    if not isinstance(ground, dict):
        return 1.0, {"run_id": None, "certificate_path": None}

    raw_eta_chip = ground.get("eta_chip")
    pic_graph_path = ground.get("pic_graph_path")
    pic_pdk = str(ground.get("pic_pdk") or "generic_silicon_photonics")

    if pic_graph_path:
        cert_output = (output_dir / "pic_cert") if output_dir is not None else None
        cert_result = run_certify(
            Path(str(pic_graph_path)).expanduser(),
            pdk_name=pic_pdk,
            protocol=str(sat_cfg.get("protocol") or "BB84_decoy"),
            wavelength_nm=float(((sat_cfg.get("satellite") or {}).get("wavelength_nm") or 1550.0)),
            output_dir=cert_output,
            dry_run=False,
        )

        certificate = cert_result.get("certificate") if isinstance(cert_result, dict) else None
        target = (certificate or {}).get("target_distance_summary") if isinstance(certificate, dict) else None
        eta_chip = _coerce_float((target or {}).get("eta_chip"), default=None)
        if eta_chip is None:
            eta_chip = _coerce_float(raw_eta_chip, default=1.0)

        return (
            float(max(0.0, min(1.0, eta_chip))),
            {
                "run_id": str(((certificate or {}).get("signoff") or {}).get("run_id") or "") or None,
                "certificate_path": cert_result.get("output_path") if isinstance(cert_result, dict) else None,
            },
        )

    eta_chip = _coerce_float(raw_eta_chip, default=1.0)
    return float(max(0.0, min(1.0, eta_chip))), {"run_id": None, "certificate_path": None}


def _build_orbit_pass_config(*, sat_cfg: dict[str, Any], eta_chip: float) -> tuple[dict[str, Any], float]:
    sat = sat_cfg.get("satellite") or {}
    atm = sat_cfg.get("atmosphere") or {}
    ground = sat_cfg.get("ground_station") or {}
    pass_geo = sat_cfg.get("pass_geometry") or {}

    altitude_km = float(sat.get("altitude_km") or 600.0)
    el_min_deg = float(pass_geo.get("elevation_min_deg") or 15.0)
    dt_s = float(pass_geo.get("dt_s") or 5.0)
    day_night = str(pass_geo.get("day_night") or "night").strip().lower() or "night"

    low_bg = 5000.0 if day_night == "day" else 200.0
    high_bg = 2000.0 if day_night == "day" else 50.0
    samples = generate_elevation_profile(
        altitude_km=altitude_km,
        el_min_deg=el_min_deg,
        dt_s=dt_s,
        day_night=day_night,
        low_el_background_cps=low_bg,
        high_el_background_cps=high_bg,
    )

    pdk_name = str(ground.get("pic_pdk") or "generic_silicon_photonics")
    eta_coupler = pdk_coupler_efficiency(get_pdk(pdk_name))
    eta_ground_terminal = (
        float(ground.get("telescope_efficiency") or 0.80)
        * float(ground.get("fibre_coupling_efficiency") or 0.45)
        * float(eta_chip)
        * float(eta_coupler)
    )
    eta_ground_terminal = max(0.0, min(1.0, eta_ground_terminal))

    protocol = str(sat_cfg.get("protocol") or "BB84_decoy")
    protocol_norm = protocol.strip().lower().replace("-", "_")
    is_bbm92 = protocol_norm in {"bbm92", "e91"}

    detector_type = str(ground.get("detector_type") or "ingaas").strip().lower()
    detector_class = _normalize_detector_class(detector_type)

    orbit_cfg = {
        "orbit_pass": {
            "id": str(sat_cfg.get("id") or "satellite_chain"),
            "band": _wavelength_to_band(float(sat.get("wavelength_nm") or 1550.0)),
            "wavelength_nm": float(sat.get("wavelength_nm") or 1550.0),
            "dt_s": float(dt_s),
            "samples": samples,
            "background_model": "fixed",
            "background_day_night": day_night,
            "availability": {
                "clear_fraction": float(
                    ((sat_cfg.get("ground_station") or {}).get("clear_sky_probability"))
                    or ((sat_cfg.get("output") or {}).get("clear_sky_probability"))
                    or 1.0
                )
            },
            "cases": [{"id": "median", "label": "Median", "channel_overrides": {}}],
        },
        "source": {
            "type": "spdc" if is_bbm92 else "emitter_cavity",
            "rep_rate_mhz": float(sat.get("rep_rate_mhz") or 100.0),
            "collection_efficiency": 1.0,
            "coupling_efficiency": float(eta_ground_terminal),
            "mu": float(sat.get("mu_signal") or 0.05),
        },
        "channel": {
            "model": "free_space",
            "tx_aperture_m": float(sat.get("tx_aperture_m") or 0.15),
            "rx_aperture_m": float(ground.get("rx_aperture_m") or 0.40),
            "atmosphere_path_model": str(atm.get("model") or "effective_thickness"),
            "atmosphere_effective_thickness_km": float(atm.get("effective_thickness_km") or 20.0),
            "atmospheric_extinction_db_per_km": float(atm.get("extinction_db_per_km") or 0.05),
            "pointing_jitter_urad": float(atm.get("pointing_jitter_urad") or 2.0),
            "turbulence_scintillation_index": float(atm.get("turbulence_scintillation_index") or 0.15),
            "connector_loss_db": 0.0,
            "background_model": "fixed",
            "background_day_night": day_night,
        },
        "detector": {
            "class": detector_class,
            "pde": float(ground.get("detector_pde") or 0.25),
            "dark_counts_cps": float(ground.get("detector_dcr_cps") or 1000.0),
            "jitter_ps_fwhm": float(ground.get("detector_jitter_ps_fwhm") or 500.0),
        },
        "timing": {
            "sync_drift_ps_rms": 10.0,
            "coincidence_window_ps": float(ground.get("coincidence_window_ps") or 1000.0),
        },
        "protocol": {
            "name": "BBM92" if is_bbm92 else "BB84_decoy",
            "mu": float(sat.get("mu_signal") or 0.5),
            "nu": float(sat.get("mu_decoy") or 0.1),
            "omega": 0.0,
            "misalignment_prob": float(sat.get("source_qber_contribution") or 0.005),
            "sifting_factor": 0.5,
            "ec_efficiency": 1.16,
        },
        "uncertainty": {},
    }
    return orbit_cfg, float(eta_ground_terminal)


def _accumulate_pass_metrics(orbit_result: dict[str, Any]) -> dict[str, Any]:
    dt_s = float(orbit_result.get("dt_s") or 1.0)
    cases = orbit_result.get("cases")
    case_rows = list(cases) if isinstance(cases, list) else []
    if not case_rows:
        return {
            "case_id": None,
            "samples_evaluated": 0,
            "samples_with_positive_key_rate": 0,
            "key_bits_accumulated": 0.0,
            "pass_duration_s": 0.0,
            "mean_key_rate_bps": 0.0,
            "peak_key_rate_bps": 0.0,
            "peak_elevation_deg": 0.0,
        }

    selected = None
    for row in case_rows:
        if isinstance(row, dict) and str(row.get("case_id") or "").strip().lower() == "median":
            selected = row
            break
    if selected is None:
        selected = case_rows[0] if isinstance(case_rows[0], dict) else {}

    points = selected.get("points") if isinstance(selected, dict) else None
    point_rows = list(points) if isinstance(points, list) else []

    key_rates = []
    elevations = []
    for point in point_rows:
        if not isinstance(point, dict):
            continue
        qkd = point.get("qkd")
        key = _coerce_float((qkd or {}).get("key_rate_bps"), default=0.0) if isinstance(qkd, dict) else 0.0
        el = _coerce_float(point.get("elevation_deg"), default=0.0)
        key_rates.append(max(0.0, float(key)))
        elevations.append(max(0.0, float(el)))

    total_key_bits = float(sum(key_rates) * dt_s)
    pass_duration_s = float(len(key_rates) * dt_s)
    mean_key_rate = float(total_key_bits / pass_duration_s) if pass_duration_s > 0.0 else 0.0
    peak_key = float(max(key_rates)) if key_rates else 0.0
    peak_idx = key_rates.index(peak_key) if key_rates else -1
    peak_el = float(elevations[peak_idx]) if peak_idx >= 0 and peak_idx < len(elevations) else 0.0

    return {
        "case_id": str((selected or {}).get("case_id") or "median"),
        "samples_evaluated": int(len(key_rates)),
        "samples_with_positive_key_rate": int(sum(1 for value in key_rates if value > 0.0)),
        "key_bits_accumulated": total_key_bits,
        "pass_duration_s": pass_duration_s,
        "mean_key_rate_bps": mean_key_rate,
        "peak_key_rate_bps": peak_key,
        "peak_elevation_deg": peak_el,
    }


def _estimate_annual_yield(*, sat_cfg: dict[str, Any], pass_metrics: dict[str, Any]) -> dict[str, Any] | None:
    out_cfg = sat_cfg.get("output") or {}
    if not bool(out_cfg.get("annual_estimate", True)):
        return None

    ground = sat_cfg.get("ground_station") or {}
    sat = sat_cfg.get("satellite") or {}
    pass_geo = sat_cfg.get("pass_geometry") or {}

    passes_per_day = annual_pass_count(
        latitude_deg=float(ground.get("latitude_deg") or 0.0),
        inclination_deg=float(sat.get("orbit_inclination_deg") or 70.0),
        altitude_km=float(sat.get("altitude_km") or 600.0),
        el_min_deg=float(pass_geo.get("elevation_min_deg") or 15.0),
    )
    clear_prob = max(
        0.0,
        min(
            1.0,
            float(
                ((ground.get("clear_sky_probability")) or (out_cfg.get("clear_sky_probability")) or 0.40)
            ),
        ),
    )
    bits_per_year = float(passes_per_day * float(pass_metrics.get("key_bits_accumulated") or 0.0) * clear_prob * 365.0)

    return {
        "passes_per_day": float(passes_per_day),
        "clear_sky_probability": float(clear_prob),
        "key_bits_per_year": bits_per_year,
        "key_mbits_per_year": float(bits_per_year / 1.0e6),
        "notes": "Annual estimate assumes independent pass yield and clear-sky fraction.",
    }


def _build_signoff(*, pass_metrics: dict[str, Any], annual: dict[str, Any] | None) -> dict[str, Any]:
    key_positive_at_zenith = float(pass_metrics.get("peak_key_rate_bps") or 0.0) > 0.0
    if annual is None:
        annual_above_1mbit = float(pass_metrics.get("key_bits_accumulated") or 0.0) >= 1.0e6
    else:
        annual_above_1mbit = float(annual.get("key_bits_per_year") or 0.0) >= 1.0e6

    decision = "GO" if key_positive_at_zenith and annual_above_1mbit else "HOLD"
    return {
        "decision": decision,
        "key_rate_positive_at_zenith": bool(key_positive_at_zenith),
        "annual_key_above_1mbit": bool(annual_above_1mbit),
    }


def _validate_chain_config_schema_if_available(config: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return

    schema_path = satellite_qkd_chain_schema_path()
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=config, schema=schema)


def _validate_chain_certificate_schema_if_available(certificate: dict[str, Any]) -> None:
    try:
        from jsonschema import validate
    except Exception:
        return

    schema_path = satellite_qkd_chain_certificate_schema_path()
    if not schema_path.exists():
        return
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=certificate, schema=schema)


def _run_id_for(*, mission_id: str, payload: Any) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "mission": str(mission_id),
                "payload": payload,
            }
        )
    ).hexdigest()[:12]


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_detector_class(detector_type: str) -> str:
    text = str(detector_type or "").strip().lower()
    if "snspd" in text:
        return "snspd"
    if "si" in text:
        return "si_apd"
    return "ingaas"


def _wavelength_to_band(wavelength_nm: float) -> str:
    wl = float(wavelength_nm)
    if wl <= 900.0:
        return "nir_850"
    if wl <= 1400.0:
        return "o_1310"
    return "c_1550"


def _coerce_float(value: Any, *, default: float | None) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed != parsed:
        return default
    return float(parsed)
