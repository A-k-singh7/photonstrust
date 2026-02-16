"""Measurement bundle ingestion into a local open registry.

Registry location (default):
- datasets/measurements/open/<dataset_id>/
  - measurement_bundle.json
  - data/... (copied referenced files)
  - index.json (registry index at datasets/measurements/open/index.json)
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.measurements._paths import open_measurements_dir
from photonstrust.measurements.schema import measurement_bundle_schema_path, validate_instance
from photonstrust.utils import hash_dict


def ingest_measurement_bundle_file(
    bundle_path: str | Path,
    *,
    open_root: str | Path | None = None,
    overwrite: bool = False,
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

    open_root_path = Path(open_root) if open_root is not None else open_measurements_dir()
    open_root_path.mkdir(parents=True, exist_ok=True)
    target_dir = open_root_path / dataset_id
    target_dir.mkdir(parents=True, exist_ok=True)

    target_manifest = target_dir / "measurement_bundle.json"
    if target_manifest.exists() and not overwrite:
        raise FileExistsError(
            f"Measurement bundle already exists: {dataset_id}. "
            f"Use overwrite=True to replace {target_manifest}."
        )

    # Verify and copy files.
    files = bundle.get("files", []) or []
    for entry in files:
        rel_path = str(entry["path"]).replace("\\", "/")
        sha_expected = str(entry["sha256"]).lower()
        src = _resolve_rel_file(bundle_dir, rel_path)
        sha_actual = _sha256_file(src)
        if sha_actual != sha_expected:
            raise ValueError(f"sha256 mismatch for {rel_path}: expected={sha_expected} actual={sha_actual}")

    # Copy manifest first for provenance.
    shutil.copy2(bundle_path, target_manifest)
    for entry in files:
        rel_path = str(entry["path"]).replace("\\", "/")
        src = _resolve_rel_file(bundle_dir, rel_path)
        dst = (target_dir / rel_path).resolve()
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    _update_index(open_root_path, bundle, target_manifest)
    return target_manifest


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


def _update_index(open_root: Path, bundle: dict, manifest_path: Path) -> None:
    index_path = open_root / "index.json"
    index = []
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            index = []

    dataset_id = str(bundle.get("dataset_id", ""))
    record = {
        "dataset_id": dataset_id,
        "kind": bundle.get("kind"),
        "title": bundle.get("title"),
        "created_at": bundle.get("created_at"),
        "share_level": bundle.get("share_level"),
        "restrictions": bundle.get("restrictions"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "manifest_path": str(manifest_path.relative_to(open_root)).replace("\\", "/"),
        "bundle_hash": hash_dict(bundle),
    }

    replaced = False
    for idx, existing in enumerate(index):
        if str(existing.get("dataset_id")) == dataset_id:
            index[idx] = record
            replaced = True
            break
    if not replaced:
        index.append(record)
    index.sort(key=lambda r: str(r.get("dataset_id", "")).lower())
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

