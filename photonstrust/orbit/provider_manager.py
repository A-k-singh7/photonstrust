"""Orbit provider selection and provenance helpers for satellite chain."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from photonstrust.orbit.providers import build_orbit_trace
from photonstrust.orbit.providers.base import OrbitProviderError, OrbitProviderRequest, OrbitProviderUnavailableError, OrbitTrace, OrbitTraceSample
from photonstrust.orbit.providers.parity import compare_provider_traces


_DEFAULT_PROVIDER_PREVIEW = "analytic"
_DEFAULT_PROVIDER_CERTIFICATION = "analytic"
_PROVIDER_ALIASES = {
    "internal_analytic": "analytic",
}


def resolve_orbit_provider(
    *,
    provider_cfg: dict[str, Any] | None,
    execution_mode: str,
    sat_cfg: dict[str, Any],
    fallback_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Resolve orbit sample provider and return samples plus trust metadata."""

    cfg = provider_cfg if isinstance(provider_cfg, dict) else {}
    mode = str(execution_mode or "preview").strip().lower() or "preview"
    requested_default = (
        _DEFAULT_PROVIDER_CERTIFICATION if mode == "certification" else _DEFAULT_PROVIDER_PREVIEW
    )
    requested_name = _normalize_provider_alias(str(cfg.get("name") or requested_default).strip() or requested_default)
    allow_fallback = bool(cfg.get("allow_fallback", mode == "preview"))

    trusted_raw = cfg.get("trusted_providers")
    trusted_rows = trusted_raw if isinstance(trusted_raw, (list, tuple, set)) else (requested_name,)
    trusted_providers = {
        _normalize_provider_alias(str(row).strip())
        for row in trusted_rows
        if str(row).strip()
    }
    if not trusted_providers:
        trusted_providers = {requested_name}

    request = _build_request(sat_cfg=sat_cfg, cfg=cfg, mode=mode)

    selected_name = requested_name
    used_fallback = False
    notes: list[str] = []

    trace, requested_error = _trace_for(provider_id=requested_name, request=request)
    requested_unavailable = trace is None

    if trace is None and allow_fallback:
        fallback_name = _DEFAULT_PROVIDER_PREVIEW
        fallback_trace, fallback_error = _trace_for(provider_id=fallback_name, request=request)
        if fallback_trace is not None:
            trace = fallback_trace
            selected_name = fallback_name
            used_fallback = fallback_name != requested_name
            notes.append(
                f"provider {requested_name!r} unavailable ({requested_error}); "
                f"falling back to {fallback_name!r}"
            )
        else:
            notes.append(
                f"provider {requested_name!r} unavailable ({requested_error}); "
                f"fallback provider {fallback_name!r} unavailable ({fallback_error})"
            )

    if trace is None:
        trace = _trace_from_fallback_samples(fallback_samples=fallback_samples, mode=mode)
        selected_name = _DEFAULT_PROVIDER_PREVIEW
        used_fallback = True
        notes.append("synthetic fallback trace used from precomputed orbit samples")

    provider_version = str(trace.provider_version or "0")
    source_hash = _trace_source_hash(trace)

    expected_version = cfg.get("expected_version")
    if expected_version is not None and str(expected_version).strip() and str(expected_version).strip() != provider_version:
        notes.append(
            "provider version mismatch: "
            f"expected={str(expected_version).strip()!r} actual={provider_version!r}"
        )

    expected_source_hash = cfg.get("expected_source_hash")
    if (
        expected_source_hash is not None
        and str(expected_source_hash).strip()
        and str(expected_source_hash).strip().lower() != source_hash.lower()
    ):
        notes.append("provider source hash mismatch against expected_source_hash")

    parity_report, parity_ok = _evaluate_parity(
        selected_trace=trace,
        selected_name=selected_name,
        request=request,
        cfg=cfg,
        mode=mode,
        notes=notes,
    )

    base_uncertainty_sigma = _coerce_float(cfg.get("uncertainty_sigma_cps"), default=0.0)
    parity_uncertainty_sigma = _coerce_float(parity_report.get("derived_uncertainty_sigma_cps"), default=0.0)
    uncertainty_sigma_cps = max(float(base_uncertainty_sigma or 0.0), float(parity_uncertainty_sigma or 0.0))

    max_uncertainty_sigma_cps = _coerce_float(
        cfg.get("max_uncertainty_sigma_cps"),
        default=250.0 if mode == "certification" else 1000.0,
    )
    uncertainty_ok = (
        float(uncertainty_sigma_cps) <= float(max_uncertainty_sigma_cps)
        if max_uncertainty_sigma_cps is not None
        else True
    )

    trust_status = "trusted"
    if requested_unavailable:
        trust_status = "unavailable"
    elif not bool(trace.trusted):
        trust_status = "untrusted"
    elif selected_name not in trusted_providers:
        trust_status = "untrusted"
    elif any("mismatch" in note for note in notes):
        trust_status = "untrusted"

    if trust_status == "unavailable":
        parity_ok = False
        uncertainty_ok = False

    if selected_name == "analytic" and fallback_samples:
        samples_payload = [dict(row) for row in fallback_samples if isinstance(row, dict)]
    else:
        samples_payload = _trace_samples_to_payload(trace)

    return {
        "requested_name": requested_name,
        "selected_name": selected_name,
        "used_fallback": bool(used_fallback),
        "provider_name": str(trace.provider_id),
        "provider_version": provider_version,
        "source_hash": source_hash,
        "trust_status": trust_status,
        "parity_ok": bool(parity_ok),
        "parity_report": parity_report,
        "uncertainty_ok": bool(uncertainty_ok),
        "uncertainty_sigma_cps": float(uncertainty_sigma_cps),
        "max_uncertainty_sigma_cps": float(max_uncertainty_sigma_cps)
        if max_uncertainty_sigma_cps is not None
        else None,
        "notes": notes,
        "samples": samples_payload,
        "context": {
            "execution_mode": mode,
            "mission_id": str(sat_cfg.get("id") or "satellite_chain"),
        },
    }


