"""Freeze release-candidate baseline hashes and optional validation artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from photonstrust.utils import hash_dict


DEFAULT_FIXTURE_RELPATHS: tuple[str, ...] = (
    "tests/fixtures/baselines.json",
    "tests/fixtures/canonical_phase41_baselines.json",
    "tests/fixtures/canonical_phase54_satellite_baselines.json",
    "tests/fixtures/pic_crosstalk_calibration_baseline.json",
    "tests/fixtures/report_hashes.json",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_relpath(relpath: str) -> str:
    return str(Path(relpath)).replace("\\", "/")


def build_rc_baseline_lock(
    repo_root: Path,
    fixture_relpaths: Sequence[str] = DEFAULT_FIXTURE_RELPATHS,
    *,
    generated_at: str | None = None,
) -> dict:
    fixtures: list[dict] = []
    for relpath in fixture_relpaths:
        normalized = _normalize_relpath(relpath)
        full_path = repo_root / Path(relpath)
        if not full_path.exists():
            raise FileNotFoundError(f"Missing fixture for RC lock: {normalized}")
        fixtures.append(
            {
                "path": normalized,
                "sha256": _sha256_file(full_path),
                "bytes": int(full_path.stat().st_size),
            }
        )

    fixtures.sort(key=lambda row: str(row["path"]).lower())
    digest_payload = {
        "fixtures": [
            {"path": str(row["path"]), "sha256": str(row["sha256"])} for row in fixtures
        ]
    }
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.rc_baseline_lock",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "fixtures": fixtures,
        "fixture_set_sha256": hash_dict(digest_payload),
    }


def _run(cmd: list[str], *, cwd: Path) -> tuple[bool, str]:
    completed = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return completed.returncode == 0, output


def write_rc_baseline_lock(
    repo_root: Path,
    *,
    output_path: Path,
    regenerate: bool,
    validation_output_root: Path,
    fixture_relpaths: Sequence[str] = DEFAULT_FIXTURE_RELPATHS,
) -> tuple[bool, list[str]]:
    failures: list[str] = []
    if regenerate:
        cmd = [
            sys.executable,
            "scripts/regenerate_baseline_fixtures.py",
            "--output-root",
            str(validation_output_root),
        ]
        ok, output = _run(cmd, cwd=repo_root)
        if not ok:
            failures.append("fixture regeneration failed")
            if output:
                failures.append(output)
            return False, failures

    try:
        payload = build_rc_baseline_lock(repo_root, fixture_relpaths)
    except Exception as exc:  # pragma: no cover - exercised via unit tests
        failures.append(str(exc))
        return False, failures

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return True, []


def main() -> int:
    parser = argparse.ArgumentParser(description="Freeze RC baseline fixtures and lock hashes.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/specs/milestones/rc_baseline_lock_2026-02-16.json"),
        help="Path to write the RC baseline lock manifest.",
    )
    parser.add_argument(
        "--regenerate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Regenerate baseline fixtures before locking hashes (default: true).",
    )
    parser.add_argument(
        "--validation-output-root",
        type=Path,
        default=Path("results/validation_rc_lock"),
        help="Validation output root when --regenerate is enabled.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    validation_output_root = (
        args.validation_output_root
        if args.validation_output_root.is_absolute()
        else (repo_root / args.validation_output_root)
    )

    ok, failures = write_rc_baseline_lock(
        repo_root,
        output_path=output_path,
        regenerate=bool(args.regenerate),
        validation_output_root=validation_output_root,
    )
    if not ok:
        print("RC baseline lock: FAIL")
        for line in failures:
            print(f" - {line}")
        return 1

    print("RC baseline lock: PASS")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
