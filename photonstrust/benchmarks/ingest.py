"""Open benchmark bundle ingestion.

This module supports taking a benchmark bundle (JSON) and placing it into a
versioned on-disk registry under `datasets/benchmarks/open/`.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.benchmarks._paths import open_benchmarks_dir
from photonstrust.benchmarks.schema import benchmark_bundle_schema_path, validate_instance
from photonstrust.utils import hash_dict


def ingest_bundle_file(
    bundle_path: str | Path,
    *,
    open_root: str | Path | None = None,
    overwrite: bool = False,
) -> Path:
    bundle_path = Path(bundle_path)
    if not bundle_path.exists():
        raise FileNotFoundError(f"Benchmark bundle not found: {bundle_path}")

    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    validate_instance(bundle, benchmark_bundle_schema_path())

    open_root_path = Path(open_root) if open_root is not None else open_benchmarks_dir()
    open_root_path.mkdir(parents=True, exist_ok=True)

    benchmark_id = str(bundle["benchmark_id"])
    target_dir = open_root_path / benchmark_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_bundle_path = target_dir / "benchmark_bundle.json"

    if target_bundle_path.exists() and not overwrite:
        raise FileExistsError(
            f"Benchmark already exists: {benchmark_id}. "
            f"Use overwrite=True to replace {target_bundle_path}."
        )

    shutil.copy2(bundle_path, target_bundle_path)
    _update_index(open_root_path, bundle, target_bundle_path)
    return target_bundle_path


def _update_index(open_root: Path, bundle: dict, bundle_path: Path) -> None:
    index_path = open_root / "index.json"
    index = []
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            index = []

    benchmark_id = str(bundle.get("benchmark_id", ""))
    record = {
        "benchmark_id": benchmark_id,
        "kind": bundle.get("kind"),
        "title": bundle.get("title"),
        "created_at": bundle.get("created_at"),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "bundle_path": str(bundle_path.relative_to(open_root)).replace("\\", "/"),
        "bundle_hash": hash_dict(bundle),
    }

    # Upsert by benchmark_id
    replaced = False
    for idx, existing in enumerate(index):
        if str(existing.get("benchmark_id")) == benchmark_id:
            index[idx] = record
            replaced = True
            break
    if not replaced:
        index.append(record)

    index.sort(key=lambda r: str(r.get("benchmark_id", "")).lower())
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")

