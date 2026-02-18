#!/usr/bin/env python3
"""Run a 3-scenario pilot demo against the local PhotonTrust API."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from typing import Any
from urllib import error, request


@dataclass(frozen=True)
class PilotCase:
    case_id: str
    protocol_name: str
    distance_km: float
    rep_rate_mhz: float
    pde: float
    dark_counts_cps: float
    coincidence_window_ps: float
    mu: float
    relay_fraction: float = 0.5
    nu: float = 0.05
    omega: float = 0.0
    phase_slices: int = 32
    detector_class: str = "snspd"
    source_type: str = "emitter_cavity"
    collection_efficiency: float = 0.35
    coupling_efficiency: float = 0.6


PILOT_CASES: tuple[PilotCase, ...] = (
    PilotCase(
        case_id="bbm92_metro_50km",
        protocol_name="BBM92",
        distance_km=50.0,
        rep_rate_mhz=100.0,
        pde=0.30,
        dark_counts_cps=100.0,
        coincidence_window_ps=200.0,
        mu=0.5,
    ),
    PilotCase(
        case_id="mdi_intercity_150km",
        protocol_name="MDI_QKD",
        distance_km=150.0,
        rep_rate_mhz=100.0,
        pde=0.75,
        dark_counts_cps=1.0,
        coincidence_window_ps=200.0,
        mu=0.2,
        nu=0.05,
        omega=0.0,
        relay_fraction=0.5,
        collection_efficiency=0.45,
        coupling_efficiency=0.65,
    ),
    PilotCase(
        case_id="tf_backbone_300km",
        protocol_name="TF_QKD",
        distance_km=300.0,
        rep_rate_mhz=850.0,
        pde=0.80,
        dark_counts_cps=0.1,
        coincidence_window_ps=100.0,
        mu=0.2,
        phase_slices=64,
        relay_fraction=0.5,
        collection_efficiency=0.50,
        coupling_efficiency=0.75,
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PhotonTrust product pilot demo cases")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000", help="PhotonTrust API base URL")
    parser.add_argument("--project-id", default="pilot_demo", help="Project ID used for all demo runs")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results/product_pilot_demo"),
        help="Root output directory for pilot demo artifacts",
    )
    parser.add_argument(
        "--execution-mode",
        choices=["preview", "certification"],
        default="preview",
        help="Execution mode used for qkd runs",
    )
    parser.add_argument("--include-qasm", action="store_true", help="Request qasm protocol artifacts")
    parser.add_argument("--timeout-s", type=float, default=180.0, help="Per-run API timeout seconds")
    parser.add_argument(
        "--label",
        default=None,
        help="Optional run label; defaults to UTC timestamp",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print cases and payloads, do not call API")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if any case fails")
    return parser.parse_args()


def _request_json(*, method: str, url: str, payload: dict[str, Any] | None, timeout_s: float) -> dict[str, Any]:
    body = None
    headers = {"accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["content-type"] = "application/json"
    req = request.Request(url=url, data=body, method=method.upper(), headers=headers)
    try:
        with request.urlopen(req, timeout=max(1.0, float(timeout_s))) as resp:
            raw = resp.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}: {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError(f"Unexpected non-object response from {url}")
    return parsed


def _safe_id(value: str, *, max_len: int = 64, fallback: str = "run") -> str:
    text = re.sub(r"[^a-z0-9_-]+", "_", str(value or "").strip().lower())
    text = text.strip("_-")
    if not text:
        text = fallback
    if len(text) > max_len:
        text = text[:max_len]
    if not text[0].isalnum():
        text = f"x{text}"
    while len(text) < 3:
        text += "x"
    return text


def _build_graph(case: PilotCase, *, run_token: str, execution_mode: str) -> dict[str, Any]:
    protocol = str(case.protocol_name).strip().upper()
    protocol_params: dict[str, Any] = {
        "name": protocol,
        "sifting_factor": 0.5,
        "ec_efficiency": 1.16,
        "misalignment_prob": 0.01,
    }
    if protocol in {"MDI_QKD", "AMDI_QKD", "PM_QKD", "TF_QKD"}:
        protocol_params["relay_fraction"] = float(case.relay_fraction)
        protocol_params["mu"] = float(case.mu)
    if protocol in {"MDI_QKD", "AMDI_QKD"}:
        protocol_params["nu"] = float(case.nu)
        protocol_params["omega"] = float(case.omega)
    if protocol in {"PM_QKD", "TF_QKD"}:
        protocol_params["phase_slices"] = int(case.phase_slices)

    case_token = _safe_id(case.case_id, max_len=32, fallback="case")
    scenario_id = _safe_id(f"s_{case_token}_{run_token}", max_len=64, fallback="scenario")
    graph_id = _safe_id(f"g_{case_token}_{run_token}", max_len=64, fallback="graph")
    return {
        "schema_version": "0.1",
        "graph_id": graph_id,
        "profile": "qkd_link",
        "metadata": {
            "title": f"Pilot demo: {case.case_id}",
            "description": "Generated by scripts/run_product_pilot_demo.py",
            "created_at": datetime.now(timezone.utc).date().isoformat(),
        },
        "scenario": {
            "id": scenario_id,
            "distance_km": {"start": float(case.distance_km), "stop": float(case.distance_km), "step": 1.0},
            "band": "c_1550",
            "wavelength_nm": 1550.0,
            "execution_mode": str(execution_mode).strip().lower(),
        },
        "uncertainty": {},
        "nodes": [
            {
                "id": "source_1",
                "kind": "qkd.source",
                "label": "Emitter",
                "params": {
                    "type": str(case.source_type),
                    "physics_backend": "analytic",
                    "rep_rate_mhz": float(case.rep_rate_mhz),
                    "collection_efficiency": float(case.collection_efficiency),
                    "coupling_efficiency": float(case.coupling_efficiency),
                    "g2_0": 0.02,
                },
            },
            {
                "id": "channel_1",
                "kind": "qkd.channel",
                "label": "Fiber",
                "params": {
                    "model": "fiber",
                    "fiber_loss_db_per_km": 0.2,
                    "connector_loss_db": 1.5,
                    "background_counts_cps": 0.0,
                },
            },
            {
                "id": "detector_1",
                "kind": "qkd.detector",
                "label": "Detector",
                "params": {
                    "class": str(case.detector_class),
                    "pde": float(case.pde),
                    "dark_counts_cps": float(case.dark_counts_cps),
                    "background_counts_cps": 0.0,
                    "jitter_ps_fwhm": 30.0,
                    "dead_time_ns": 100.0,
                    "afterpulsing_prob": 0.001,
                },
            },
            {
                "id": "timing_1",
                "kind": "qkd.timing",
                "label": "Timing",
                "params": {
                    "sync_drift_ps_rms": 10.0,
                    "coincidence_window_ps": float(case.coincidence_window_ps),
                },
            },
            {
                "id": "protocol_1",
                "kind": "qkd.protocol",
                "label": "Protocol",
                "params": protocol_params,
            },
        ],
        "edges": [
            {"from": "source_1", "to": "channel_1", "kind": "control", "label": "emits into"},
            {"from": "channel_1", "to": "detector_1", "kind": "optical", "label": "propagates"},
        ],
    }


def _extract_first_card(payload: dict[str, Any]) -> dict[str, Any] | None:
    results = payload.get("results") if isinstance(payload.get("results"), dict) else {}
    cards = results.get("cards") if isinstance(results.get("cards"), list) else []
    if cards and isinstance(cards[0], dict):
        return cards[0]
    return None


def _render_summary_markdown(summary: dict[str, Any]) -> str:
    rows = summary.get("cases") if isinstance(summary.get("cases"), list) else []
    lines: list[str] = [
        "# Product Pilot Demo Summary",
        "",
        f"- generated_at: `{summary.get('generated_at')}`",
        f"- api_base_url: `{summary.get('api_base_url')}`",
        f"- project_id: `{summary.get('project_id')}`",
        f"- execution_mode: `{summary.get('execution_mode')}`",
        f"- cases_total: `{summary.get('cases_total')}`",
        f"- cases_succeeded: `{summary.get('cases_succeeded')}`",
        f"- cases_failed: `{summary.get('cases_failed')}`",
        "",
        "| case_id | protocol | status | key_rate_bps | qber | safe_use | run_id | duration_s |",
        "|---|---|---:|---:|---:|---|---|---:|",
    ]
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| {case_id} | {protocol} | {status} | {key_rate} | {qber} | {safe_use} | {run_id} | {duration_s} |".format(
                case_id=str(row.get("case_id", "")),
                protocol=str(row.get("protocol_name", "")),
                status=str(row.get("status", "")),
                key_rate=_fmt_number(row.get("key_rate_bps")),
                qber=_fmt_number(row.get("qber")),
                safe_use=str(row.get("safe_use", "")),
                run_id=str(row.get("run_id", "")),
                duration_s=_fmt_number(row.get("duration_s")),
            )
        )
        if str(row.get("error", "")).strip():
            lines.append(f"- `{row.get('case_id')}` error: {row.get('error')}")
    lines.append("")
    return "\n".join(lines)


def _fmt_number(value: Any) -> str:
    try:
        return f"{float(value):.6g}"
    except (TypeError, ValueError):
        return ""


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    results_root = args.results_root if args.results_root.is_absolute() else (repo_root / args.results_root)
    results_root = results_root.resolve()
    run_label = str(args.label or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    run_token = _safe_id(run_label, max_len=20, fallback="run")
    out_dir = (results_root / run_label).resolve()
    raw_dir = out_dir / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    api_base_url = str(args.api_base_url).strip().rstrip("/")
    health_url = f"{api_base_url}/healthz"

    if args.dry_run:
        print(f"[dry-run] API: {api_base_url}")
        print(f"[dry-run] project_id: {args.project_id}")
        print(f"[dry-run] output_dir: {out_dir}")
        for case in PILOT_CASES:
            graph = _build_graph(case, run_token=run_token, execution_mode=str(args.execution_mode))
            payload = {
                "graph": graph,
                "project_id": str(args.project_id),
                "execution_mode": str(args.execution_mode),
                "include_qasm": bool(args.include_qasm),
            }
            print(f"[dry-run] case={case.case_id} payload_graph_id={graph.get('graph_id')}")
            (raw_dir / f"{case.case_id}.request.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return 0

    try:
        _ = _request_json(method="GET", url=health_url, payload=None, timeout_s=8.0)
    except Exception as exc:
        print(f"[error] API health check failed at {health_url}: {exc}")
        return 2

    case_rows: list[dict[str, Any]] = []
    for case in PILOT_CASES:
        graph = _build_graph(case, run_token=run_token, execution_mode=str(args.execution_mode))
        payload = {
            "graph": graph,
            "project_id": str(args.project_id),
            "execution_mode": str(args.execution_mode),
            "include_qasm": bool(args.include_qasm),
        }
        (raw_dir / f"{case.case_id}.request.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[run] {case.case_id} ({case.protocol_name}, {case.distance_km:.1f} km)")

        started = time.perf_counter()
        row: dict[str, Any] = {
            "case_id": case.case_id,
            "protocol_name": case.protocol_name,
            "distance_km": float(case.distance_km),
            "status": "failed",
            "duration_s": None,
            "run_id": None,
            "key_rate_bps": None,
            "qber": None,
            "safe_use": None,
            "output_dir": None,
            "error": None,
        }
        try:
            response = _request_json(
                method="POST",
                url=f"{api_base_url}/v0/qkd/run",
                payload=payload,
                timeout_s=float(args.timeout_s),
            )
            (raw_dir / f"{case.case_id}.response.json").write_text(json.dumps(response, indent=2), encoding="utf-8")
            first_card = _extract_first_card(response) or {}
            outputs = first_card.get("outputs") if isinstance(first_card.get("outputs"), dict) else {}
            derived = first_card.get("derived") if isinstance(first_card.get("derived"), dict) else {}
            safe = first_card.get("safe_use_label") if isinstance(first_card.get("safe_use_label"), dict) else {}
            row["status"] = "ok"
            row["run_id"] = response.get("run_id")
            row["output_dir"] = response.get("output_dir")
            row["key_rate_bps"] = outputs.get("key_rate_bps")
            row["qber"] = derived.get("qber_total")
            row["safe_use"] = safe.get("label")
        except Exception as exc:
            row["error"] = str(exc)
            (raw_dir / f"{case.case_id}.error.txt").write_text(str(exc), encoding="utf-8")
        finally:
            row["duration_s"] = time.perf_counter() - started
            case_rows.append(row)

    cases_succeeded = sum(1 for row in case_rows if str(row.get("status")) == "ok")
    cases_failed = len(case_rows) - cases_succeeded
    summary = {
        "schema_version": "0.1",
        "kind": "photonstrust.product_pilot_demo.summary",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base_url": api_base_url,
        "project_id": str(args.project_id),
        "execution_mode": str(args.execution_mode),
        "run_label": run_label,
        "output_dir": str(out_dir),
        "cases_total": len(case_rows),
        "cases_succeeded": cases_succeeded,
        "cases_failed": cases_failed,
        "cases": case_rows,
    }
    summary_path = out_dir / "pilot_demo_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    markdown_path = out_dir / "pilot_demo_summary.md"
    markdown_path.write_text(_render_summary_markdown(summary), encoding="utf-8")

    print(f"[done] summary: {summary_path}")
    print(f"[done] markdown: {markdown_path}")
    print(f"[done] success={cases_succeeded}/{len(case_rows)} failed={cases_failed}")
    if args.strict and cases_failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
