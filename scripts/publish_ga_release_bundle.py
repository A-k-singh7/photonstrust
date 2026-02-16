"""Build GA release bundle manifest and optionally regenerate bundle artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.utils import hash_dict


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _run(cmd: list[str], *, cwd: Path) -> tuple[bool, str]:
    completed = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return completed.returncode == 0, output


def build_ga_release_bundle_manifest(
    repo_root: Path,
    *,
    bundle_root: Path,
    generated_at: str | None = None,
) -> dict:
    resolved_bundle_root = bundle_root if bundle_root.is_absolute() else (repo_root / bundle_root)
    if not resolved_bundle_root.exists():
        raise FileNotFoundError(f"missing bundle root: {resolved_bundle_root}")

    files: list[dict] = []
    for path in sorted(resolved_bundle_root.rglob("*"), key=lambda item: str(item).lower()):
        if not path.is_file():
            continue
        relpath = str(path.relative_to(resolved_bundle_root)).replace("\\", "/")
        files.append(
            {
                "path": relpath,
                "sha256": _sha256_file(path),
                "bytes": int(path.stat().st_size),
            }
        )

    if not files:
        raise ValueError(f"bundle root contains no files: {resolved_bundle_root}")

    file_digest = hash_dict(
        {
            "files": [
                {"path": str(row["path"]), "sha256": str(row["sha256"])} for row in files
            ]
        }
    )
    reliability_card_count = sum(1 for row in files if str(row["path"]).endswith("reliability_card.json"))

    return {
        "schema_version": "0.1",
        "kind": "photonstrust.ga_release_bundle_manifest",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "bundle_root": str(bundle_root).replace("\\", "/"),
        "file_count": len(files),
        "reliability_card_count": reliability_card_count,
        "files": files,
        "bundle_sha256": file_digest,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish GA release bundle manifest.")
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=Path("results/release_bundle"),
        help="Root directory for GA release bundle artifacts.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/specs/milestones/ga_release_bundle_manifest_2026-02-16.json"),
        help="Path to write GA bundle manifest JSON.",
    )
    parser.add_argument(
        "--rebuild-bundle",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Regenerate release bundle via scripts/bundle_release.py first (default: true).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    if args.rebuild_bundle:
        ok, output = _run([sys.executable, "scripts/bundle_release.py"], cwd=repo_root)
        if not ok:
            print("GA release bundle publish: FAIL")
            print(" - bundle generation failed")
            if output:
                print(f" - {output}")
            return 1

    try:
        manifest = build_ga_release_bundle_manifest(repo_root, bundle_root=args.bundle_root)
    except Exception as exc:
        print("GA release bundle publish: FAIL")
        print(f" - {exc}")
        return 1

    output_path = args.output if args.output.is_absolute() else (repo_root / args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print("GA release bundle publish: PASS")
    print(str(output_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
