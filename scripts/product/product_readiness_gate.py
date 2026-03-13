#!/usr/bin/env python3
"""Run a fail-closed local product readiness gate for Week 4 surfaces."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from typing import Any, Callable
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local product readiness gate (QKD + PIC + pilot flow)")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000", help="API base URL when not spawning API")
    parser.add_argument("--spawn-api", action="store_true", help="Spawn uvicorn API for gate execution")
    parser.add_argument("--api-host", default="127.0.0.1", help="Host for spawned API")
    parser.add_argument("--api-port", type=int, default=8000, help="Port for spawned API")
    parser.add_argument("--project-id", default="product_readiness", help="Project ID for test runs")
    parser.add_argument("--timeout-s", type=float, default=180.0, help="API POST timeout seconds")
    parser.add_argument("--health-timeout-s", type=float, default=40.0, help="Health wait timeout when spawning API")
    parser.add_argument("--skip-qkd", action="store_true", help="Skip QKD run check")
    parser.add_argument("--skip-pic", action="store_true", help="Skip PIC checks")
    parser.add_argument("--skip-pilot", action="store_true", help="Skip pilot demo script check")
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("results/product_readiness/product_readiness_report.json"),
        help="Path for machine-readable readiness report JSON",
    )
    parser.add_argument(
        "--pilot-results-root",
        type=Path,
        default=Path("results/product_readiness/pilot_runs"),
        help="Output root passed to pilot demo script",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print plan only, do not execute checks")
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
        payload_obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}") from exc
    if not isinstance(payload_obj, dict):
        raise RuntimeError(f"Unexpected non-object response from {url}")
    return payload_obj


def _is_port_available(host: str, port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((str(host), int(port)))
        return True
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except Exception:
            pass


def _wait_for_health(api_base_url: str, *, timeout_s: float) -> dict[str, Any]:
    deadline = time.time() + max(1.0, float(timeout_s))
    last_error: str | None = None
    while time.time() < deadline:
        try:
            return _request_json(method="GET", url=f"{api_base_url.rstrip('/')}/healthz", payload=None, timeout_s=3.0)
        except Exception as exc:
            last_error = str(exc)
            time.sleep(0.4)
    raise RuntimeError(f"API health timeout at {api_base_url}/healthz ({last_error or 'no response'})")


def _qkd_graph() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "graph_id": "gate_qkd_link",
        "profile": "qkd_link",
        "metadata": {"title": "Gate QKD Graph", "description": "", "created_at": "2026-02-18"},
        "scenario": {"id": "gate_qkd_link", "distance_km": 10, "band": "c_1550", "wavelength_nm": 1550, "execution_mode": "preview"},
        "uncertainty": {},
        "nodes": [
            {"id": "source_1", "kind": "qkd.source", "params": {"type": "emitter_cavity"}},
            {"id": "channel_1", "kind": "qkd.channel", "params": {"model": "fiber"}},
            {"id": "detector_1", "kind": "qkd.detector", "params": {"class": "snspd"}},
            {"id": "timing_1", "kind": "qkd.timing", "params": {"sync_drift_ps_rms": 10}},
            {"id": "protocol_1", "kind": "qkd.protocol", "params": {"name": "BBM92"}},
        ],
        "edges": [
            {"from": "source_1", "to": "channel_1", "kind": "optical"},
            {"from": "channel_1", "to": "detector_1", "kind": "optical"},
        ],
    }


def _pic_chain_graph() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "graph_id": "gate_pic_chain",
        "profile": "pic_circuit",
        "metadata": {"title": "Gate PIC Chain", "description": "", "created_at": "2026-02-18"},
        "circuit": {"id": "gate_pic_chain", "wavelength_nm": 1550},
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 2.5}},
            {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 2000, "loss_db_per_cm": 2.0}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {"insertion_loss_db": 1.5}},
        ],
        "edges": [
            {"from": "gc_in", "to": "wg_1", "kind": "optical"},
            {"from": "wg_1", "to": "ec_out", "kind": "optical"},
        ],
    }


def _pic_mzi_graph() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "graph_id": "gate_pic_mzi",
        "profile": "pic_circuit",
        "metadata": {"title": "Gate PIC MZI", "description": "", "created_at": "2026-02-18"},
        "circuit": {
            "id": "gate_pic_mzi",
            "wavelength_nm": 1550,
            "solver": "scattering",
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 1.0, "insertion_loss_db": 0.1}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in", "kind": "optical"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in", "kind": "optical"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1", "kind": "optical"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2", "kind": "optical"},
        ],
    }


def _terminate_process(proc: subprocess.Popen[bytes | str], *, name: str) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        pass
    try:
        proc.wait(timeout=8.0)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=3.0)
    except Exception:
        print(f"[warn] Could not fully stop process: {name}")


def _run_check(name: str, fn: Callable[[], dict[str, Any]], checks: list[dict[str, Any]]) -> None:
    started = time.perf_counter()
    try:
        details = fn()
        checks.append(
            {
                "name": name,
                "passed": True,
                "duration_s": time.perf_counter() - started,
                "details": details,
            }
        )
    except Exception as exc:
        checks.append(
            {
                "name": name,
                "passed": False,
                "duration_s": time.perf_counter() - started,
                "details": {"error": str(exc)},
            }
        )


def _require_finite_number(
    value: Any,
    *,
    field: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{field} must be numeric, got {value!r}") from exc
    if not math.isfinite(parsed):
        raise RuntimeError(f"{field} must be finite, got {parsed!r}")
    if minimum is not None and parsed < float(minimum):
        raise RuntimeError(f"{field}={parsed!r} is below minimum {float(minimum)!r}")
    if maximum is not None and parsed > float(maximum):
        raise RuntimeError(f"{field}={parsed!r} is above maximum {float(maximum)!r}")
    return float(parsed)


def _require_nonempty_string(value: Any, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{field} must be a non-empty string")
    return text


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    report_path = args.report_path if args.report_path.is_absolute() else (repo_root / args.report_path)
    report_path = report_path.resolve()
    pilot_results_root = args.pilot_results_root if args.pilot_results_root.is_absolute() else (repo_root / args.pilot_results_root)
    pilot_results_root = pilot_results_root.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    pilot_results_root.mkdir(parents=True, exist_ok=True)

    api_base_url = str(args.api_base_url).strip().rstrip("/")
    api_proc: subprocess.Popen[bytes | str] | None = None
    checks: list[dict[str, Any]] = []
    started_at = datetime.now(timezone.utc).isoformat()

    if bool(args.spawn_api):
        api_base_url = f"http://{args.api_host}:{int(args.api_port)}"

    if args.dry_run:
        print("[dry-run] Product readiness gate plan")
        print(f"- api_base_url: {api_base_url}")
        print(f"- spawn_api: {bool(args.spawn_api)}")
        print(f"- skip_qkd: {bool(args.skip_qkd)}")
        print(f"- skip_pic: {bool(args.skip_pic)}")
        print(f"- skip_pilot: {bool(args.skip_pilot)}")
        print(f"- report_path: {report_path}")
        return 0

    try:
        if bool(args.spawn_api):
            if not _is_port_available(str(args.api_host), int(args.api_port)):
                raise RuntimeError(f"Cannot spawn API: port already in use ({args.api_host}:{int(args.api_port)})")

            env = dict(os.environ)
            env["PHOTONTRUST_API_RUNS_ROOT"] = str((report_path.parent / "api_runs").resolve())
            api_cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "photonstrust.api.server:app",
                "--host",
                str(args.api_host),
                "--port",
                str(int(args.api_port)),
            ]
            api_proc = subprocess.Popen(api_cmd, cwd=str(repo_root), env=env)
            _ = _wait_for_health(api_base_url, timeout_s=float(args.health_timeout_s))

        def _check_api_health() -> dict[str, Any]:
            payload = _request_json(method="GET", url=f"{api_base_url}/healthz", payload=None, timeout_s=15.0)
            status = str(payload.get("status", "")).strip().lower()
            version = _require_nonempty_string(payload.get("version"), field="api.health.version")
            if status != "ok":
                raise RuntimeError(f"api.health.status must be 'ok', got {status!r}")
            return {"status": status, "version": version}

        _run_check("api_health", _check_api_health, checks)

        if not bool(args.skip_qkd):
            def _check_qkd() -> dict[str, Any]:
                payload = {
                    "graph": _qkd_graph(),
                    "project_id": str(args.project_id),
                    "execution_mode": "preview",
                    "include_qasm": False,
                }
                response = _request_json(
                    method="POST",
                    url=f"{api_base_url}/v0/qkd/run",
                    payload=payload,
                    timeout_s=float(args.timeout_s),
                )
                first_card = {}
                results = response.get("results") if isinstance(response.get("results"), dict) else {}
                cards = results.get("cards") if isinstance(results.get("cards"), list) else []
                if cards and isinstance(cards[0], dict):
                    first_card = cards[0]
                outputs = first_card.get("outputs") if isinstance(first_card.get("outputs"), dict) else {}
                derived = first_card.get("derived") if isinstance(first_card.get("derived"), dict) else {}
                safe = first_card.get("safe_use_label") if isinstance(first_card.get("safe_use_label"), dict) else {}
                run_id = _require_nonempty_string(response.get("run_id"), field="qkd.run_id")
                key_rate_bps = _require_finite_number(
                    outputs.get("key_rate_bps"),
                    field="qkd.outputs.key_rate_bps",
                    minimum=0.0,
                )
                qber = _require_finite_number(
                    derived.get("qber_total"),
                    field="qkd.derived.qber_total",
                    minimum=0.0,
                    maximum=0.5,
                )
                safe_use = _require_nonempty_string(safe.get("label"), field="qkd.safe_use.label")
                return {
                    "run_id": run_id,
                    "key_rate_bps": key_rate_bps,
                    "qber": qber,
                    "safe_use": safe_use,
                }

            _run_check("qkd_run_golden", _check_qkd, checks)

        if not bool(args.skip_pic):
            def _check_pic_chain() -> dict[str, Any]:
                response = _request_json(
                    method="POST",
                    url=f"{api_base_url}/v0/pic/simulate",
                    payload={"graph": _pic_chain_graph(), "wavelength_nm": 1550.0},
                    timeout_s=float(args.timeout_s),
                )
                results = response.get("results") if isinstance(response.get("results"), dict) else {}
                chain = results.get("chain_solver") if isinstance(results.get("chain_solver"), dict) else {}
                graph_hash = _require_nonempty_string(response.get("graph_hash"), field="pic.chain.graph_hash")
                eta_total = _require_finite_number(
                    chain.get("eta_total"),
                    field="pic.chain.eta_total",
                    minimum=0.0,
                    maximum=1.0,
                )
                total_loss_db = _require_finite_number(
                    chain.get("total_loss_db"),
                    field="pic.chain.total_loss_db",
                    minimum=0.0,
                )
                return {
                    "graph_hash": graph_hash,
                    "eta_total": eta_total,
                    "total_loss_db": total_loss_db,
                }

            def _check_pic_mzi() -> dict[str, Any]:
                response = _request_json(
                    method="POST",
                    url=f"{api_base_url}/v0/pic/simulate",
                    payload={"graph": _pic_mzi_graph(), "wavelength_nm": 1550.0},
                    timeout_s=float(args.timeout_s),
                )
                results = response.get("results") if isinstance(response.get("results"), dict) else {}
                scatt = results.get("scattering_solver") if isinstance(results.get("scattering_solver"), dict) else {}
                graph_hash = _require_nonempty_string(response.get("graph_hash"), field="pic.mzi.graph_hash")
                applicable = bool(scatt.get("applicable", False))
                if not applicable:
                    reason = str(scatt.get("reason", "")).strip() or "scattering solver not applicable"
                    raise RuntimeError(f"pic.mzi.scattering_solver.applicable must be true ({reason})")
                external_outputs = scatt.get("external_outputs") if isinstance(scatt.get("external_outputs"), list) else []
                if len(external_outputs) == 0:
                    raise RuntimeError("pic.mzi.scattering_solver.external_outputs must be non-empty")
                return {
                    "graph_hash": graph_hash,
                    "scattering_applicable": applicable,
                    "external_outputs": len(external_outputs),
                }

            _run_check("pic_chain_simulate", _check_pic_chain, checks)
            _run_check("pic_mzi_simulate", _check_pic_mzi, checks)

        if not bool(args.skip_pilot):
            def _check_pilot_script() -> dict[str, Any]:
                cmd = [
                    sys.executable,
                    str((repo_root / "scripts" / "run_product_pilot_demo.py").resolve()),
                    "--api-base-url",
                    api_base_url,
                    "--project-id",
                    str(args.project_id),
                    "--results-root",
                    str(pilot_results_root),
                    "--label",
                    "product_readiness_gate",
                    "--strict",
                ]
                completed = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, check=False)
                if completed.returncode != 0:
                    raise RuntimeError(
                        f"Pilot demo script failed ({completed.returncode}). "
                        f"stdout={completed.stdout[-600:]} stderr={completed.stderr[-600:]}"
                    )
                summary_path = None
                for line in completed.stdout.splitlines():
                    match = re.search(r"summary:\s*(.+pilot_demo_summary\.json)$", line.strip())
                    if match:
                        summary_path = Path(match.group(1).strip())
                        break
                if summary_path is None or not summary_path.exists():
                    raise RuntimeError("Pilot demo script succeeded but summary path was not found in stdout.")
                summary = json.loads(summary_path.read_text(encoding="utf-8"))
                cases_total = int(summary.get("cases_total", 0) or 0)
                cases_succeeded = int(summary.get("cases_succeeded", 0) or 0)
                cases_failed = int(summary.get("cases_failed", 0) or 0)
                if cases_total <= 0:
                    raise RuntimeError("Pilot demo summary has no cases.")
                if cases_failed != 0 or cases_succeeded != cases_total:
                    raise RuntimeError(
                        "Pilot demo summary indicates failures "
                        f"(succeeded={cases_succeeded}, failed={cases_failed}, total={cases_total})."
                    )
                rows = summary.get("cases") if isinstance(summary.get("cases"), list) else []
                if len(rows) != cases_total:
                    raise RuntimeError(
                        f"Pilot demo summary row count mismatch (rows={len(rows)} total={cases_total})."
                    )
                not_ok = [row.get("case_id") for row in rows if isinstance(row, dict) and str(row.get("status", "")).lower() != "ok"]
                if not_ok:
                    raise RuntimeError(f"Pilot demo summary contains non-ok cases: {not_ok}")
                return {
                    "summary_path": str(summary_path),
                    "cases_total": cases_total,
                    "cases_succeeded": cases_succeeded,
                    "cases_failed": cases_failed,
                }

            _run_check("pilot_demo_script", _check_pilot_script, checks)

    finally:
        if api_proc is not None:
            _terminate_process(api_proc, name="uvicorn")

    all_passed = all(bool(item.get("passed")) for item in checks)
    report = {
        "schema_version": "0.1",
        "kind": "photonstrust.product_readiness_gate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at,
        "api_base_url": api_base_url,
        "spawn_api": bool(args.spawn_api),
        "checks": checks,
        "all_passed": bool(all_passed),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Product readiness report: {report_path}")
    print(f"Product readiness: {'PASS' if all_passed else 'FAIL'}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
