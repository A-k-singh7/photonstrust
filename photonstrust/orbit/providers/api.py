"""Public parity API for orbit provider lanes."""

from __future__ import annotations

from typing import Any

from photonstrust.orbit.providers import build_orbit_trace
from photonstrust.orbit.providers.base import OrbitProviderError, OrbitProviderRequest, OrbitProviderUnavailableError
from photonstrust.orbit.providers.parity import compare_provider_traces


def run_provider_parity(
    *,
    config: dict[str, Any],
    providers: list[str],
    reference_provider: str | None = None,
) -> dict[str, Any]:
    """Run parity comparison across provider traces for a satellite config."""

    if not isinstance(config, dict):
        raise TypeError("config must be a dict")

    rows = [str(name).strip().lower() for name in providers if str(name).strip()]
    if len(rows) < 2:
        raise ValueError("providers must include at least two provider names")

    request = _build_request(config)
    trace_a = _trace_or_raise(rows[0], request)
    trace_b = _trace_or_raise(rows[1], request)

    parity_ab = compare_provider_traces(trace_a, trace_b)
    thresholds = _thresholds_from_config(config)
    violations = _violations_from_parity(parity_ab.to_dict(), thresholds)

    out: dict[str, Any] = {
        "providers": list(rows[:2]),
        "execution_mode": str(request.execution_mode),
        "trace_a": trace_a.to_dict(),
        "trace_b": trace_b.to_dict(),
        "parity": parity_ab.to_dict(),
        "thresholds": thresholds,
        "violations": violations,
    }

    if reference_provider is not None and str(reference_provider).strip():
        ref_name = str(reference_provider).strip().lower()
        ref_trace = _trace_or_raise(ref_name, request)
        ref_a = compare_provider_traces(ref_trace, trace_a).to_dict()
        ref_b = compare_provider_traces(ref_trace, trace_b).to_dict()
        ref_violations = _violations_from_parity(ref_a, thresholds) + _violations_from_parity(ref_b, thresholds)
        out["reference_provider"] = ref_name
        out["reference_trace"] = ref_trace.to_dict()
        out["reference_parity"] = {
            "a": ref_a,
            "b": ref_b,
        }
        out["violations"].extend(ref_violations)

    return out


def _build_request(config: dict[str, Any]) -> OrbitProviderRequest:
    sat_cfg = config.get("satellite_qkd_chain") if isinstance(config.get("satellite_qkd_chain"), dict) else {}
    sat = sat_cfg.get("satellite") if isinstance(sat_cfg.get("satellite"), dict) else {}
    pass_geo = sat_cfg.get("pass_geometry") if isinstance(sat_cfg.get("pass_geometry"), dict) else {}
    orbit_provider = sat_cfg.get("orbit_provider") if isinstance(sat_cfg.get("orbit_provider"), dict) else {}

    tle_raw = sat.get("tle") if isinstance(sat.get("tle"), dict) else {}
    tle_cfg = orbit_provider.get("tle") if isinstance(orbit_provider.get("tle"), dict) else {}

    tle_line1 = (
        orbit_provider.get("tle_line1")
        or tle_cfg.get("line1")
        or sat.get("tle_line1")
        or tle_raw.get("line1")
    )
    tle_line2 = (
        orbit_provider.get("tle_line2")
        or tle_cfg.get("line2")
        or sat.get("tle_line2")
        or tle_raw.get("line2")
    )

    runtime = sat_cfg.get("runtime") if isinstance(sat_cfg.get("runtime"), dict) else {}
    mode = str(runtime.get("execution_mode") or config.get("execution_mode") or "preview").strip().lower() or "preview"

    return OrbitProviderRequest(
        altitude_km=float(sat.get("altitude_km") or 600.0),
        elevation_min_deg=float(pass_geo.get("elevation_min_deg") or 15.0),
        dt_s=float(pass_geo.get("dt_s") or 5.0),
        execution_mode=mode,
        tle_line1=str(tle_line1).strip() if tle_line1 is not None else None,
        tle_line2=str(tle_line2).strip() if tle_line2 is not None else None,
        satellite_name=str(sat_cfg.get("id") or sat.get("name") or "satellite"),
    )


def _trace_or_raise(provider_name: str, request: OrbitProviderRequest):
    try:
        return build_orbit_trace(str(provider_name).strip().lower(), request)
    except (OrbitProviderUnavailableError, OrbitProviderError) as exc:
        raise RuntimeError(str(exc)) from exc


def _thresholds_from_config(config: dict[str, Any]) -> dict[str, float]:
    sat_cfg = config.get("satellite_qkd_chain") if isinstance(config.get("satellite_qkd_chain"), dict) else {}
    orbit_provider = sat_cfg.get("orbit_provider") if isinstance(sat_cfg.get("orbit_provider"), dict) else {}

    return {
        "pass_start_s": float(orbit_provider.get("parity_max_start_end_delta_s", 30.0) or 30.0),
        "pass_end_s": float(orbit_provider.get("parity_max_start_end_delta_s", 30.0) or 30.0),
        "peak_elevation_deg": float(orbit_provider.get("parity_max_peak_elevation_delta_deg", 5.0) or 5.0),
        "peak_slant_range_km": float(orbit_provider.get("parity_max_peak_slant_range_delta_km", 250.0) or 250.0),
        "sample_count": float(orbit_provider.get("parity_max_sample_count_delta", 20) or 20),
    }


def _violations_from_parity(parity_payload: dict[str, Any], thresholds: dict[str, float]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    for metric in (
        "pass_start_s",
        "pass_end_s",
        "peak_elevation_deg",
        "peak_slant_range_km",
        "sample_count",
    ):
        row = parity_payload.get(metric)
        if not isinstance(row, dict):
            continue
        abs_delta = float(row.get("abs_delta", 0.0) or 0.0)
        limit = float(thresholds.get(metric, 0.0) or 0.0)
        if abs_delta > limit:
            violations.append(
                {
                    "metric": metric,
                    "delta_kind": "abs",
                    "observed": abs_delta,
                    "limit": limit,
                    "reference_provider": parity_payload.get("reference_provider"),
                    "candidate_provider": parity_payload.get("candidate_provider"),
                }
            )
    return violations
