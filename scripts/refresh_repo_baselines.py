#!/usr/bin/env python3
"""Refresh reproducibility baselines used by nightly and release workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _run(cmd: list[str], *, cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _refresh_measurement_bundle_manifest(manifest_path: Path) -> int:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = payload.get("files")
    if not isinstance(entries, list):
        return 0

    updated = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rel_path = str(entry.get("path") or "").replace("\\", "/").strip()
        if not rel_path:
            continue
        file_path = manifest_path.parent / rel_path
        new_hash = _sha256(file_path)
        if str(entry.get("sha256") or "").lower() != new_hash:
            entry["sha256"] = new_hash
            updated += 1

    _write_json(manifest_path, payload)
    return updated


def refresh_measurement_fixtures(repo_root: Path) -> dict[str, int]:
    manifests = sorted((repo_root / "tests" / "fixtures").glob("**/measurement_bundle.json"))
    updated_entries = 0
    for manifest_path in manifests:
        updated_entries += _refresh_measurement_bundle_manifest(manifest_path)
    return {
        "manifest_count": len(manifests),
        "updated_entry_count": updated_entries,
    }


def _milestone_relpaths(repo_root: Path) -> list[str]:
    milestone_root = repo_root / "reports" / "specs" / "milestones"
    if not milestone_root.exists():
        return []
    relpaths: list[str] = []
    for path in sorted(milestone_root.iterdir()):
        if path.is_file():
            relpaths.append(str(path.relative_to(repo_root)).replace("\\", "/"))
    return relpaths


def normalize_milestones(repo_root: Path, python_exe: str) -> int:
    relpaths = _milestone_relpaths(repo_root)
    if relpaths:
        _run([python_exe, "-m", "pre_commit", "run", "--files", *relpaths], cwd=repo_root)
    return len(relpaths)


def refresh_release_gate(repo_root: Path, python_exe: str) -> None:
    _run([python_exe, "scripts/release/refresh_release_gate_packet.py"], cwd=repo_root)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh repo baselines used by nightly and release checks")
    parser.add_argument("--measurement-fixtures", action="store_true", help="Refresh measurement bundle fixture hashes")
    parser.add_argument("--release-gate", action="store_true", help="Refresh the tracked release gate packet + signature")
    parser.add_argument("--normalize-milestones", action="store_true", help="Run pre-commit normalization on tracked milestone artifacts")
    parser.add_argument("--all", action="store_true", help="Run all refresh steps")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected = bool(args.measurement_fixtures or args.release_gate or args.normalize_milestones or args.all)
    if not selected:
        args.all = True

    repo_root = _repo_root()
    python_exe = sys.executable
    summary: dict[str, object] = {"repo_root": str(repo_root)}

    if args.all or args.measurement_fixtures:
        summary["measurement_fixtures"] = refresh_measurement_fixtures(repo_root)

    if args.all or args.release_gate:
        refresh_release_gate(repo_root, python_exe)
        summary["release_gate_refreshed"] = True

    if args.all or args.normalize_milestones:
        summary["normalized_milestone_file_count"] = normalize_milestones(repo_root, python_exe)

    print(json.dumps(summary, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
