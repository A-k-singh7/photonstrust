"""Verify GA release bundle manifest integrity and optional replay sample."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_ga_bundle_manifest(
    repo_root: Path,
    *,
    manifest_path: Path,
) -> tuple[bool, list[str], dict]:
    failures: list[str] = []
    resolved_manifest = manifest_path if manifest_path.is_absolute() else (repo_root / manifest_path)
    if not resolved_manifest.exists():
        return False, [f"missing manifest: {resolved_manifest}"], {}

    try:
        manifest = json.loads(resolved_manifest.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"failed to parse manifest: {exc}"], {}

    if not isinstance(manifest, dict):
        return False, ["manifest must be a JSON object"], {}

    kind = str(manifest.get("kind") or "")
    if kind != "photonstrust.ga_release_bundle_manifest":
        failures.append(f"unexpected manifest kind: {kind}")

    bundle_root_field = manifest.get("bundle_root")
    bundle_root = repo_root / Path(str(bundle_root_field))
    if not bundle_root.exists():
        failures.append(f"bundle root missing: {bundle_root}")

    files = manifest.get("files")
    if not isinstance(files, list):
        failures.append("manifest files field must be a list")
        return False, failures, manifest

    has_run_registry = False
    reliability_card_count = 0
    for index, item in enumerate(files):
        if not isinstance(item, dict):
            failures.append(f"files[{index}] must be an object")
            continue
        relpath = str(item.get("path") or "")
        expected_sha256 = str(item.get("sha256") or "")
        if not relpath:
            failures.append(f"files[{index}] missing path")
            continue

        file_path = bundle_root / Path(relpath)
        if not file_path.exists():
            failures.append(f"missing bundle file: {relpath}")
            continue
        actual_sha256 = _sha256_file(file_path)
        if expected_sha256 != actual_sha256:
            failures.append(f"hash mismatch for {relpath}")

        normalized = relpath.replace("\\", "/")
        if normalized == "run_registry.json":
            has_run_registry = True
        if normalized.endswith("reliability_card.json"):
            reliability_card_count += 1

    if not has_run_registry:
        failures.append("bundle missing run_registry.json")
    if reliability_card_count <= 0:
        failures.append("bundle has no reliability_card.json artifacts")

    return len(failures) == 0, failures, manifest


def run_replay_sample(
    repo_root: Path,
    *,
    replay_config: Path,
    replay_output: Path,
    timeout_seconds: float,
) -> tuple[bool, str]:
    config_path = replay_config if replay_config.is_absolute() else (repo_root / replay_config)
    output_path = replay_output if replay_output.is_absolute() else (repo_root / replay_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "photonstrust.cli",
        "run",
        str(config_path),
        "--output",
        str(output_path),
    ]
    completed = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    if completed.returncode != 0:
        return False, output

    run_registry = output_path / "run_registry.json"
    if not run_registry.exists():
        return False, f"replay output missing run registry: {run_registry}"
    return True, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify GA release bundle and replay sample.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("reports/specs/milestones/ga_release_bundle_manifest_2026-02-16.json"),
        help="Path to GA release bundle manifest JSON.",
    )
    parser.add_argument(
        "--run-replay",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Execute replay sample command after manifest verification (default: true).",
    )
    parser.add_argument(
        "--replay-config",
        type=Path,
        default=Path("configs/demo1_quick_smoke.yml"),
        help="Scenario config to run for replay sample verification.",
    )
    parser.add_argument(
        "--replay-output",
        type=Path,
        default=Path("results/ga_release/replay_sample"),
        help="Output directory for replay sample run.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=90.0,
        help="Replay command timeout in seconds (default: 90).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    ok, failures, _manifest = verify_ga_bundle_manifest(repo_root, manifest_path=args.manifest)
    if not ok:
        print("GA release bundle verify: FAIL")
        for line in failures:
            print(f" - {line}")
        return 1

    if args.run_replay:
        replay_ok, replay_output = run_replay_sample(
            repo_root,
            replay_config=args.replay_config,
            replay_output=args.replay_output,
            timeout_seconds=float(args.timeout),
        )
        if not replay_ok:
            print("GA release bundle verify: FAIL")
            print(" - replay sample failed")
            if replay_output:
                print(f" - {replay_output}")
            return 1

    print("GA release bundle verify: PASS")
    print(str(args.manifest if args.manifest.is_absolute() else (repo_root / args.manifest)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
