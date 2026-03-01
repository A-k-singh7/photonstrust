"""Foundry DRC sealed runner seam (metadata-safe summary only).

This module intentionally exposes a minimal, non-proprietary contract for
foundry DRC outcomes. It must never emit deck paths, deck content, or rule text.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from photonstrust.layout.pic.generic_cli_sealed_runner import run_generic_cli_sealed
from photonstrust.utils import hash_dict

_ALLOWED_CHECK_STATUSES = {"pass", "fail", "error"}
_ALLOWED_RUN_STATUSES = {"pass", "fail", "error"}
_LOCAL_DRC_RULES: tuple[tuple[str, str], ...] = (
    ("DRC.WG.MIN_WIDTH", "wg_min_width"),
    ("DRC.WG.MIN_SPACING", "wg_min_spacing"),
    ("DRC.WG.MIN_BEND_RADIUS", "wg_min_bend_radius"),
    ("DRC.WG.MIN_ENCLOSURE", "wg_min_enclosure"),
)
_LOCAL_DRC_DEFAULTS_UM: dict[str, float] = {
    "DRC.WG.MIN_WIDTH": 0.45,
    "DRC.WG.MIN_SPACING": 0.20,
    "DRC.WG.MIN_BEND_RADIUS": 5.0,
    "DRC.WG.MIN_ENCLOSURE": 1.0,
}
_GENERIC_CLI_EMPTY_CHECKS_ERROR_CODE = "generic_cli_empty_checks"
_GENERIC_CLI_STATUS_CHECKS_CONFLICT_ERROR_CODE = "generic_cli_status_checks_conflict"
_GENERIC_CLI_SUMMARY_JSON_REQUIRED_ERROR_CODE = "generic_cli_summary_json_required"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_status(value: Any, *, default: str = "error") -> str:
    status = _clean_text(value).lower()
    if status in _ALLOWED_RUN_STATUSES:
        return status
    return default


def _normalize_checks(raw_checks: Any) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    if not isinstance(raw_checks, list):
        return checks

    for i, raw in enumerate(raw_checks):
        if not isinstance(raw, dict):
            continue
        check_id = _clean_text(raw.get("id")) or f"check_{i}"
        check_name = _clean_text(raw.get("name")) or check_id
        status_raw = _clean_text(raw.get("status")).lower()
        status = status_raw if status_raw in _ALLOWED_CHECK_STATUSES else "error"
        checks.append({"id": check_id, "name": check_name, "status": status})

    checks.sort(key=lambda c: (c["id"].lower(), c["name"].lower()))
    return checks


def _normalize_check_status_with_map(raw_status: Any, check_status_map: dict[str, str] | None) -> str:
    status_raw = _clean_text(raw_status).lower()
    if check_status_map:
        mapped_value = None
        for source_status, normalized_status in check_status_map.items():
            if _clean_text(source_status).lower() == status_raw:
                mapped_value = normalized_status
                break
        mapped = _clean_text(mapped_value).lower()
        if mapped in _ALLOWED_CHECK_STATUSES:
            return mapped
    if status_raw in _ALLOWED_CHECK_STATUSES:
        return status_raw
    return "error"


def _normalize_checks_with_status_map(raw_checks: Any, check_status_map: dict[str, str] | None) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    if not isinstance(raw_checks, list):
        return checks

    for i, raw in enumerate(raw_checks):
        if not isinstance(raw, dict):
            continue
        check_id = _clean_text(raw.get("id") or raw.get("check_id")) or f"check_{i}"
        check_name = _clean_text(raw.get("name") or raw.get("check_name")) or check_id
        status = _normalize_check_status_with_map(raw.get("status"), check_status_map)
        checks.append({"id": check_id, "name": check_name, "status": status})

    checks.sort(key=lambda c: (c["id"].lower(), c["name"].lower()))
    return checks


def _derived_status(checks: list[dict[str, str]]) -> str:
    if any(c["status"] == "error" for c in checks):
        return "error"
    if any(c["status"] == "fail" for c in checks):
        return "fail"
    return "pass"


def _harden_generic_cli_outcome(
    *,
    status: str,
    checks: list[dict[str, str]],
    error_code: str | None,
) -> tuple[str, str | None]:
    normalized_status = _normalize_status(status, default="error")
    normalized_error_code = _clean_text(error_code) or None
    if normalized_status != "pass":
        return normalized_status, normalized_error_code
    if not checks:
        return "error", normalized_error_code or _GENERIC_CLI_EMPTY_CHECKS_ERROR_CODE
    if any(_clean_text(check.get("status")).lower() in {"fail", "error"} for check in checks):
        return "error", normalized_error_code or _GENERIC_CLI_STATUS_CHECKS_CONFLICT_ERROR_CODE
    return normalized_status, normalized_error_code


def _deterministic_run_id(*, execution_backend: str, deck_fingerprint: str | None, checks: list[dict[str, str]]) -> str:
    seed = {
        "execution_backend": execution_backend,
        "deck_fingerprint": deck_fingerprint,
        "checks": checks,
    }
    return f"drcs_{hash_dict(seed)[:12]}"


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


def _sorted_unique_strings(values: list[str]) -> list[str]:
    cleaned = {_clean_text(v) for v in values if _clean_text(v)}
    return sorted(cleaned, key=lambda t: (t.lower(), t))


def _extract_local_routes_payload(req: dict[str, Any]) -> list[Any] | None:
    raw_routes = req.get("routes")
    if isinstance(raw_routes, dict) and isinstance(raw_routes.get("routes"), list):
        return list(raw_routes.get("routes"))
    if isinstance(raw_routes, list):
        return list(raw_routes)

    mock_result = req.get("mock_result")
    if isinstance(mock_result, dict):
        mock_routes = mock_result.get("routes")
        if isinstance(mock_routes, dict) and isinstance(mock_routes.get("routes"), list):
            return list(mock_routes.get("routes"))
        if isinstance(mock_routes, list):
            return list(mock_routes)

    return None


def _extract_local_design_rules(req: dict[str, Any]) -> dict[str, Any]:
    pdk_payload = req.get("pdk")
    if not isinstance(pdk_payload, dict):
        return {}
    design_rules = pdk_payload.get("design_rules")
    if isinstance(design_rules, dict):
        return dict(design_rules)
    return {}


def _resolve_design_rule_um(design_rules: dict[str, Any], *, keys: tuple[str, ...], fallback: float) -> float:
    for key in keys:
        if key not in design_rules:
            continue
        parsed = _safe_float(design_rules.get(key))
        if parsed is not None and parsed >= 0.0:
            return parsed
    return float(fallback)


def _resolve_local_rule_thresholds(design_rules: dict[str, Any]) -> dict[str, float]:
    return {
        "DRC.WG.MIN_WIDTH": _resolve_design_rule_um(
            design_rules,
            keys=("min_waveguide_width_um", "min_width_um", "waveguide_min_width_um"),
            fallback=_LOCAL_DRC_DEFAULTS_UM["DRC.WG.MIN_WIDTH"],
        ),
        "DRC.WG.MIN_SPACING": _resolve_design_rule_um(
            design_rules,
            keys=(
                "min_waveguide_spacing_um",
                "min_waveguide_gap_um",
                "min_spacing_um",
                "min_gap_um",
            ),
            fallback=_LOCAL_DRC_DEFAULTS_UM["DRC.WG.MIN_SPACING"],
        ),
        "DRC.WG.MIN_BEND_RADIUS": _resolve_design_rule_um(
            design_rules,
            keys=("min_bend_radius_um", "min_waveguide_bend_radius_um", "min_radius_um"),
            fallback=_LOCAL_DRC_DEFAULTS_UM["DRC.WG.MIN_BEND_RADIUS"],
        ),
        "DRC.WG.MIN_ENCLOSURE": _resolve_design_rule_um(
            design_rules,
            keys=("min_waveguide_enclosure_um", "min_enclosure_um", "waveguide_min_enclosure_um"),
            fallback=_LOCAL_DRC_DEFAULTS_UM["DRC.WG.MIN_ENCLOSURE"],
        ),
    }


def _route_id(raw_route: dict[str, Any], *, index: int) -> str:
    return _clean_text(raw_route.get("route_id") or raw_route.get("id")) or f"route_{index}"


def _route_layer(raw_route: dict[str, Any]) -> str:
    raw_layer = raw_route.get("layer")
    if isinstance(raw_layer, dict):
        layer = _clean_text(raw_layer.get("layer"))
        datatype = _clean_text(raw_layer.get("datatype"))
        if layer or datatype:
            return f"{layer}:{datatype}" if datatype else layer
    for key in ("layer", "layer_name", "layer_id", "route_layer"):
        value = _clean_text(raw_route.get(key))
        if value:
            return value
    return "default"


def _route_width_um(raw_route: dict[str, Any]) -> float | None:
    for key in ("width_um", "width", "core_width_um"):
        parsed = _safe_float(raw_route.get(key))
        if parsed is not None and parsed >= 0.0:
            return parsed
    return None


def _route_enclosure_um(raw_route: dict[str, Any]) -> float | None:
    for key in ("enclosure_um", "cladding_enclosure_um", "waveguide_enclosure_um"):
        parsed = _safe_float(raw_route.get(key))
        if parsed is not None and parsed >= 0.0:
            return parsed

    raw_layers = raw_route.get("layers")
    if isinstance(raw_layers, dict):
        cladding = raw_layers.get("cladding")
        if isinstance(cladding, dict):
            parsed = _safe_float(cladding.get("enclosure_um"))
            if parsed is not None and parsed >= 0.0:
                return parsed

    return None


def _normalize_points_um(raw_points: Any) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    if not isinstance(raw_points, list):
        return points

    for point in raw_points:
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue
        x = _safe_float(point[0])
        y = _safe_float(point[1])
        if x is None or y is None:
            continue
        points.append((x, y))
    return points


def _polyline_segments(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        if abs(p0[0] - p1[0]) <= 1e-15 and abs(p0[1] - p1[1]) <= 1e-15:
            continue
        segments.append((p0, p1))
    return segments


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a: tuple[float, float], p: tuple[float, float], b: tuple[float, float], *, eps: float = 1e-12) -> bool:
    return (
        min(a[0], b[0]) - eps <= p[0] <= max(a[0], b[0]) + eps
        and min(a[1], b[1]) - eps <= p[1] <= max(a[1], b[1]) + eps
    )


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    eps = 1e-12
    o1 = _orientation(a, b, c)
    o2 = _orientation(a, b, d)
    o3 = _orientation(c, d, a)
    o4 = _orientation(c, d, b)

    if ((o1 > eps and o2 < -eps) or (o1 < -eps and o2 > eps)) and (
        (o3 > eps and o4 < -eps) or (o3 < -eps and o4 > eps)
    ):
        return True
    if abs(o1) <= eps and _on_segment(a, c, b, eps=eps):
        return True
    if abs(o2) <= eps and _on_segment(a, d, b, eps=eps):
        return True
    if abs(o3) <= eps and _on_segment(c, a, d, eps=eps):
        return True
    if abs(o4) <= eps and _on_segment(c, b, d, eps=eps):
        return True
    return False


def _point_segment_distance_um(
    point: tuple[float, float],
    seg_a: tuple[float, float],
    seg_b: tuple[float, float],
) -> float:
    vx = seg_b[0] - seg_a[0]
    vy = seg_b[1] - seg_a[1]
    norm2 = vx * vx + vy * vy
    if norm2 <= 1e-15:
        return math.hypot(point[0] - seg_a[0], point[1] - seg_a[1])

    t = ((point[0] - seg_a[0]) * vx + (point[1] - seg_a[1]) * vy) / norm2
    t = min(1.0, max(0.0, t))
    proj_x = seg_a[0] + t * vx
    proj_y = seg_a[1] + t * vy
    return math.hypot(point[0] - proj_x, point[1] - proj_y)


def _segment_distance_um(
    seg_a: tuple[tuple[float, float], tuple[float, float]],
    seg_b: tuple[tuple[float, float], tuple[float, float]],
) -> float:
    a0, a1 = seg_a
    b0, b1 = seg_b

    if _segments_intersect(a0, a1, b0, b1):
        return 0.0

    return min(
        _point_segment_distance_um(a0, b0, b1),
        _point_segment_distance_um(a1, b0, b1),
        _point_segment_distance_um(b0, a0, a1),
        _point_segment_distance_um(b1, a0, a1),
    )


def _route_centerline_distance_um(route_a: dict[str, Any], route_b: dict[str, Any]) -> float | None:
    segments_a = route_a.get("segments") if isinstance(route_a.get("segments"), list) else []
    segments_b = route_b.get("segments") if isinstance(route_b.get("segments"), list) else []
    if not segments_a or not segments_b:
        return None

    best = math.inf
    for seg_a in segments_a:
        if not isinstance(seg_a, tuple) or len(seg_a) != 2:
            continue
        for seg_b in segments_b:
            if not isinstance(seg_b, tuple) or len(seg_b) != 2:
                continue
            dist = _segment_distance_um(seg_a, seg_b)
            if dist < best:
                best = dist

    if not math.isfinite(best):
        return None
    return best


def _bend_radius_from_triplet_um(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
) -> float | None:
    a = math.hypot(p1[0] - p2[0], p1[1] - p2[1])
    b = math.hypot(p0[0] - p2[0], p0[1] - p2[1])
    c = math.hypot(p0[0] - p1[0], p0[1] - p1[1])
    if min(a, b, c) <= 1e-15:
        return None

    twice_area = abs((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p1[1] - p0[1]) * (p2[0] - p0[0]))
    if twice_area <= 1e-15:
        return None

    radius_um = (a * b * c) / (2.0 * twice_area)
    if not math.isfinite(radius_um):
        return None
    return radius_um


def _collect_route_bend_radii_um(raw_route: dict[str, Any], points: list[tuple[float, float]]) -> list[float]:
    radii: list[float] = []

    raw_bends = raw_route.get("bends")
    if isinstance(raw_bends, list):
        for bend in raw_bends:
            if not isinstance(bend, dict):
                continue
            radius = _safe_float(bend.get("radius_um") if "radius_um" in bend else bend.get("radius"))
            if radius is None or radius < 0.0:
                continue
            radii.append(radius)

    if len(points) >= 3:
        for i in range(len(points) - 2):
            radius = _bend_radius_from_triplet_um(points[i], points[i + 1], points[i + 2])
            if radius is not None and radius >= 0.0:
                radii.append(radius)

    return radii


def _normalize_local_routes(raw_routes: list[Any]) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for i, raw_route in enumerate(raw_routes):
        if not isinstance(raw_route, dict):
            continue
        route_id = _route_id(raw_route, index=i)
        points = _normalize_points_um(raw_route.get("points_um"))
        routes.append(
            {
                "route_id": route_id,
                "layer": _route_layer(raw_route),
                "width_um": _route_width_um(raw_route),
                "enclosure_um": _route_enclosure_um(raw_route),
                "segments": _polyline_segments(points),
                "bend_radii_um": _collect_route_bend_radii_um(raw_route, points),
            }
        )

    routes.sort(key=lambda r: (str(r.get("route_id", "")).lower(), str(r.get("route_id", ""))))
    return routes


def _rule_result(
    *,
    status: str,
    required_um: float | None,
    observed_um: float | None,
    violation_count: int,
    entity_refs: list[str],
) -> dict[str, Any]:
    normalized_status = _normalize_status(status, default="error")
    required_value = _safe_float(required_um)
    observed_value = _safe_float(observed_um) if observed_um is not None else None
    violations = max(0, int(violation_count))
    refs = _sorted_unique_strings(entity_refs)
    return {
        "status": normalized_status,
        "required_um": required_value,
        "observed_um": observed_value,
        "violation_count": violations,
        "entity_refs": refs,
    }


def _local_rule_error_results(required_by_rule: dict[str, float]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for rule_id, _ in _LOCAL_DRC_RULES:
        results[rule_id] = _rule_result(
            status="error",
            required_um=required_by_rule.get(rule_id),
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )
    return results


def _evaluate_local_min_width(routes: list[dict[str, Any]], required_um: float) -> dict[str, Any]:
    if required_um < 0.0:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    observed_values: list[float] = []
    violations: list[str] = []
    for route in routes:
        route_id = _clean_text(route.get("route_id")) or "route"
        width_um = route.get("width_um")
        measured = float(width_um) if isinstance(width_um, (float, int)) else 0.0
        observed_values.append(measured)
        if measured < required_um:
            violations.append(f"routes:{route_id}")

    return _rule_result(
        status="fail" if violations else "pass",
        required_um=required_um,
        observed_um=min(observed_values) if observed_values else None,
        violation_count=len(_sorted_unique_strings(violations)),
        entity_refs=violations,
    )


def _evaluate_local_min_spacing(routes: list[dict[str, Any]], required_um: float) -> dict[str, Any]:
    if required_um < 0.0:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    pair_count = 0
    compared_pairs = 0
    missing_pair_width = False
    observed_spacing_um: float | None = None
    violations: list[str] = []

    for i in range(len(routes)):
        route_a = routes[i]
        for j in range(i + 1, len(routes)):
            route_b = routes[j]
            if route_a.get("layer") != route_b.get("layer"):
                continue

            pair_count += 1
            center_dist_um = _route_centerline_distance_um(route_a, route_b)
            if center_dist_um is None:
                continue

            width_a = route_a.get("width_um")
            width_b = route_b.get("width_um")
            if not isinstance(width_a, (float, int)) or not isinstance(width_b, (float, int)):
                missing_pair_width = True
                continue
            compared_pairs += 1

            w_a = float(width_a)
            w_b = float(width_b)
            edge_spacing_um = center_dist_um - 0.5 * (w_a + w_b)

            if observed_spacing_um is None or edge_spacing_um < observed_spacing_um:
                observed_spacing_um = edge_spacing_um
            if edge_spacing_um < required_um:
                left = _clean_text(route_a.get("route_id")) or f"route_{i}"
                right = _clean_text(route_b.get("route_id")) or f"route_{j}"
                pair_ref = ":".join(sorted([left, right], key=lambda t: (t.lower(), t)))
                violations.append(f"routes:{pair_ref}")

    if missing_pair_width:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    if pair_count > 0 and compared_pairs == 0:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    return _rule_result(
        status="fail" if violations else "pass",
        required_um=required_um,
        observed_um=observed_spacing_um,
        violation_count=len(_sorted_unique_strings(violations)),
        entity_refs=violations,
    )


def _evaluate_local_min_bend_radius(routes: list[dict[str, Any]], required_um: float) -> dict[str, Any]:
    if required_um < 0.0:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    observed_radius_um: float | None = None
    has_bend_evidence = False
    violations: list[str] = []

    for route in routes:
        radii = route.get("bend_radii_um") if isinstance(route.get("bend_radii_um"), list) else []
        numeric_radii = [float(r) for r in radii if isinstance(r, (float, int))]
        if not numeric_radii:
            continue
        has_bend_evidence = True

        route_min_radius = min(numeric_radii)
        if observed_radius_um is None or route_min_radius < observed_radius_um:
            observed_radius_um = route_min_radius
        if route_min_radius < required_um:
            route_id = _clean_text(route.get("route_id")) or "route"
            violations.append(f"routes:{route_id}")

    if not has_bend_evidence:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    return _rule_result(
        status="fail" if violations else "pass",
        required_um=required_um,
        observed_um=observed_radius_um,
        violation_count=len(_sorted_unique_strings(violations)),
        entity_refs=violations,
    )


def _evaluate_local_min_enclosure(routes: list[dict[str, Any]], required_um: float) -> dict[str, Any]:
    if required_um < 0.0:
        return _rule_result(
            status="error",
            required_um=required_um,
            observed_um=None,
            violation_count=0,
            entity_refs=[],
        )

    observed_values: list[float] = []
    violations: list[str] = []
    for route in routes:
        route_id = _clean_text(route.get("route_id")) or "route"
        enclosure_um = route.get("enclosure_um")
        measured = float(enclosure_um) if isinstance(enclosure_um, (float, int)) else 0.0
        observed_values.append(measured)
        if measured < required_um:
            violations.append(f"routes:{route_id}")

    return _rule_result(
        status="fail" if violations else "pass",
        required_um=required_um,
        observed_um=min(observed_values) if observed_values else None,
        violation_count=len(_sorted_unique_strings(violations)),
        entity_refs=violations,
    )


def _evaluate_local_rule_results(req: dict[str, Any]) -> dict[str, dict[str, Any]]:
    design_rules = _extract_local_design_rules(req)
    required_by_rule = _resolve_local_rule_thresholds(design_rules)

    raw_routes = _extract_local_routes_payload(req)
    if raw_routes is None:
        return _local_rule_error_results(required_by_rule)

    routes = _normalize_local_routes(raw_routes)

    return {
        "DRC.WG.MIN_WIDTH": _evaluate_local_min_width(routes, required_by_rule["DRC.WG.MIN_WIDTH"]),
        "DRC.WG.MIN_SPACING": _evaluate_local_min_spacing(
            routes,
            required_by_rule["DRC.WG.MIN_SPACING"],
        ),
        "DRC.WG.MIN_BEND_RADIUS": _evaluate_local_min_bend_radius(
            routes,
            required_by_rule["DRC.WG.MIN_BEND_RADIUS"],
        ),
        "DRC.WG.MIN_ENCLOSURE": _evaluate_local_min_enclosure(
            routes,
            required_by_rule["DRC.WG.MIN_ENCLOSURE"],
        ),
    }


def _normalize_rule_results(raw_rule_results: Any) -> dict[str, dict[str, Any]]:
    rule_results: dict[str, dict[str, Any]] = {}
    if not isinstance(raw_rule_results, dict):
        return rule_results

    for rule_id, _ in _LOCAL_DRC_RULES:
        raw_result = raw_rule_results.get(rule_id)
        if not isinstance(raw_result, dict):
            continue
        raw_refs = raw_result.get("entity_refs")
        refs = [str(ref) for ref in raw_refs] if isinstance(raw_refs, list) else []
        try:
            violation_count = int(raw_result.get("violation_count") or 0)
        except (TypeError, ValueError):
            violation_count = 0
        rule_results[rule_id] = _rule_result(
            status=_clean_text(raw_result.get("status")) or "error",
            required_um=_safe_float(raw_result.get("required_um")),
            observed_um=_safe_float(raw_result.get("observed_um"))
            if raw_result.get("observed_um") is not None
            else None,
            violation_count=violation_count,
            entity_refs=refs,
        )

    return rule_results


def _checks_from_rule_results(rule_results: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    for rule_id, rule_name in _LOCAL_DRC_RULES:
        raw_result = rule_results.get(rule_id) if isinstance(rule_results, dict) else None
        raw_status = raw_result.get("status") if isinstance(raw_result, dict) else "error"
        checks.append({"id": rule_id, "name": rule_name, "status": _normalize_status(raw_status)})
    return _normalize_checks(checks)


@dataclass(frozen=True)
class FoundryDRCSealedSummary:
    schema_version: str
    kind: str
    run_id: str
    status: str
    execution_backend: str
    started_at: str
    finished_at: str
    check_counts: dict[str, int]
    failed_check_ids: list[str]
    failed_check_names: list[str]
    rule_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    deck_fingerprint: str | None = None
    error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": self.kind,
            "run_id": self.run_id,
            "status": self.status,
            "execution_backend": self.execution_backend,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "check_counts": {
                "total": int(self.check_counts.get("total", 0)),
                "passed": int(self.check_counts.get("passed", 0)),
                "failed": int(self.check_counts.get("failed", 0)),
                "errored": int(self.check_counts.get("errored", 0)),
            },
            "failed_check_ids": list(self.failed_check_ids),
            "failed_check_names": list(self.failed_check_names),
            "rule_results": _normalize_rule_results(self.rule_results),
            "deck_fingerprint": self.deck_fingerprint,
            "error_code": self.error_code,
        }


def run_foundry_drc_sealed(
    request: dict[str, Any] | None = None,
    *,
    now_fn: Callable[[], str] = _utc_now_iso,
) -> dict[str, Any]:
    """Run a sealed foundry DRC backend and return metadata-safe summary.

    Supported request fields:
      - run_id?: str
      - backend?: str ("mock", "generic_cli", and "local_rules"/"local")
      - deck_fingerprint?: str
      - mock_result?:
          {
            status?: "pass"|"fail"|"error",
            checks?: [{id, name, status}],
          }
      - generic_cli?:
          {
            command: list[str],
            cwd?: str,
            env_allowlist?: list[str],
            timeout_s?: float,
            summary_json_path?: str,
            check_status_map?: {external_status: "pass"|"fail"|"error"},
            input_paths?: {placeholder_name: path},
            output_paths?: {placeholder_name: path},
          }
      - routes?:
          {
            routes: [{route_id, width_um, enclosure_um?, points_um, bends?}],
          }
      - pdk?:
          {
            design_rules?: {
              min_waveguide_width_um?: number,
              min_waveguide_spacing_um?: number,
              min_bend_radius_um?: number,
              min_waveguide_enclosure_um?: number,
            }
          }

    Notes:
      - Deck paths/content/rule text are intentionally ignored.
      - Output is constrained to safe metadata for API-facing summaries.
    """

    req = dict(request or {})
    started_at = now_fn()

    requested_backend = _clean_text(req.get("backend") or "mock") or "mock"
    execution_backend = (
        requested_backend if requested_backend in {"mock", "generic_cli", "local_rules", "local"} else "mock"
    )
    deck_fingerprint_raw = req.get("deck_fingerprint")
    deck_fingerprint = _clean_text(deck_fingerprint_raw) if deck_fingerprint_raw is not None else None

    backend_error_code: str | None = None
    checks: list[dict[str, str]] = []
    rule_results: dict[str, dict[str, Any]] = {}
    status: str

    if requested_backend == "mock":
        mock_result = req.get("mock_result") if isinstance(req.get("mock_result"), dict) else {}
        checks = _normalize_checks(mock_result.get("checks"))
        status = _normalize_status(mock_result.get("status"), default=_derived_status(checks))
    elif requested_backend == "generic_cli":
        raw_cli_req = req.get("generic_cli")
        cli_req = raw_cli_req if isinstance(raw_cli_req, dict) else req
        raw_check_status_map = cli_req.get("check_status_map")
        check_status_map = raw_check_status_map if isinstance(raw_check_status_map, dict) else None

        runner_result = run_generic_cli_sealed(
            command=cli_req.get("command") if isinstance(cli_req.get("command"), list) else [],
            cwd=_clean_text(cli_req.get("cwd")) or None,
            env_allowlist=cli_req.get("env_allowlist") if isinstance(cli_req.get("env_allowlist"), list) else None,
            timeout_s=float(cli_req.get("timeout_s")) if cli_req.get("timeout_s") is not None else 300.0,
            summary_json_path=_clean_text(cli_req.get("summary_json_path")) or None,
            input_paths=cli_req.get("input_paths") if isinstance(cli_req.get("input_paths"), dict) else None,
            output_paths=cli_req.get("output_paths") if isinstance(cli_req.get("output_paths"), dict) else None,
        )

        if runner_result.summary_json is not None:
            checks = _normalize_checks_with_status_map(runner_result.summary_json.get("checks"), check_status_map)
            status = _normalize_status(runner_result.summary_json.get("status"), default=_derived_status(checks))
        else:
            checks = []
            status = "error"

        if not runner_result.ok and status == "pass":
            status = "error"
        backend_error_code = runner_result.error_code
        if runner_result.ok and runner_result.summary_json is None and backend_error_code is None:
            backend_error_code = _GENERIC_CLI_SUMMARY_JSON_REQUIRED_ERROR_CODE
        if not runner_result.ok and backend_error_code is None:
            backend_error_code = "backend_execution_error"
        status, backend_error_code = _harden_generic_cli_outcome(
            status=status,
            checks=checks,
            error_code=backend_error_code,
        )
    elif requested_backend in {"local_rules", "local"}:
        rule_results = _evaluate_local_rule_results(req)
        checks = _checks_from_rule_results(rule_results)
        status = _derived_status(checks)
    else:
        # Sealed proprietary backends are not implemented in open-core.
        checks = []
        status = "error"
        backend_error_code = "backend_unavailable"

    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    errored = sum(1 for c in checks if c["status"] == "error")

    failed_checks = [c for c in checks if c["status"] == "fail"]
    failed_check_ids = [c["id"] for c in failed_checks]
    failed_check_names = [c["name"] for c in failed_checks]

    run_id = _clean_text(req.get("run_id")) or _deterministic_run_id(
        execution_backend=requested_backend,
        deck_fingerprint=deck_fingerprint,
        checks=checks,
    )

    summary = FoundryDRCSealedSummary(
        schema_version="0.1",
        kind="pic.foundry_drc_sealed_summary",
        run_id=run_id,
        status=status,
        execution_backend=execution_backend,
        started_at=started_at,
        finished_at=now_fn(),
        check_counts={
            "total": int(len(checks)),
            "passed": int(passed),
            "failed": int(failed),
            "errored": int(errored),
        },
        failed_check_ids=failed_check_ids,
        failed_check_names=failed_check_names,
        rule_results=rule_results,
        deck_fingerprint=deck_fingerprint,
        error_code=backend_error_code,
    )
    return summary.to_dict()