def _build_request(*, sat_cfg: dict[str, Any], cfg: dict[str, Any], mode: str) -> OrbitProviderRequest:
    sat_raw = sat_cfg.get("satellite")
    sat: dict[str, Any] = sat_raw if isinstance(sat_raw, dict) else {}
    pass_geo_raw = sat_cfg.get("pass_geometry")
    pass_geo: dict[str, Any] = pass_geo_raw if isinstance(pass_geo_raw, dict) else {}

    tle_raw_block = sat.get("tle")
    tle_raw: dict[str, Any] = tle_raw_block if isinstance(tle_raw_block, dict) else {}
    tle_cfg_block = cfg.get("tle")
    tle_cfg: dict[str, Any] = tle_cfg_block if isinstance(tle_cfg_block, dict) else {}

    tle_line1 = (
        cfg.get("tle_line1")
        or tle_cfg.get("line1")
        or sat.get("tle_line1")
        or tle_raw.get("line1")
    )
    tle_line2 = (
        cfg.get("tle_line2")
        or tle_cfg.get("line2")
        or sat.get("tle_line2")
        or tle_raw.get("line2")
    )

    satellite_name = (
        sat.get("satellite_name")
        or sat.get("name")
        or cfg.get("satellite_name")
        or sat_cfg.get("id")
        or "satellite"
    )

    return OrbitProviderRequest(
        altitude_km=float(sat.get("altitude_km") or 600.0),
        elevation_min_deg=float(pass_geo.get("elevation_min_deg") or 15.0),
        dt_s=float(pass_geo.get("dt_s") or 5.0),
        execution_mode=mode,
        tle_line1=str(tle_line1).strip() if tle_line1 is not None else None,
        tle_line2=str(tle_line2).strip() if tle_line2 is not None else None,
        satellite_name=str(satellite_name),
    )


def _trace_for(*, provider_id: str, request: OrbitProviderRequest) -> tuple[OrbitTrace | None, str | None]:
    name = _normalize_provider_alias(provider_id)
    try:
        return build_orbit_trace(name, request), None
    except OrbitProviderUnavailableError as exc:
        return None, str(exc)
    except OrbitProviderError as exc:
        return None, str(exc)
    except Exception as exc:
        return None, str(exc)


def _trace_from_fallback_samples(*, fallback_samples: list[dict[str, Any]], mode: str) -> OrbitTrace:
    samples: list[OrbitTraceSample] = []
    for row in fallback_samples:
        if not isinstance(row, dict):
            continue
        samples.append(
            OrbitTraceSample(
                t_s=float(row.get("t_s", 0.0) or 0.0),
                elevation_deg=float(row.get("elevation_deg", 0.0) or 0.0),
                slant_range_km=float(row.get("distance_km", 0.0) or 0.0),
            )
        )
    samples.sort(key=lambda item: float(item.t_s))
    return OrbitTrace(
        provider_id="analytic",
        provider_version="synthetic-fallback",
        execution_mode=mode,
        trusted=False,
        compatibility="fallback_samples",
        samples=tuple(samples),
        metadata={"reason": "fallback_samples"},
        untrusted_reasons=("fallback_samples",),
    )


