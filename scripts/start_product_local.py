#!/usr/bin/env python3
"""Start PhotonTrust product surfaces locally (API + Streamlit UI)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start PhotonTrust API + UI locally")
    parser.add_argument("--api-host", default="127.0.0.1", help="API host bind address")
    parser.add_argument("--api-port", type=int, default=8000, help="API port")
    parser.add_argument("--ui-host", default="127.0.0.1", help="Streamlit host bind address")
    parser.add_argument("--ui-port", type=int, default=8501, help="Streamlit port")
    parser.add_argument(
        "--results-root",
        type=Path,
        default=Path("results/product_local"),
        help="Results root used by UI and API run outputs",
    )
    parser.add_argument(
        "--project-id",
        default="default",
        help="Default project ID prefilled in Run Builder",
    )
    parser.add_argument("--reload", action="store_true", help="Enable uvicorn auto-reload for API")
    parser.add_argument(
        "--api-start-timeout",
        type=float,
        default=40.0,
        help="Seconds to wait for API health check before failing",
    )
    parser.add_argument(
        "--allow-port-in-use",
        action="store_true",
        help="Skip local port availability preflight checks",
    )
    parser.add_argument(
        "--smoke-seconds",
        type=float,
        default=0.0,
        help="Auto-stop after N seconds (useful for smoke checks)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print commands/env and exit")
    return parser.parse_args()


def _http_health_ok(base_url: str, *, timeout_s: float = 2.0) -> bool:
    url = f"{base_url.rstrip('/')}/healthz"
    try:
        with request.urlopen(url, timeout=max(0.5, float(timeout_s))) as resp:
            _ = resp.read()
            return int(resp.status) == 200
    except (error.URLError, error.HTTPError, TimeoutError):
        return False


def _wait_for_api(base_url: str, *, timeout_s: float) -> bool:
    deadline = time.time() + max(1.0, float(timeout_s))
    while time.time() < deadline:
        if _http_health_ok(base_url):
            return True
        time.sleep(0.4)
    return False


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


def _format_cmd(parts: list[str]) -> str:
    out: list[str] = []
    for item in parts:
        if " " in item:
            out.append(f"\"{item}\"")
        else:
            out.append(item)
    return " ".join(out)


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


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    results_root = args.results_root if args.results_root.is_absolute() else (repo_root / args.results_root)
    results_root = results_root.resolve()
    api_runs_root = (results_root / "api_runs").resolve()
    ui_app_path = (repo_root / "ui" / "app.py").resolve()
    api_base_url = f"http://{args.api_host}:{int(args.api_port)}"
    ui_url = f"http://{args.ui_host}:{int(args.ui_port)}"

    env = dict(os.environ)
    env["PHOTONTRUST_API_BASE_URL"] = api_base_url
    env["PHOTONTRUST_RESULTS_ROOT"] = str(results_root)
    env["PHOTONTRUST_DEFAULT_PROJECT_ID"] = str(args.project_id)
    env["PHOTONTRUST_API_RUNS_ROOT"] = str(api_runs_root)

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
    if args.reload:
        api_cmd.append("--reload")

    ui_cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(ui_app_path),
        "--server.address",
        str(args.ui_host),
        "--server.port",
        str(int(args.ui_port)),
        "--browser.gatherUsageStats",
        "false",
    ]

    print("PhotonTrust local product launcher")
    print(f"- repo_root: {repo_root}")
    print(f"- api_base_url: {api_base_url}")
    print(f"- ui_url: {ui_url}")
    print(f"- results_root: {results_root}")
    print(f"- api_runs_root: {api_runs_root}")
    print(f"- default_project_id: {args.project_id}")
    print(f"- api_cmd: {_format_cmd(api_cmd)}")
    print(f"- ui_cmd: {_format_cmd(ui_cmd)}")

    if args.dry_run:
        return 0

    if not bool(args.allow_port_in_use):
        if not _is_port_available(str(args.api_host), int(args.api_port)):
            print(f"[error] API port already in use: {args.api_host}:{int(args.api_port)}")
            print("Use --allow-port-in-use to skip this check when attaching to existing services.")
            return 3
        if not _is_port_available(str(args.ui_host), int(args.ui_port)):
            print(f"[error] UI port already in use: {args.ui_host}:{int(args.ui_port)}")
            print("Use --allow-port-in-use to skip this check when attaching to existing services.")
            return 3

    results_root.mkdir(parents=True, exist_ok=True)
    api_runs_root.mkdir(parents=True, exist_ok=True)

    api_proc: subprocess.Popen[bytes | str] | None = None
    ui_proc: subprocess.Popen[bytes | str] | None = None
    start_ts = time.time()
    try:
        api_proc = subprocess.Popen(api_cmd, cwd=str(repo_root), env=env)
        if not _wait_for_api(api_base_url, timeout_s=float(args.api_start_timeout)):
            print("[error] API did not become healthy before timeout.")
            return 2

        ui_proc = subprocess.Popen(ui_cmd, cwd=str(repo_root), env=env)

        print("")
        print("Services started:")
        print(f"- API health: {api_base_url}/healthz")
        print(f"- UI: {ui_url}")
        print("Use Ctrl+C to stop both services.")
        if float(args.smoke_seconds) > 0.0:
            print(f"Smoke mode enabled: auto-stop after {args.smoke_seconds:.1f}s")

        while True:
            if api_proc.poll() is not None:
                print(f"[error] API process exited with code {api_proc.returncode}.")
                return int(api_proc.returncode or 1)
            if ui_proc.poll() is not None:
                print(f"[error] UI process exited with code {ui_proc.returncode}.")
                return int(ui_proc.returncode or 1)
            if float(args.smoke_seconds) > 0.0 and (time.time() - start_ts) >= float(args.smoke_seconds):
                print("[ok] Smoke window completed.")
                return 0
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nInterrupted, shutting down services...")
        return 130
    finally:
        if ui_proc is not None:
            _terminate_process(ui_proc, name="streamlit")
        if api_proc is not None:
            _terminate_process(api_proc, name="uvicorn")


if __name__ == "__main__":
    raise SystemExit(main())
