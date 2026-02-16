"""Performance DRC checks (v0).

Performance DRC = physics-aware checks that act like DRC, but on performance
metrics (crosstalk, loss margins, bandwidth constraints, etc.).
"""

from __future__ import annotations

import math
import platform
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.pic.layout.verification import verify_layout_signoff_bundle
from photonstrust.components.pic.crosstalk import predict_parallel_waveguide_xt_db, recommended_min_gap_um
from photonstrust.pdk import resolve_pdk_contract
from photonstrust.reporting.performance_drc_report import render_performance_drc_html
from photonstrust.utils import hash_dict
from photonstrust.verification.layout_features import extract_parallel_waveguide_runs_from_request


def run_parallel_waveguide_crosstalk_check(
    request: dict,
    *,
    output_dir: str | Path | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the parallel-waveguide crosstalk performance check and return a report dict."""

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    model = request.get("model") if isinstance(request.get("model"), dict) else None
    corner = request.get("corner") if isinstance(request.get("corner"), dict) else None

    # Wavelength list (nm).
    wavelengths = request.get("wavelength_sweep_nm")
    if wavelengths is None:
        wavelengths = request.get("wavelength_nm")
    if isinstance(wavelengths, list):
        wavelengths_nm = [float(x) for x in wavelengths]
    else:
        wavelengths_nm = [float(wavelengths)]
    wavelengths_nm = [w for w in wavelengths_nm if w and w > 0]
    if not wavelengths_nm:
        raise ValueError("wavelength_sweep_nm (or wavelength_nm) must be provided and > 0")

    target_xt_db = request.get("target_xt_db")
    target_xt_db = float(target_xt_db) if target_xt_db is not None else None

    pdk_req = request.get("pdk")
    pdk_contract = resolve_pdk_contract(pdk_req if isinstance(pdk_req, dict) else {})
    pdk = pdk_contract["pdk"]
    pdk_rules = pdk.get("design_rules", {}) if isinstance(pdk, dict) else {}

    layout_features = None
    layout_hash = None
    loss_budget = None
    signoff_bundle = None
    drc_violations_annotated: list[dict[str, Any]] = []
    performance_violations: list[dict[str, Any]] = []

    # Optional route-level layout extraction (v0.1).
    # If routes are provided, compute the worst-case XT envelope across all
    # extracted parallel-run segments.
    routes = request.get("routes")
    if routes is not None and not isinstance(routes, list):
        raise TypeError("routes must be a list when provided")

    if isinstance(routes, list):
        layout_features = extract_parallel_waveguide_runs_from_request(request)
        parallel_runs = layout_features.get("parallel_runs", []) or []
        if not parallel_runs:
            raise ValueError("no parallel waveguide parallel-run segments were extracted from routes")

        # Physical DRC across all extracted segments.
        violations = []
        min_gap = float(pdk_rules.get("min_waveguide_gap_um", 0.0) or 0.0)
        for r in parallel_runs:
            if not isinstance(r, dict):
                continue
            try:
                g = float(r.get("gap_um"))
            except Exception:
                continue
            if g < min_gap:
                ra = str(r.get("route_a", "")).strip()
                rb = str(r.get("route_b", "")).strip()
                msg = f"{ra}:{rb} gap_um<{min_gap} (PDK min_waveguide_gap_um)"
                violations.append(msg)
                drc_violations_annotated.append(
                    {
                        "id": f"drc.min_waveguide_gap:{ra}:{rb}:{r.get('a_seg_index')}:{r.get('b_seg_index')}",
                        "source": "performance_drc.crosstalk",
                        "code": "drc.min_waveguide_gap",
                        "severity": "error",
                        "applicability": "blocking",
                        "entity_ref": f"routes:{ra}:{rb}",
                        "message": msg,
                        "location": r.get("overlap") if isinstance(r.get("overlap"), dict) else None,
                    }
                )
        drc_pass = len(violations) == 0

        # For each wavelength, find the worst (largest) XT across segments.
        points = []
        worst_xt = None
        worst_margin = None
        worst_run = None

        rec_gap = None
        if target_xt_db is not None:
            # Recommended gap across all segments (max required gap to satisfy spec).
            recs = []
            for r in parallel_runs:
                if not isinstance(r, dict):
                    continue
                L = float(r.get("parallel_length_um", 0.0) or 0.0)
                if L <= 0.0:
                    continue
                for w in wavelengths_nm:
                    try:
                        recs.append(
                            float(
                                recommended_min_gap_um(
                                    target_xt_db=float(target_xt_db),
                                    parallel_length_um=float(L),
                                    wavelength_nm=float(w),
                                    model=model,
                                    corner=corner,
                                )
                            )
                        )
                    except Exception:
                        # Leave as None if model invalid; report will still include points.
                        pass
            if recs:
                rec_gap = max(recs)

        for w in wavelengths_nm:
            xt_worst = None
            xt_worst_run = None
            for r in parallel_runs:
                if not isinstance(r, dict):
                    continue
                g = float(r.get("gap_um", 0.0) or 0.0)
                L = float(r.get("parallel_length_um", 0.0) or 0.0)
                xt = float(
                    predict_parallel_waveguide_xt_db(
                        gap_um=float(g),
                        parallel_length_um=float(L),
                        wavelength_nm=float(w),
                        model=model,
                        corner=corner,
                    )
                )
                if xt_worst is None or xt > xt_worst:
                    xt_worst = xt
                    xt_worst_run = r

            xt_worst = float(xt_worst if xt_worst is not None else 0.0)
            if worst_xt is None or xt_worst > worst_xt:
                worst_xt = xt_worst
                worst_run = xt_worst_run

            passed = None
            margin = None
            if target_xt_db is not None:
                margin = float(target_xt_db - xt_worst)
                passed = bool(margin >= 0.0)
                if worst_margin is None or margin < worst_margin:
                    worst_margin = margin

            run_ref = None
            if isinstance(xt_worst_run, dict):
                ra = str(xt_worst_run.get("route_a", "")).strip()
                rb = str(xt_worst_run.get("route_b", "")).strip()
                run_ref = f"{ra}:{rb}"

            points.append(
                {
                    "wavelength_nm": float(w),
                    "xt_db": float(xt_worst),
                    "margin_db": margin,
                    "pass": passed,
                    "worst_run_ref": run_ref,
                }
            )

        worst_xt = float(worst_xt if worst_xt is not None else 0.0)
        gap_um = float((worst_run or {}).get("gap_um", 0.0) if isinstance(worst_run, dict) else 0.0)
        parallel_length_um = float(
            (worst_run or {}).get("parallel_length_um", 0.0) if isinstance(worst_run, dict) else 0.0
        )

        layout_hash = hash_dict(
            {
                "extractor": "route_extract.parallel_runs.v0_1",
                "settings": (layout_features.get("settings") if isinstance(layout_features, dict) else None),
            }
        )
    else:
        gap_um = float(request.get("gap_um"))
        parallel_length_um = float(request.get("parallel_length_um"))

        # Simple physical DRC (design rules), even though this is performance DRC.
        violations = []
        min_gap = float(pdk_rules.get("min_waveguide_gap_um", 0.0) or 0.0)
        if gap_um < min_gap:
            msg = f"gap_um<{min_gap} (PDK min_waveguide_gap_um)"
            violations.append(msg)
            drc_violations_annotated.append(
                {
                    "id": "drc.min_waveguide_gap:scalar",
                    "source": "performance_drc.crosstalk",
                    "code": "drc.min_waveguide_gap",
                    "severity": "error",
                    "applicability": "blocking",
                    "entity_ref": "request:gap_um",
                    "message": msg,
                    "location": None,
                }
            )
        drc_pass = len(violations) == 0

        points = []
        worst_xt = None
        worst_margin = None
        rec_gap = None
        if target_xt_db is not None:
            recs = []
            for w in wavelengths_nm:
                try:
                    recs.append(
                        float(
                            recommended_min_gap_um(
                                target_xt_db=float(target_xt_db),
                                parallel_length_um=float(parallel_length_um),
                                wavelength_nm=float(w),
                                model=model,
                                corner=corner,
                            )
                        )
                    )
                except Exception:
                    # Leave as None if model invalid; report will still include points.
                    pass
            if recs:
                rec_gap = max(recs)

        for w in wavelengths_nm:
            xt = float(
                predict_parallel_waveguide_xt_db(
                    gap_um=float(gap_um),
                    parallel_length_um=float(parallel_length_um),
                    wavelength_nm=float(w),
                    model=model,
                    corner=corner,
                )
            )
            if worst_xt is None or xt > worst_xt:
                worst_xt = xt

            passed = None
            margin = None
            if target_xt_db is not None:
                margin = float(target_xt_db - xt)
                passed = bool(margin >= 0.0)
                if worst_margin is None or margin < worst_margin:
                    worst_margin = margin

            points.append(
                {
                    "wavelength_nm": float(w),
                    "xt_db": float(xt),
                    "margin_db": margin,
                    "pass": passed,
                }
            )

        worst_xt = float(worst_xt if worst_xt is not None else 0.0)

    if target_xt_db is not None:
        for p in points:
            if not isinstance(p, dict):
                continue
            if p.get("pass") is not False:
                continue
            wl = p.get("wavelength_nm")
            msg = f"xt_db exceeds target at wavelength_nm={wl}"
            performance_violations.append(
                {
                    "id": f"pdrc.crosstalk_target:{wl}",
                    "source": "performance_drc.crosstalk",
                    "code": "pdrc.crosstalk_target",
                    "severity": "error",
                    "applicability": "blocking",
                    "entity_ref": f"wavelength_nm:{wl}",
                    "message": msg,
                    "location": {"wavelength_nm": wl},
                }
            )

    if isinstance(routes, list):
        loss_cfg = request.get("loss_budget") if isinstance(request.get("loss_budget"), dict) else {}
        loss_budget = _compute_route_loss_budget(routes, settings=loss_cfg, pdk_rules=pdk_rules)
        for v in loss_budget.get("violations_annotated", []) or []:
            if isinstance(v, dict):
                performance_violations.append(v)

    signoff_cfg = request.get("signoff_bundle") if isinstance(request.get("signoff_bundle"), dict) else None
    if isinstance(signoff_cfg, dict):
        signoff_bundle = verify_layout_signoff_bundle(**signoff_cfg)
        performance_violations.extend(_annotate_signoff_violations(signoff_bundle))

    all_violations = drc_violations_annotated + performance_violations
    all_violations.sort(key=lambda v: (str(v.get("code", "")), str(v.get("id", ""))))

    has_blocking = any(_is_blocking_violation(v) for v in all_violations)
    has_reviewable = any(isinstance(v, dict) for v in all_violations)
    status = "pass"
    if has_blocking:
        status = "fail"
    elif has_reviewable:
        status = "warn"

    normalized_inputs = {
        "gap_um": float(gap_um),
        "parallel_length_um": float(parallel_length_um),
        "wavelength_sweep_nm": [float(w) for w in wavelengths_nm],
        "target_xt_db": float(target_xt_db) if target_xt_db is not None else None,
        "model": model,
        "corner": corner,
        "pdk": {
            "name": pdk.get("name"),
            "version": pdk.get("version"),
            "design_rules": pdk_rules,
        },
    }
    if layout_features is not None:
        normalized_inputs["routes"] = routes
        normalized_inputs["layout_extract"] = (
            request.get("layout_extract") if isinstance(request.get("layout_extract"), dict) else {}
        )
    if isinstance(request.get("loss_budget"), dict):
        normalized_inputs["loss_budget"] = request.get("loss_budget")
    if isinstance(signoff_cfg, dict):
        normalized_inputs["signoff_bundle"] = signoff_cfg
    input_hash = hash_dict(normalized_inputs)
    model_hash = hash_dict(
        {
            "predictor": "parallel_waveguide_xt_db.v0",
            "model_defaults": {"kappa0_per_um": 1.0e-3, "gap_decay_um": 0.2, "lambda_ref_nm": 1550.0, "lambda_exp": 1.0},
        }
    )

    run_id = str(run_id or request.get("run_id") or uuid.uuid4().hex[:12])
    report: dict[str, Any] = {
        "schema_version": "0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "check": {
            "kind": "pic.parallel_waveguide_crosstalk",
            "inputs": normalized_inputs,
        },
        "results": {
            "status": status,
            "points": points,
            "worst_xt_db": worst_xt,
            "worst_margin_db": float(worst_margin) if worst_margin is not None else None,
            "recommended_min_gap_um": float(rec_gap) if rec_gap is not None else None,
            "drc": {
                "pass": drc_pass,
                "violations": violations,
                "violations_annotated": drc_violations_annotated,
            },
            "layout": (layout_features.get("summary") if isinstance(layout_features, dict) else None)
            if layout_features is not None
            else None,
            "loss_budget": loss_budget,
            "signoff_bundle": signoff_bundle,
            "violations": all_violations,
            "violation_summary": _violation_summary(all_violations),
        },
        "artifacts": {"report_json_path": None, "report_html_path": None},
        "provenance": {
            "photonstrust_version": _photonstrust_version(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "input_hash": input_hash,
            "model_hash": model_hash,
            "layout_hash": layout_hash,
        },
    }

    if output_dir is not None:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        json_path = out / "performance_drc_report.json"
        html_path = out / "performance_drc_report.html"
        json_path.write_text(_json(report), encoding="utf-8")
        html_path.write_text(render_performance_drc_html(report), encoding="utf-8")
        report["artifacts"]["report_json_path"] = str(json_path)
        report["artifacts"]["report_html_path"] = str(html_path)

    return report


def _violation_summary(violations: list[dict[str, Any]]) -> dict[str, Any]:
    total = 0
    by_severity: dict[str, int] = {}
    by_applicability: dict[str, int] = {}
    for v in violations:
        if not isinstance(v, dict):
            continue
        total += 1
        sev = str(v.get("severity", "unknown")).strip().lower() or "unknown"
        app = str(v.get("applicability", "unknown")).strip().lower() or "unknown"
        by_severity[sev] = by_severity.get(sev, 0) + 1
        by_applicability[app] = by_applicability.get(app, 0) + 1
    return {
        "total": int(total),
        "by_severity": by_severity,
        "by_applicability": by_applicability,
        "blocking": int(sum(1 for v in violations if _is_blocking_violation(v))),
    }


def _is_blocking_violation(violation: dict[str, Any]) -> bool:
    if not isinstance(violation, dict):
        return False
    applicability = str(violation.get("applicability", "")).strip().lower()
    return applicability == "blocking"


def _annotate_signoff_violations(signoff_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(signoff_bundle, dict):
        return out
    for i, raw in enumerate(signoff_bundle.get("violations", []) or []):
        msg = str(raw)
        label = "signoff"
        if ":" in msg:
            label = str(msg.split(":", 1)[0]).strip() or "signoff"
        out.append(
            {
                "id": f"signoff:{label}:{i}",
                "source": "performance_drc.signoff_bundle",
                "code": f"signoff.{label}",
                "severity": "error",
                "applicability": "blocking",
                "entity_ref": f"signoff_check:{label}",
                "message": msg,
                "location": None,
            }
        )
    return out


def _compute_route_loss_budget(
    routes: list[dict[str, Any]],
    *,
    settings: dict[str, Any],
    pdk_rules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pdk_rules = pdk_rules if isinstance(pdk_rules, dict) else {}

    waveguide_loss_db_per_cm = _coerce_float(settings.get("waveguide_loss_db_per_cm"), 2.0)
    bend_loss_per_90deg_db = _coerce_float(settings.get("bend_loss_per_90deg_db"), 0.005)
    crossing_loss_db = _coerce_float(settings.get("crossing_loss_db"), 0.02)

    max_route_loss_db_raw = settings.get("max_route_loss_db")
    max_route_loss_db = float(max_route_loss_db_raw) if max_route_loss_db_raw is not None else None

    max_bends_raw = settings.get("max_bends_per_route")
    max_bends_per_route = int(max_bends_raw) if max_bends_raw is not None else None

    max_cross_raw = settings.get("max_crossings_per_route")
    max_crossings_per_route = int(max_cross_raw) if max_cross_raw is not None else None

    route_rows: list[dict[str, Any]] = []
    violations_annotated: list[dict[str, Any]] = []
    parsed: list[dict[str, Any]] = []
    pass_ok = True

    for i, route in enumerate(routes):
        if not isinstance(route, dict):
            pass_ok = False
            violations_annotated.append(
                {
                    "id": f"pdrc.invalid_route:{i}",
                    "source": "performance_drc.loss_budget",
                    "code": "pdrc.invalid_route",
                    "severity": "error",
                    "applicability": "blocking",
                    "entity_ref": f"route_index:{i}",
                    "message": "route entry must be an object",
                    "location": None,
                }
            )
            continue

        rid = str(route.get("route_id") or route.get("id") or f"route_{i}").strip()
        points = _route_polyline(route.get("points_um"))
        if len(points) < 2:
            pass_ok = False
            violations_annotated.append(
                {
                    "id": f"pdrc.invalid_route_points:{rid}",
                    "source": "performance_drc.loss_budget",
                    "code": "pdrc.invalid_route_points",
                    "severity": "error",
                    "applicability": "blocking",
                    "entity_ref": f"route:{rid}",
                    "message": "route requires at least 2 valid points",
                    "location": None,
                }
            )
            continue

        bends = _route_bends(points)
        parsed.append(
            {
                "route_id": rid,
                "points": points,
                "length_um": _route_length_um(points),
                "bends": bends,
                "segments": _route_segments(points),
            }
        )

    crossings = _crossing_annotations(parsed)
    crossings_by_route: dict[str, list[dict[str, Any]]] = {}
    for c in crossings:
        a = str(c.get("route_a", ""))
        b = str(c.get("route_b", ""))
        crossings_by_route.setdefault(a, []).append(c)
        crossings_by_route.setdefault(b, []).append(c)

    worst_route_loss_db = 0.0
    worst_route_id = None

    for row in parsed:
        rid = str(row["route_id"])
        length_um = float(row["length_um"])
        bends = list(row["bends"])
        crossing_rows = crossings_by_route.get(rid, [])

        propagation_loss_db = float(waveguide_loss_db_per_cm) * (length_um / 1.0e4)
        bend_loss_db = float(bend_loss_per_90deg_db) * float(len(bends))
        crossing_loss_total_db = float(crossing_loss_db) * float(len(crossing_rows))
        route_loss_db = propagation_loss_db + bend_loss_db + crossing_loss_total_db

        if route_loss_db > worst_route_loss_db:
            worst_route_loss_db = float(route_loss_db)
            worst_route_id = rid

        route_pass = True
        if max_route_loss_db is not None and route_loss_db > float(max_route_loss_db):
            route_pass = False
            pass_ok = False
            violations_annotated.append(
                {
                    "id": f"pdrc.route_loss_budget:{rid}",
                    "source": "performance_drc.loss_budget",
                    "code": "pdrc.route_loss_budget",
                    "severity": "error",
                    "applicability": "blocking",
                    "entity_ref": f"route:{rid}",
                    "message": (
                        f"route_loss_db={route_loss_db:.6g} exceeds "
                        f"max_route_loss_db={float(max_route_loss_db):.6g}"
                    ),
                    "location": {
                        "route_id": rid,
                        "a_um": [row["points"][0][0], row["points"][0][1]],
                        "b_um": [row["points"][-1][0], row["points"][-1][1]],
                    },
                }
            )

        if max_bends_per_route is not None and len(bends) > int(max_bends_per_route):
            route_pass = False
            violations_annotated.append(
                {
                    "id": f"pdrc.route_bend_count:{rid}",
                    "source": "performance_drc.loss_budget",
                    "code": "pdrc.route_bend_count",
                    "severity": "warning",
                    "applicability": "reviewable",
                    "entity_ref": f"route:{rid}",
                    "message": (
                        f"bend_count={len(bends)} exceeds "
                        f"max_bends_per_route={int(max_bends_per_route)}"
                    ),
                    "location": {
                        "route_id": rid,
                        "bend_vertices_um": [[b["x_um"], b["y_um"]] for b in bends],
                    },
                }
            )

        if max_crossings_per_route is not None and len(crossing_rows) > int(max_crossings_per_route):
            route_pass = False
            violations_annotated.append(
                {
                    "id": f"pdrc.route_crossing_count:{rid}",
                    "source": "performance_drc.loss_budget",
                    "code": "pdrc.route_crossing_count",
                    "severity": "warning",
                    "applicability": "reviewable",
                    "entity_ref": f"route:{rid}",
                    "message": (
                        f"crossing_count={len(crossing_rows)} exceeds "
                        f"max_crossings_per_route={int(max_crossings_per_route)}"
                    ),
                    "location": {
                        "route_id": rid,
                        "crossing_points_um": [[c.get("x_um"), c.get("y_um")] for c in crossing_rows],
                    },
                }
            )

        risk_level = "low"
        if max_route_loss_db is not None:
            margin = float(max_route_loss_db) - route_loss_db
            if margin < 0.0:
                risk_level = "high"
            elif margin < 0.2:
                risk_level = "medium"
        elif route_loss_db > 3.0:
            risk_level = "high"
        elif route_loss_db > 1.0:
            risk_level = "medium"

        route_rows.append(
            {
                "route_id": rid,
                "length_um": length_um,
                "bend_count": int(len(bends)),
                "crossing_count": int(len(crossing_rows)),
                "propagation_loss_db": float(propagation_loss_db),
                "bend_loss_db": float(bend_loss_db),
                "crossing_loss_db": float(crossing_loss_total_db),
                "route_loss_db": float(route_loss_db),
                "risk_level": risk_level,
                "pass": bool(route_pass),
            }
        )

    route_rows.sort(key=lambda r: str(r.get("route_id", "")).lower())
    violations_annotated.sort(key=lambda v: (str(v.get("code", "")), str(v.get("id", ""))))
    violations = [str(v.get("message", "")) for v in violations_annotated if isinstance(v, dict)]

    return {
        "pass": bool(pass_ok),
        "settings": {
            "waveguide_loss_db_per_cm": float(waveguide_loss_db_per_cm),
            "bend_loss_per_90deg_db": float(bend_loss_per_90deg_db),
            "crossing_loss_db": float(crossing_loss_db),
            "max_route_loss_db": float(max_route_loss_db) if max_route_loss_db is not None else None,
            "max_bends_per_route": int(max_bends_per_route) if max_bends_per_route is not None else None,
            "max_crossings_per_route": int(max_crossings_per_route) if max_crossings_per_route is not None else None,
            "pdk_min_bend_radius_um": float(pdk_rules.get("min_bend_radius_um", 0.0) or 0.0),
        },
        "route_count": int(len(route_rows)),
        "worst_route_id": worst_route_id,
        "worst_route_loss_db": float(worst_route_loss_db),
        "routes": route_rows,
        "crossings": crossings,
        "violations": violations,
        "violations_annotated": violations_annotated,
    }


def _coerce_float(value: Any, default: float) -> float:
    try:
        out = float(value)
        if not math.isfinite(out):
            return float(default)
        return out
    except Exception:
        return float(default)


def _route_polyline(points: Any) -> list[tuple[float, float]]:
    if not isinstance(points, list):
        return []
    out: list[tuple[float, float]] = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            continue
        try:
            x = float(p[0])
            y = float(p[1])
        except Exception:
            continue
        if out and abs(x - out[-1][0]) <= 1e-12 and abs(y - out[-1][1]) <= 1e-12:
            continue
        out.append((x, y))
    return out


def _route_length_um(points: list[tuple[float, float]]) -> float:
    total = 0.0
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        total += math.hypot(x1 - x0, y1 - y0)
    return float(total)


def _route_bends(points: list[tuple[float, float]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if len(points) < 3:
        return out
    for i in range(1, len(points) - 1):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx1, dy1 = (x1 - x0), (y1 - y0)
        dx2, dy2 = (x2 - x1), (y2 - y1)
        if abs(dx1) <= 1e-12 and abs(dy2) <= 1e-12:
            out.append({"index": i, "x_um": x1, "y_um": y1})
        elif abs(dy1) <= 1e-12 and abs(dx2) <= 1e-12:
            out.append({"index": i, "x_um": x1, "y_um": y1})
    return out


def _route_segments(points: list[tuple[float, float]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(len(points) - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        if abs(y1 - y0) <= 1e-12 and abs(x1 - x0) > 1e-12:
            out.append(
                {
                    "seg_index": i,
                    "orientation": "h",
                    "x0": min(x0, x1),
                    "x1": max(x0, x1),
                    "y0": y0,
                    "y1": y1,
                }
            )
        elif abs(x1 - x0) <= 1e-12 and abs(y1 - y0) > 1e-12:
            out.append(
                {
                    "seg_index": i,
                    "orientation": "v",
                    "x0": x0,
                    "x1": x1,
                    "y0": min(y0, y1),
                    "y1": max(y0, y1),
                }
            )
    return out


def _between_strict(x: float, a: float, b: float, tol: float = 1e-12) -> bool:
    lo = min(a, b) + tol
    hi = max(a, b) - tol
    return lo <= x <= hi


def _crossing_annotations(parsed_routes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i in range(len(parsed_routes)):
        for j in range(i + 1, len(parsed_routes)):
            ra = parsed_routes[i]
            rb = parsed_routes[j]
            for sa in ra.get("segments", []) or []:
                for sb in rb.get("segments", []) or []:
                    if not isinstance(sa, dict) or not isinstance(sb, dict):
                        continue
                    oa = str(sa.get("orientation", ""))
                    ob = str(sb.get("orientation", ""))
                    if oa == ob:
                        continue

                    if oa == "h" and ob == "v":
                        x = float(sb.get("x0", 0.0) or 0.0)
                        y = float(sa.get("y0", 0.0) or 0.0)
                        if not (_between_strict(x, float(sa.get("x0", 0.0) or 0.0), float(sa.get("x1", 0.0) or 0.0))):
                            continue
                        if not (_between_strict(y, float(sb.get("y0", 0.0) or 0.0), float(sb.get("y1", 0.0) or 0.0))):
                            continue
                    elif oa == "v" and ob == "h":
                        x = float(sa.get("x0", 0.0) or 0.0)
                        y = float(sb.get("y0", 0.0) or 0.0)
                        if not (_between_strict(x, float(sb.get("x0", 0.0) or 0.0), float(sb.get("x1", 0.0) or 0.0))):
                            continue
                        if not (_between_strict(y, float(sa.get("y0", 0.0) or 0.0), float(sa.get("y1", 0.0) or 0.0))):
                            continue
                    else:
                        continue

                    out.append(
                        {
                            "route_a": str(ra.get("route_id", "")),
                            "route_b": str(rb.get("route_id", "")),
                            "a_seg_index": int(sa.get("seg_index", 0) or 0),
                            "b_seg_index": int(sb.get("seg_index", 0) or 0),
                            "x_um": float(x),
                            "y_um": float(y),
                        }
                    )

    out.sort(
        key=lambda c: (
            str(c.get("route_a", "")).lower(),
            str(c.get("route_b", "")).lower(),
            float(c.get("x_um", 0.0)),
            float(c.get("y_um", 0.0)),
        )
    )
    return out


def _json(payload: dict) -> str:
    import json

    return json.dumps(payload, indent=2)


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except Exception:
            return None
    return None