def _trace_source_hash(trace: OrbitTrace) -> str:
    metadata = trace.metadata if isinstance(trace.metadata, dict) else {}
    tle_hash = metadata.get("tle_hash")
    if isinstance(tle_hash, str) and tle_hash.strip():
        return tle_hash.strip()
    payload = {
        "provider_id": trace.provider_id,
        "provider_version": trace.provider_version,
        "compatibility": trace.compatibility,
        "sample_count": trace.sample_count,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trace_samples_to_payload(trace: OrbitTrace) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sample in trace.samples:
        rows.append(
            {
                "t_s": float(sample.t_s),
                "distance_km": float(sample.slant_range_km),
                "elevation_deg": float(sample.elevation_deg),
            }
        )
    return rows


def _evaluate_parity(
    *,
    selected_trace: OrbitTrace,
    selected_name: str,
    request: OrbitProviderRequest,
    cfg: dict[str, Any],
    mode: str,
    notes: list[str],
) -> tuple[dict[str, Any], bool]:
    raw_reference = cfg.get("reference_provider")
    if raw_reference is None:
        if selected_name == "skyfield":
            raw_reference = "poliastro"
        elif selected_name == "poliastro":
            raw_reference = "analytic"

    reference_provider = (
        _normalize_provider_alias(str(raw_reference).strip())
        if raw_reference is not None and str(raw_reference).strip()
        else None
    )
    require_parity = bool(cfg.get("require_parity", mode == "certification" and reference_provider is not None))

    thresholds = {
        "pass_start_s": float(_coerce_float(cfg.get("parity_max_start_end_delta_s"), default=30.0) or 30.0),
        "pass_end_s": float(_coerce_float(cfg.get("parity_max_start_end_delta_s"), default=30.0) or 30.0),
        "peak_elevation_deg": float(
            _coerce_float(cfg.get("parity_max_peak_elevation_delta_deg"), default=5.0) or 5.0
        ),
        "peak_slant_range_km": float(
            _coerce_float(cfg.get("parity_max_peak_slant_range_delta_km"), default=250.0) or 250.0
        ),
        "sample_count": float(_coerce_float(cfg.get("parity_max_sample_count_delta"), default=20.0) or 20.0),
    }

    if not reference_provider:
        report = {
            "required": bool(require_parity),
            "reference_provider": None,
            "violations": [],
            "thresholds": thresholds,
            "derived_uncertainty_sigma_cps": 0.0,
        }
        return report, (not require_parity)

    reference_trace, reference_error = _trace_for(provider_id=reference_provider, request=request)
    if reference_trace is None:
        notes.append(f"parity reference provider {reference_provider!r} unavailable: {reference_error}")
        report = {
            "required": bool(require_parity),
            "reference_provider": reference_provider,
            "error": str(reference_error),
            "violations": [
                {
                    "metric": "reference_provider_available",
                    "observed": 1.0,
                    "limit": 0.0,
                }
            ]
            if require_parity
            else [],
            "thresholds": thresholds,
            "derived_uncertainty_sigma_cps": 50.0 if require_parity else 0.0,
        }
        return report, (not require_parity)

    parity = compare_provider_traces(reference_trace, selected_trace)
    violations: list[dict[str, Any]] = []
    for metric, delta in (
        ("pass_start_s", parity.pass_start_s),
        ("pass_end_s", parity.pass_end_s),
        ("peak_elevation_deg", parity.peak_elevation_deg),
        ("peak_slant_range_km", parity.peak_slant_range_km),
        ("sample_count", parity.sample_count),
    ):
        limit = float(thresholds[metric])
        if float(delta.abs_delta) > limit:
            violations.append(
                {
                    "metric": metric,
                    "observed": float(delta.abs_delta),
                    "limit": float(limit),
                    "delta": float(delta.delta),
                    "delta_kind": "abs",
                }
            )

    derived_uncertainty_sigma_cps = float(
        max(
            float(parity.peak_slant_range_km.abs_delta) * 0.1,
            float(parity.peak_elevation_deg.abs_delta) * 2.0,
        )
    )
    report = parity.to_dict()
    report.update(
        {
            "required": bool(require_parity),
            "reference_provider": reference_provider,
            "thresholds": thresholds,
            "violations": violations,
            "derived_uncertainty_sigma_cps": derived_uncertainty_sigma_cps,
        }
    )
    return report, len(violations) == 0


def _normalize_provider_alias(name: str) -> str:
    normalized = str(name or "").strip().lower() or _DEFAULT_PROVIDER_PREVIEW
    return _PROVIDER_ALIASES.get(normalized, normalized)


def _coerce_float(value: Any, *, default: float | None) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    if parsed != parsed:
        return default
    return float(parsed)
