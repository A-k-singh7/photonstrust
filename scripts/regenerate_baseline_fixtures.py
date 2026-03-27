"""Regenerate baseline fixtures (demo + Phase 41) and validate them.

This is an operator-friendly front door that reuses the existing baseline
scripts/tests and adds a deterministic re-run check.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

FIXTURE_RELPATHS = [
    "tests/fixtures/baselines.json",
    "tests/fixtures/canonical_phase41_baselines.json",
    "tests/fixtures/canonical_phase54_satellite_baselines.json",
]

BASELINE_TESTS = [
    "tests/test_regression_baselines.py",
    "tests/test_canonical_baselines.py",
    "tests/test_satellite_canonical_baselines.py",
    "tests/test_validation_harness.py",
]


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_generators_and_hash(repo_root: Path, python_exe: str) -> dict[str, str]:
    _run([python_exe, "scripts/generate_baselines.py"], cwd=repo_root)
    _run([python_exe, "scripts/generate_phase41_canonical_baselines.py"], cwd=repo_root)
    _run([python_exe, "scripts/generate_phase54_satellite_canonical_baselines.py"], cwd=repo_root)

    hashes: dict[str, str] = {}
    for rel in FIXTURE_RELPATHS:
        path = repo_root / rel
        if not path.exists():
            raise SystemExit(f"Expected fixture was not generated: {path}")
        hashes[rel] = _sha256(path)
    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Regenerate demo + Phase 41 baseline fixtures and validate them."
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("results/validation"),
        help="Output root for validation harness artifacts.",
    )
    parser.add_argument(
        "--skip-determinism-check",
        action="store_true",
        help="Skip the second generator pass/hash-compare determinism check.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    python_exe = sys.executable

    first_hashes = _run_generators_and_hash(repo_root, python_exe)

    if not args.skip_determinism_check:
        second_hashes = _run_generators_and_hash(repo_root, python_exe)
        if first_hashes != second_hashes:
            print("ERROR: Non-deterministic fixture regeneration detected.", file=sys.stderr)
            for rel in FIXTURE_RELPATHS:
                h1 = first_hashes.get(rel)
                h2 = second_hashes.get(rel)
                if h1 != h2:
                    print(f"  - {rel}: {h1} != {h2}", file=sys.stderr)
            return 1

    _run([python_exe, "-m", "pytest", *BASELINE_TESTS], cwd=repo_root)
    _run([python_exe, "scripts/validation/check_benchmark_drift.py"], cwd=repo_root)
    _run(
        [python_exe, "scripts/validation/run_validation_harness.py", "--output-root", str(args.output_root)],
        cwd=repo_root,
    )

    print("\nBaseline fixtures regenerated and validated successfully.")
    for rel in FIXTURE_RELPATHS:
        print(f"  - {rel}: {first_hashes[rel]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
