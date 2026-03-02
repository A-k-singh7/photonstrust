"""Foundry PEX sealed runner seam (metadata-safe summary only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Any, Callable

from photonstrust.layout.pic.generic_cli_sealed_runner import run_generic_cli_backend
from photonstrust.utils import hash_dict

_ALLOWED_CHECK_STATUSES = {"pass", "fail", "error"}
_ALLOWED_RUN_STATUSES = {"pass", "fail", "error"}
_GENERIC_CLI_EMPTY_CHECKS_ERROR_CODE = "generic_cli_empty_checks"
_GENERIC_CLI_STATUS_CHECKS_CONFLICT_ERROR_CODE = "generic_cli_status_checks_conflict"
_LOCAL_PEX_MISSING_PDK_RULES_ERROR_CODE = "local_pex_missing_required_pdk_rules"
_LOCAL_PEX_CHECKS: tuple[tuple[str, str], ...] = (
    ("PEX.RC.BOUNDS", "rc_bounds"),
    ("PEX.COUPLING.BOUNDS", "coupling_bounds"),
    ("PEX.NET.COVERAGE", "net_coverage"),
)
_LOCAL_PEX_DEFAULT_RULES: dict[str, float] = {
    "resistance_ohm_per_um": 0.02,
    "capacitance_ff_per_um": 0.002,
    "max_total_resistance_ohm": 5000.0,
    "max_total_capacitance_ff": 10000.0,
    "max_rc_delay_ps": 50000.0,
    "max_coupling_coeff": 0.1,
    "min_net_coverage_ratio": 1.0,
}
_LOCAL_PEX_RULE_ALIASES: dict[str, tuple[str, ...]] = {
    "resistance_ohm_per_um": ("resistance_ohm_per_um", "wg_resistance_ohm_per_um"),
    "capacitance_ff_per_um": ("capacitance_ff_per_um", "wg_capacitance_ff_per_um"),
    "max_total_resistance_ohm": ("max_total_resistance_ohm", "max_resistance_ohm"),
    "max_total_capacitance_ff": ("max_total_capacitance_ff", "max_capacitance_ff"),
    "max_rc_delay_ps": ("max_rc_delay_ps", "max_rc_ps"),
    "max_coupling_coeff": ("max_coupling_coeff", "max_coupling_ratio"),
    "min_net_coverage_ratio": ("min_net_coverage_ratio",),
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _safe_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    return parsed


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


def _extract_local_routes_payload(req: dict[str, Any]) -> list[Any] | None:
    raw_routes = req.get("routes")
    if isinstance(raw_routes, dict) and isinstance(raw_routes.get("routes"), list):
        return list(raw_routes.get("routes"))
    if isinstance(raw_routes, list):
        return list(raw_routes)

    raw_mock_result = req.get("mock_result")
    if isinstance(raw_mock_result, dict):
        mock_routes = raw_mock_result.get("routes")
        if isinstance(mock_routes, dict) and isinstance(mock_routes.get("routes"), list):
            return list(mock_routes.get("routes"))
        if isinstance(mock_routes, list):
            return list(mock_routes)
    return None


def _extract_local_graph_payload(req: dict[str, Any]) -> dict[str, Any] | None:
    raw_graph = req.get("graph")
    if isinstance(raw_graph, dict):
        return dict(raw_graph)

    raw_mock_result = req.get("mock_result")
    if isinstance(raw_mock_result, dict) and isinstance(raw_mock_result.get("graph"), dict):
        return dict(raw_mock_result.get("graph"))
    return None


def _resolve_local_pex_rules(req: dict[str, Any]) -> tuple[dict[str, float], list[str]]:
    req_pex_rules = req.get("pex_rules") if isinstance(req.get("pex_rules"), dict) else {}
    pdk = req.get("pdk") if isinstance(req.get("pdk"), dict) else {}
    pdk_pex_rules = pdk.get("pex_rules") if isinstance(pdk.get("pex_rules"), dict) else {}
    pdk_design_rules = pdk.get("design_rules") if isinstance(pdk.get("design_rules"), dict) else {}
    sources = [req_pex_rules, pdk_pex_rules, pdk_design_rules]

    out: dict[str, float] = {}
    missing_explicit: list[str] = []
    for canonical_key, aliases in _LOCAL_PEX_RULE_ALIASES.items():
        value: float | None = None
        for source in sources:
            for alias in aliases:
                if alias in source:
                    value = _safe_float(source.get(alias))
                    break
            if value is not None:
                break

        if value is None:
            default_value = _safe_float(_LOCAL_PEX_DEFAULT_RULES.get(canonical_key))
            if default_value is not None:
                value = default_value
            missing_explicit.append(canonical_key)

        if value is None:
            value = 0.0
        out[canonical_key] = float(value)

    return out, sorted(set(missing_explicit), key=lambda t: t.lower())


def _polyline_length_um(raw_points: Any) -> float | None:
    if not isinstance(raw_points, list):
        return None
    points: list[tuple[float, float]] = []
    for raw in raw_points:
        if not isinstance(raw, (list, tuple)) or len(raw) < 2:
            continue
        x = _safe_float(raw[0])
        y = _safe_float(raw[1])
        if x is None or y is None:
            continue
        points.append((float(x), float(y)))
    if len(points) < 2:
        return None

    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i - 1][0]
        dy = points[i][1] - points[i - 1][1]
        total += math.hypot(dx, dy)
    return total


def _edge_key_from_route(route: dict[str, Any], *, fallback: str) -> str:
    source = route.get("source") if isinstance(route.get("source"), dict) else {}
    edge = source.get("edge") if isinstance(source.get("edge"), dict) else {}
    from_node = _clean_text(edge.get("from") or route.get("from"))
    to_node = _clean_text(edge.get("to") or route.get("to"))
    from_port = _clean_text(edge.get("from_port") or route.get("from_port"))
    to_port = _clean_text(edge.get("to_port") or route.get("to_port"))
    if from_node and to_node:
        if from_port or to_port:
            return f"{from_node}.{from_port}->{to_node}.{to_port}"
        return f"{from_node}->{to_node}"
    return fallback


def _normalize_local_routes(raw_routes: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(raw_routes):
        if not isinstance(raw, dict):
            continue
        route_id = _clean_text(raw.get("route_id")) or f"route_{i}"
        length_um = _safe_float(raw.get("length_um"))
        if length_um is None:
            length_um = _polyline_length_um(raw.get("points_um"))

        resistance_ohm = _safe_float(raw.get("resistance_ohm"))
        capacitance_ff = _safe_float(raw.get("capacitance_ff"))
        coupling_coeff = _safe_float(raw.get("coupling_coeff"))
        if coupling_coeff is None:
            coupling_db = _safe_float(raw.get("coupling_db"))
            if coupling_db is not None:
                coupling_coeff = 10.0 ** (float(coupling_db) / 20.0)

        out.append(
            {
                "route_id": route_id,
                "edge_key": _edge_key_from_route(raw, fallback=route_id),
                "length_um": length_um,
                "resistance_ohm": resistance_ohm,
                "capacitance_ff": capacitance_ff,
                "coupling_coeff": coupling_coeff,
            }
        )
    return out


def _evaluate_local_rc_bounds(routes: list[dict[str, Any]], rules: dict[str, float]) -> str:
    if not routes:
        return "error"

    res_per_um = float(rules["resistance_ohm_per_um"])
    cap_per_um = float(rules["capacitance_ff_per_um"])
    max_r = float(rules["max_total_resistance_ohm"])
    max_c = float(rules["max_total_capacitance_ff"])
    max_rc_ps = float(rules["max_rc_delay_ps"])

    total_r = 0.0
    total_c = 0.0
    unknown_count = 0
    valid_count = 0
    for route in routes:
        length = _safe_float(route.get("length_um"))
        resistance = _safe_float(route.get("resistance_ohm"))
        capacitance = _safe_float(route.get("capacitance_ff"))
        if resistance is None and length is not None:
            resistance = float(length) * res_per_um
        if capacitance is None and length is not None:
            capacitance = float(length) * cap_per_um
        if resistance is None or capacitance is None or resistance < 0 or capacitance < 0:
            unknown_count += 1
            continue

        valid_count += 1
        total_r += float(resistance)
        total_c += float(capacitance)

    if valid_count <= 0 or unknown_count > 0:
        return "error"

    rc_delay_ps = total_r * total_c * 1e-3
    if total_r > max_r or total_c > max_c or rc_delay_ps > max_rc_ps:
        return "fail"
    return "pass"


def _evaluate_local_coupling_bounds(routes: list[dict[str, Any]], rules: dict[str, float]) -> str:
    if not routes:
        return "error"

    max_coeff = float(rules["max_coupling_coeff"])
    observed: list[float] = []
    for route in routes:
        coeff = _safe_float(route.get("coupling_coeff"))
        if coeff is None:
            continue
        if coeff < 0:
            return "error"
        observed.append(float(coeff))

    if not observed:
        return "error"
    if max(observed) > max_coeff:
        return "fail"
    return "pass"


def _evaluate_local_net_coverage(
    routes: list[dict[str, Any]],
    graph: dict[str, Any] | None,
    rules: dict[str, float],
) -> str:
    min_ratio = float(rules["min_net_coverage_ratio"])
    if min_ratio <= 0:
        return "error"

    extracted_keys = {_clean_text(route.get("edge_key")) for route in routes if _clean_text(route.get("edge_key"))}
    extracted_nets = len(extracted_keys)

    expected_nets = 0
    if isinstance(graph, dict):
        raw_edges = graph.get("edges")
        if isinstance(raw_edges, list):
            expected_nets = sum(1 for edge in raw_edges if isinstance(edge, dict))
    if expected_nets <= 0:
        expected_nets = extracted_nets
    if expected_nets <= 0:
        return "error"

    coverage_ratio = float(extracted_nets) / float(expected_nets)
    if coverage_ratio + 1e-12 < min_ratio:
        return "fail"
    return "pass"


def _evaluate_local_pex_checks(req: dict[str, Any]) -> tuple[list[dict[str, str]], list[str]]:
    raw_routes = _extract_local_routes_payload(req)
    graph = _extract_local_graph_payload(req)
    routes = _normalize_local_routes(raw_routes) if isinstance(raw_routes, list) else []
    rules, missing_explicit_rule_ids = _resolve_local_pex_rules(req)

    if bool(req.get("require_explicit_pex_rules")) and missing_explicit_rule_ids:
        return (
            _normalize_checks(
                [
                    {"id": check_id, "name": check_name, "status": "error"}
                    for check_id, check_name in _LOCAL_PEX_CHECKS
                ]
            ),
            missing_explicit_rule_ids,
        )

    statuses = {
        "PEX.RC.BOUNDS": _evaluate_local_rc_bounds(routes, rules),
        "PEX.COUPLING.BOUNDS": _evaluate_local_coupling_bounds(routes, rules),
        "PEX.NET.COVERAGE": _evaluate_local_net_coverage(routes, graph, rules),
    }
    checks = _normalize_checks(
        [
            {"id": check_id, "name": check_name, "status": statuses.get(check_id, "error")}
            for check_id, check_name in _LOCAL_PEX_CHECKS
        ]
    )
    return checks, missing_explicit_rule_ids


def _deterministic_run_id(*, execution_backend: str, deck_fingerprint: str | None, checks: list[dict[str, str]]) -> str:
    seed = {
        "execution_backend": execution_backend,
        "deck_fingerprint": deck_fingerprint,
        "checks": checks,
    }
    return f"pexs_{hash_dict(seed)[:12]}"


@dataclass(frozen=True)
class FoundryPEXSealedSummary:
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
            "deck_fingerprint": self.deck_fingerprint,
            "error_code": self.error_code,
        }


def run_foundry_pex_sealed(
    request: dict[str, Any] | None = None,
    *,
    now_fn: Callable[[], str] = _utc_now_iso,
) -> dict[str, Any]:
    req = dict(request or {})
    started_at = now_fn()

    requested_backend = _clean_text(req.get("backend") or "mock") or "mock"
    execution_backend = requested_backend if requested_backend in {"mock", "generic_cli", "local_pex", "local"} else "mock"
    deck_fingerprint_raw = req.get("deck_fingerprint")
    deck_fingerprint = _clean_text(deck_fingerprint_raw) if deck_fingerprint_raw is not None else None

    backend_error_code: str | None = None
    checks: list[dict[str, str]] = []
    status: str

    if requested_backend == "mock":
        raw_mock_result = req.get("mock_result")
        if isinstance(raw_mock_result, dict):
            mock_result: dict[str, Any] = dict(raw_mock_result)
        else:
            mock_result = {}
        checks = _normalize_checks(mock_result.get("checks"))
        status = _normalize_status(mock_result.get("status"), default=_derived_status(checks))
    elif requested_backend == "generic_cli":
        generic_result = run_generic_cli_backend(
            req,
            normalize_status=_normalize_status,
            normalize_checks=_normalize_checks,
            derive_status=_derived_status,
        )
        checks = generic_result.checks
        status = generic_result.status
        backend_error_code = generic_result.error_code
        status, backend_error_code = _harden_generic_cli_outcome(
            status=status,
            checks=checks,
            error_code=backend_error_code,
        )
    elif requested_backend in {"local_pex", "local"}:
        checks, missing_explicit_rule_ids = _evaluate_local_pex_checks(req)
        status = _derived_status(checks)
        if bool(req.get("require_explicit_pex_rules")) and missing_explicit_rule_ids:
            backend_error_code = _LOCAL_PEX_MISSING_PDK_RULES_ERROR_CODE
    else:
        checks = []
        status = "error"
        backend_error_code = "unsupported_backend"

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

    summary = FoundryPEXSealedSummary(
        schema_version="0.1",
        kind="pic.foundry_pex_sealed_summary",
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
        deck_fingerprint=deck_fingerprint,
        error_code=backend_error_code,
    )
    return summary.to_dict()
