"""Optional QuTiP parity lane for PhotonTrust.

This script compares a focused set of analytic vs QuTiP-backed paths for:
- emitter model outputs
- memory model outputs
- end-to-end BBM92 point estimates (via source backend switch)

By default the lane is non-breaking:
- if QuTiP is missing, the script reports "skipped" and exits 0
- if parity deltas are large, the script reports findings and exits 0

Use --strict to make this lane fail on missing QuTiP or threshold breaches.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from photonstrust.physics.emitter import get_emitter_stats
from photonstrust.physics.memory import MemoryStats, simulate_memory
from photonstrust.qkd import compute_point


THRESHOLDS: list[dict[str, Any]] = [
    {
        "category": "emitter",
        "metric": "g2_0",
        "delta_kind": "abs",
        "limit": 0.10,
        "reason": "Large g2 drift materially changes multi-photon probability.",
    },
    {
        "category": "emitter",
        "metric": "emission_prob",
        "delta_kind": "rel",
        "limit": 0.20,
        "reason": "Emission probability should stay within a coarse trend band.",
    },
    {
        "category": "memory",
        "metric": "fidelity",
        "delta_kind": "abs",
        "limit": 0.05,
        "reason": "Memory fidelity parity should be within 5 percentage points.",
    },
    {
        "category": "qkd",
        "metric": "qber_total",
        "delta_kind": "abs",
        "limit": 0.05,
        "reason": "QBER drift beyond 5 points is protocol-significant.",
    },
    {
        "category": "qkd",
        "metric": "key_rate_bps",
        "delta_kind": "rel",
        "limit": 0.50,
        "reason": "Key-rate parity should be within 50% for this focused smoke lane.",
    },
]


def _compare_scalars(analytic: float, qutip: float) -> dict[str, float | None]:
    analytic_v = float(analytic)
    qutip_v = float(qutip)
    abs_delta = abs(qutip_v - analytic_v)
    rel_delta = None
    if abs(analytic_v) > 1e-12:
        rel_delta = abs_delta / abs(analytic_v)
    return {
        "analytic": analytic_v,
        "qutip": qutip_v,
        "abs_delta": abs_delta,
        "rel_delta": rel_delta,
    }


def _emitter_cases() -> list[dict[str, Any]]:
    base = {
        "type": "emitter_cavity",
        "seed": 123,
        "radiative_lifetime_ns": 1.0,
        "purcell_factor": 5.0,
        "dephasing_rate_per_ns": 0.5,
        "drive_strength": 0.05,
        "pulse_window_ns": 5.0,
        "g2_0": 0.02,
    }

    cases = [
        {"case_id": "emitter_steady_state", "overrides": {"emission_mode": "steady_state"}},
        {
            "case_id": "emitter_transient",
            "overrides": {
                "emission_mode": "transient",
                "drive_strength": 0.12,
                "transient_steps": 96,
            },
        },
    ]

    out: list[dict[str, Any]] = []
    for item in cases:
        analytic_cfg = deepcopy(base)
        analytic_cfg.update(item["overrides"])
        analytic_cfg["physics_backend"] = "analytic"

        qutip_cfg = deepcopy(base)
        qutip_cfg.update(item["overrides"])
        qutip_cfg["physics_backend"] = "qutip"

        analytic = get_emitter_stats(analytic_cfg)
        qutip = get_emitter_stats(qutip_cfg)

        out.append(
            {
                "category": "emitter",
                "case_id": item["case_id"],
                "qutip_backend_used": qutip.get("backend"),
                "fallback_reason": qutip.get("fallback_reason"),
                "metrics": {
                    "emission_prob": _compare_scalars(analytic["emission_prob"], qutip["emission_prob"]),
                    "g2_0": _compare_scalars(analytic["g2_0"], qutip["g2_0"]),
                    "p_multi": _compare_scalars(analytic["p_multi"], qutip["p_multi"]),
                },
            }
        )
    return out


def _memory_to_dict(stats: MemoryStats) -> dict[str, Any]:
    return asdict(stats)


def _memory_cases() -> list[dict[str, Any]]:
    base = {
        "t1_ms": 50,
        "t2_ms": 10,
        "retrieval_efficiency": 0.8,
        "store_efficiency": 1.0,
        "seed": 7,
        "n_trajectories": 200,
    }
    waits_ns = [1e3, 1e6, 1e9]

    out: list[dict[str, Any]] = []
    for wait in waits_ns:
        analytic_cfg = deepcopy(base)
        analytic_cfg["physics_backend"] = "analytic"

        qutip_cfg = deepcopy(base)
        qutip_cfg["physics_backend"] = "qutip"

        analytic = _memory_to_dict(simulate_memory(analytic_cfg, wait))
        qutip = _memory_to_dict(simulate_memory(qutip_cfg, wait))

        out.append(
            {
                "category": "memory",
                "case_id": f"memory_wait_ns_{int(wait)}",
                "wait_time_ns": float(wait),
                "qutip_backend_used": qutip.get("backend"),
                "fallback_reason": None if qutip.get("backend") == "qutip" else "qutip path fallback",
                "metrics": {
                    "p_retrieve": _compare_scalars(analytic["p_retrieve"], qutip["p_retrieve"]),
                    "fidelity": _compare_scalars(analytic["fidelity"], qutip["fidelity"]),
                    "variance_fidelity": _compare_scalars(
                        analytic["variance_fidelity"],
                        qutip["variance_fidelity"],
                    ),
                },
            }
        )
    return out


def _qkd_cases() -> list[dict[str, Any]]:
    scenario_base = {
        "source": {
            "type": "emitter_cavity",
            "rep_rate_mhz": 100,
            "collection_efficiency": 0.35,
            "coupling_efficiency": 0.6,
            "radiative_lifetime_ns": 1.0,
            "purcell_factor": 5,
            "dephasing_rate_per_ns": 0.5,
            "g2_0": 0.02,
            "pulse_window_ns": 5.0,
            "seed": 123,
        },
        "channel": {
            "fiber_loss_db_per_km": 0.2,
            "connector_loss_db": 1.5,
            "dispersion_ps_per_km": 5,
        },
        "detector": {
            "class": "snspd",
            "pde": 0.3,
            "dark_counts_cps": 100,
            "jitter_ps_fwhm": 30,
            "dead_time_ns": 100,
            "afterpulsing_prob": 0.001,
        },
        "timing": {"sync_drift_ps_rms": 10, "coincidence_window_ps": 200},
        "protocol": {
            "name": "BBM92",
            "sifting_factor": 0.5,
            "ec_efficiency": 1.16,
        },
    }

    out: list[dict[str, Any]] = []
    for distance_km in [10.0, 25.0, 50.0]:
        analytic_scenario = deepcopy(scenario_base)
        analytic_scenario["source"]["physics_backend"] = "analytic"

        qutip_scenario = deepcopy(scenario_base)
        qutip_scenario["source"]["physics_backend"] = "qutip"

        analytic = asdict(compute_point(analytic_scenario, distance_km))
        qutip = asdict(compute_point(qutip_scenario, distance_km))

        qutip_source_stats = get_emitter_stats(qutip_scenario["source"])

        out.append(
            {
                "category": "qkd",
                "case_id": f"bbm92_distance_km_{int(distance_km)}",
                "distance_km": float(distance_km),
                "qutip_backend_used": qutip_source_stats.get("backend"),
                "fallback_reason": qutip_source_stats.get("fallback_reason"),
                "metrics": {
                    "key_rate_bps": _compare_scalars(analytic["key_rate_bps"], qutip["key_rate_bps"]),
                    "qber_total": _compare_scalars(analytic["qber_total"], qutip["qber_total"]),
                    "entanglement_rate_hz": _compare_scalars(
                        analytic["entanglement_rate_hz"],
                        qutip["entanglement_rate_hz"],
                    ),
                    "p_pair": _compare_scalars(analytic["p_pair"], qutip["p_pair"]),
                },
            }
        )
    return out


def _max_delta(records: list[dict[str, Any]], metric: str, delta_kind: str) -> float:
    values: list[float] = []
    for rec in records:
        metric_rec = rec.get("metrics", {}).get(metric)
        if not metric_rec:
            continue
        value = metric_rec.get(f"{delta_kind}_delta")
        if value is None:
            continue
        values.append(float(value))
    if not values:
        return 0.0
    return max(values)


def _evaluate_thresholds(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    breaches: list[dict[str, Any]] = []
    by_category: dict[str, list[dict[str, Any]]] = {}
    for rec in records:
        by_category.setdefault(rec["category"], []).append(rec)

    for spec in THRESHOLDS:
        category_records = by_category.get(spec["category"], [])
        peak = _max_delta(category_records, spec["metric"], spec["delta_kind"])
        if peak > float(spec["limit"]):
            breaches.append(
                {
                    "category": spec["category"],
                    "metric": spec["metric"],
                    "delta_kind": spec["delta_kind"],
                    "observed": peak,
                    "limit": float(spec["limit"]),
                    "reason": spec["reason"],
                }
            )
    return breaches


def _collect_fallbacks(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rec in records:
        reason = rec.get("fallback_reason")
        if reason:
            out.append(
                {
                    "category": rec.get("category"),
                    "case_id": rec.get("case_id"),
                    "reason": reason,
                }
            )
    return out


def _render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# QuTiP parity lane report")
    lines.append("")
    lines.append(f"- Generated: {report['generated_at']}")
    lines.append(f"- Python: {report['environment']['python']}")
    lines.append(f"- QuTiP available: {report['environment']['qutip_available']}")
    lines.append(f"- QuTiP version: {report['environment'].get('qutip_version')}")
    lines.append(f"- Strict mode: {report['strict_mode']}")
    lines.append("")

    if report["status"] == "skipped":
        lines.append("QuTiP is not installed; parity comparison skipped (non-breaking lane).")
        lines.append("")
        lines.append("Recommendation: **NO-GO** for requiring QuTiP in mandatory CI.")
        return "\n".join(lines)

    lines.append("## Threshold breaches")
    breaches = report["summary"].get("threshold_breaches", [])
    if not breaches:
        lines.append("- None")
    else:
        for b in breaches:
            lines.append(
                f"- {b['category']}.{b['metric']} ({b['delta_kind']}): observed={b['observed']:.6g}, "
                f"limit={b['limit']:.6g} — {b['reason']}"
            )
    lines.append("")

    lines.append("## Focused deltas (max by metric)")
    max_deltas = report["summary"].get("max_deltas", {})
    for category, metrics in max_deltas.items():
        lines.append(f"- {category}")
        for metric_name, value in metrics.items():
            abs_d = value.get("abs_delta")
            rel_d = value.get("rel_delta")
            if rel_d is None:
                lines.append(f"  - {metric_name}: abs={abs_d:.6g}, rel=n/a")
            else:
                lines.append(f"  - {metric_name}: abs={abs_d:.6g}, rel={rel_d:.6g}")
    lines.append("")

    recommendation = report["recommendation"]
    lines.append("## Recommendation")
    lines.append(f"- Decision: **{recommendation['decision'].upper()}**")
    lines.append(f"- Rationale: {recommendation['rationale']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run optional QuTiP parity lane.")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("results/qutip_parity/qutip_parity_report.json"),
        help="Path to write machine-readable parity report.",
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("results/qutip_parity/qutip_parity_report.md"),
        help="Path to write markdown parity summary.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail when QuTiP is missing or parity thresholds are breached.",
    )
    args = parser.parse_args()

    qutip_spec = importlib.util.find_spec("qutip")
    qutip_available = qutip_spec is not None
    qutip_version = None
    if qutip_available:
        qutip_mod = importlib.import_module("qutip")
        qutip_version = str(getattr(qutip_mod, "__version__", "unknown"))

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_mode": bool(args.strict),
        "status": "ok",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "qutip_available": bool(qutip_available),
            "qutip_version": qutip_version,
        },
        "records": [],
        "summary": {},
        "recommendation": {},
    }

    if not qutip_available:
        report["status"] = "skipped"
        report["summary"] = {
            "threshold_breaches": [],
            "fallbacks": [],
            "max_deltas": {},
        }
        report["recommendation"] = {
            "decision": "no-go",
            "rationale": "QuTiP not installed in baseline environment; keep lane optional/non-blocking.",
            "require_qutip_in_ci": False,
        }
    else:
        records = _emitter_cases() + _memory_cases() + _qkd_cases()
        fallbacks = _collect_fallbacks(records)
        breaches = _evaluate_thresholds(records)

        max_deltas: dict[str, dict[str, dict[str, float | None]]] = {}
        for rec in records:
            category = str(rec["category"])
            max_deltas.setdefault(category, {})
            for metric_name, values in rec.get("metrics", {}).items():
                slot = max_deltas[category].setdefault(
                    metric_name,
                    {
                        "abs_delta": 0.0,
                        "rel_delta": None,
                    },
                )
                abs_delta = float(values.get("abs_delta", 0.0) or 0.0)
                rel_delta = values.get("rel_delta")
                if abs_delta > float(slot["abs_delta"]):
                    slot["abs_delta"] = abs_delta
                if rel_delta is not None:
                    rel_v = float(rel_delta)
                    if slot["rel_delta"] is None or rel_v > float(slot["rel_delta"]):
                        slot["rel_delta"] = rel_v

        report["records"] = records
        report["summary"] = {
            "threshold_breaches": breaches,
            "fallbacks": fallbacks,
            "max_deltas": max_deltas,
        }

        require_qutip_in_ci = not breaches and not fallbacks
        if require_qutip_in_ci:
            recommendation = {
                "decision": "go",
                "rationale": "Focused parity checks are within configured guard-bands and no fallbacks observed.",
                "require_qutip_in_ci": True,
            }
        else:
            recommendation = {
                "decision": "no-go",
                "rationale": (
                    "Focused parity lane shows material analytic-vs-QuTiP deltas and/or fallback behavior. "
                    "Keep QuTiP lane optional until model alignment improves."
                ),
                "require_qutip_in_ci": False,
            }
        report["recommendation"] = recommendation

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    md = _render_markdown(report)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text(md + "\n", encoding="utf-8")

    print(f"QuTiP parity report written: {args.output_json}")
    print(f"QuTiP parity summary written: {args.output_md}")
    print(f"Recommendation: {report['recommendation']['decision'].upper()}")

    if args.strict:
        if report["status"] == "skipped":
            return 1
        if report["summary"].get("threshold_breaches") or report["summary"].get("fallbacks"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
