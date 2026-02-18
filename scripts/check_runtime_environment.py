"""Validate isolated Python runtime environment and lock constraints."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def canonicalize_name(name: str) -> str:
    return re.sub(r"[-_.]+", "-", str(name).strip().lower())


def parse_lock_file(lock_path: Path) -> dict[str, str]:
    if not lock_path.exists():
        raise ValueError(f"lock file does not exist: {lock_path}")

    requirements: dict[str, str] = {}
    for lineno, raw_line in enumerate(lock_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if "==" not in line:
            raise ValueError(f"{lock_path}:{lineno}: expected pinned requirement with '=='")
        name, version = line.split("==", 1)
        key = canonicalize_name(name)
        normalized_version = version.strip()
        if not key or not normalized_version:
            raise ValueError(f"{lock_path}:{lineno}: invalid pinned requirement")
        existing = requirements.get(key)
        if existing is not None and existing != normalized_version:
            raise ValueError(
                f"{lock_path}:{lineno}: conflicting pins for {key}: {existing} vs {normalized_version}"
            )
        requirements[key] = normalized_version

    if not requirements:
        raise ValueError(f"lock file has no pinned requirements: {lock_path}")
    return requirements


def collect_installed_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for dist in metadata.distributions():
        name = dist.metadata.get("Name") or dist.metadata.get("name") or ""
        if not name:
            continue
        out[canonicalize_name(name)] = str(dist.version)
    return out


def check_locked_versions(
    lock_requirements: dict[str, str],
    *,
    installed_versions: dict[str, str] | None = None,
) -> list[str]:
    observed = installed_versions if installed_versions is not None else collect_installed_versions()
    failures: list[str] = []
    for name, expected in sorted(lock_requirements.items()):
        actual = observed.get(name)
        if actual is None:
            failures.append(f"missing locked dependency: {name}=={expected}")
            continue
        if str(actual) != str(expected):
            failures.append(f"locked dependency mismatch: {name} installed={actual} expected={expected}")
    return failures


def active_virtualenv_path() -> Path | None:
    venv_env = os.environ.get("VIRTUAL_ENV")
    if venv_env:
        return Path(venv_env).resolve()
    if sys.prefix == sys.base_prefix:
        return None
    return Path(sys.prefix).resolve()


def check_isolated_environment(
    repo_root: Path,
    *,
    require_local_venv: bool,
    active_venv: Path | None = None,
) -> list[str]:
    venv_path = active_venv if active_venv is not None else active_virtualenv_path()
    failures: list[str] = []

    if venv_path is None:
        failures.append("not running inside a virtual environment")
        return failures

    if require_local_venv:
        try:
            venv_path.relative_to(repo_root.resolve())
        except ValueError:
            failures.append(f"virtual environment is outside repository root: {venv_path}")
    return failures


def run_pip_check(*, python_executable: str | Path | None = None) -> tuple[bool, str]:
    python_cmd = str(python_executable or sys.executable)
    proc = subprocess.run(
        [python_cmd, "-m", "pip", "check"],
        capture_output=True,
        text=True,
    )
    output = ((proc.stdout or "") + (proc.stderr or "")).strip()
    return proc.returncode == 0, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate isolated runtime environment and dependency locks.")
    parser.add_argument(
        "--lock-file",
        type=Path,
        default=Path("requirements/runtime.lock.txt"),
        help="Path to lock/constraints file (default: requirements/runtime.lock.txt).",
    )
    parser.add_argument(
        "--require-local-venv",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Require the active virtual environment to live under the repository root (default: true).",
    )
    parser.add_argument(
        "--skip-pip-check",
        action="store_true",
        help="Skip `pip check` dependency resolution validation.",
    )
    parser.add_argument(
        "--skip-lock-check",
        action="store_true",
        help="Skip validation against the lock file.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        default=None,
        help="Optional output path for machine-readable report JSON.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report: dict = {
        "repo_root": str(repo_root),
        "python_executable": str(sys.executable),
        "active_virtualenv": str(active_virtualenv_path() or ""),
        "lock_file": str(args.lock_file),
        "checks": [],
        "ok": True,
        "failures": [],
    }

    failures: list[str] = []

    env_failures = check_isolated_environment(repo_root, require_local_venv=bool(args.require_local_venv))
    if env_failures:
        failures.extend(env_failures)
    report["checks"].append({"name": "isolated_environment", "ok": not env_failures, "details": env_failures})

    if args.skip_lock_check:
        report["checks"].append({"name": "locked_dependencies", "ok": True, "details": ["skipped"]})
    else:
        try:
            lock_requirements = parse_lock_file(args.lock_file if args.lock_file.is_absolute() else repo_root / args.lock_file)
            lock_failures = check_locked_versions(lock_requirements)
        except Exception as exc:
            lock_failures = [f"lock check failed: {exc}"]
        if lock_failures:
            failures.extend(lock_failures)
        report["checks"].append({"name": "locked_dependencies", "ok": not lock_failures, "details": lock_failures})

    if args.skip_pip_check:
        report["checks"].append({"name": "pip_check", "ok": True, "details": ["skipped"]})
    else:
        pip_ok, pip_output = run_pip_check()
        if not pip_ok:
            failures.append("pip check failed")
        report["checks"].append(
            {
                "name": "pip_check",
                "ok": bool(pip_ok),
                "details": [pip_output] if pip_output else [],
            }
        )

    report["ok"] = len(failures) == 0
    report["failures"] = failures

    if args.report_json is not None:
        report_path = args.report_json if args.report_json.is_absolute() else (repo_root / args.report_json)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if report["ok"]:
        print("Runtime environment check: PASS")
        return 0

    print("Runtime environment check: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
