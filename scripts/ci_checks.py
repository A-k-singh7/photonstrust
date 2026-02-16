"""Practical local/CI guardrails for PhotonTrust.

Runs:
1) compileall bytecode checks
2) pytest suite
3) validation harness smoke (single canonical baseline case)
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("+", " ".join(cmd))
    completed = subprocess.run(cmd, cwd=cwd)
    return int(completed.returncode)


def _run_validation_harness_smoke(*, repo_root: Path, output_root: Path) -> int:
    code = """
from pathlib import Path
from photonstrust.benchmarks.validation_harness import ValidationCase, run_validation_harness

repo_root = Path.cwd()
case = ValidationCase(
    case_id="ci_smoke_demo1_default",
    config_path=repo_root / "configs" / "demo1_default.yml",
    baseline_path=repo_root / "tests" / "fixtures" / "baselines.json",
)
summary = run_validation_harness(
    repo_root=repo_root,
    output_root=Path(__import__('os').environ["PHOTONTRUST_CI_VALIDATION_OUTPUT"]),
    cases=[case],
)
print(summary)
raise SystemExit(0 if bool(summary.get('ok', False)) else 1)
"""
    env = dict(**os.environ)
    env["PHOTONTRUST_CI_VALIDATION_OUTPUT"] = str(output_root)
    cmd = [sys.executable, "-c", code]
    print("+", "validation harness smoke (single case)")
    completed = subprocess.run(cmd, cwd=repo_root, env=env)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run compile/test/validation CI guardrails")
    parser.add_argument(
        "--pytest-args",
        default="-q",
        help="Arguments forwarded to pytest (default: '-q').",
    )
    parser.add_argument(
        "--validation-output-root",
        default="results/validation_ci_smoke",
        help="Output root for validation harness smoke artifacts.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    steps = [
        (
            "compileall",
            [sys.executable, "-m", "compileall", "-q", "photonstrust", "scripts", "tests"],
        ),
        (
            "pytest",
            [sys.executable, "-m", "pytest", *shlex.split(args.pytest_args)],
        ),
    ]

    for name, cmd in steps:
        rc = _run(cmd, cwd=repo_root)
        if rc != 0:
            print(f"[ci-checks] failed step: {name}")
            return rc

    rc = _run_validation_harness_smoke(
        repo_root=repo_root,
        output_root=repo_root / args.validation_output_root,
    )
    if rc != 0:
        print("[ci-checks] failed step: validation_harness_smoke")
        return rc

    print("[ci-checks] all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
