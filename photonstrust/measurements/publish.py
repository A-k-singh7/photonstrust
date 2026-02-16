"""Artifact pack publisher for measurement bundles (local, opt-in).

This does not upload anything; it creates a shareable folder (and optional zip)
after running conservative redaction scans.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.measurements.redaction import scan_measurement_bundle
from photonstrust.measurements.schema import (
    artifact_pack_manifest_schema_path,
    measurement_bundle_schema_path,
    validate_instance,
)
from photonstrust.utils import hash_dict


def publish_artifact_pack(
    bundle_path: str | Path,
    output_dir: str | Path,
    *,
    pack_id: str | None = None,
    allow_risk: bool = False,
    zip_pack: bool = True,
) -> Path:
    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        raise FileNotFoundError(f"Measurement bundle not found: {bundle_path}")

    bundle_dir = bundle_path.parent.resolve()
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    validate_instance(bundle, measurement_bundle_schema_path())

    dataset_id = str(bundle["dataset_id"]).strip()
    if not dataset_id:
        raise ValueError("measurement_bundle.dataset_id must be non-empty")

    generated_at = datetime.now(timezone.utc).isoformat()
    pack_id = pack_id or f"{dataset_id}_{generated_at.replace(':', '').replace('-', '')}"
    pack_root = Path(output_dir) / pack_id
    pack_root.mkdir(parents=True, exist_ok=True)

    # Copy manifest + referenced files into pack root.
    manifest_dst = pack_root / "measurement_bundle.json"
    shutil.copy2(bundle_path, manifest_dst)
    file_entries = bundle.get("files", []) or []

    rel_paths = ["measurement_bundle.json"]
    for entry in file_entries:
        rel_path = str(entry["path"]).replace("\\", "/")
        src = _resolve_rel_file(bundle_dir, rel_path)
        sha_expected = str(entry["sha256"]).lower()
        sha_actual = _sha256_file(src)
        if sha_actual != sha_expected:
            raise ValueError(f"sha256 mismatch for {rel_path}: expected={sha_expected} actual={sha_actual}")

        dst = (pack_root / rel_path).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        rel_paths.append(rel_path)

    # Scan for secrets/sensitive files.
    issues = scan_measurement_bundle(pack_root, file_paths=rel_paths)
    if issues and not allow_risk:
        raise ValueError(f"Redaction scan failed with issues: {issues}")

    scan_status = "pass"
    if issues and allow_risk:
        scan_status = "overridden"
    elif issues:
        scan_status = "fail"

    zip_path = None
    if zip_pack:
        zip_base = str((Path(output_dir) / pack_id).resolve())
        zip_out = shutil.make_archive(zip_base, "zip", root_dir=str(pack_root))
        zip_path = str(Path(zip_out).name)

    manifest = {
        "schema_version": "0",
        "generated_at": generated_at,
        "pack_id": str(pack_id),
        "measurement_bundle_path": "measurement_bundle.json",
        "zip_path": zip_path,
        "scan": {"status": scan_status, "issues": issues},
        "provenance": {
            "config_hash": (bundle.get("links", {}) or {}).get("config_hash"),
            "bundle_hash": hash_dict(bundle),
            "photonstrust_version": _photonstrust_version(),
            "python": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }

    pack_manifest_path = pack_root / "artifact_pack_manifest.json"
    pack_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    validate_instance(manifest, artifact_pack_manifest_schema_path(), require_jsonschema=False)

    return pack_root


def _resolve_rel_file(bundle_dir: Path, rel_path: str) -> Path:
    if not rel_path or rel_path.startswith("/") or rel_path.startswith("..") or "/.." in rel_path:
        raise ValueError(f"Illegal bundle file path: {rel_path!r}")
    src = (bundle_dir / rel_path).resolve()
    if bundle_dir not in src.parents:
        raise ValueError(f"Path traversal detected: {rel_path!r}")
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"Referenced file not found: {rel_path} (resolved: {src})")
    return src


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _photonstrust_version() -> str | None:
    try:
        from importlib.metadata import version

        return version("photonstrust")
    except Exception:
        try:
            root = Path(__file__).resolve().parents[2]
            pyproject = root / "pyproject.toml"
            if not pyproject.exists():
                return None
            for line in pyproject.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip("\"'")
        except Exception:
            return None
    return None

