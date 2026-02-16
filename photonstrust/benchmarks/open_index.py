"""Open benchmark index rebuild and consistency checks."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.benchmarks.schema import benchmark_bundle_schema_path, validate_instance
from photonstrust.utils import hash_dict


def rebuild_open_index(open_root: Path) -> list[dict]:
    """Rebuild deterministic index records from benchmark bundles."""

    bundle_paths = sorted(
        open_root.glob("*/benchmark_bundle.json"),
        key=lambda path: str(path.relative_to(open_root)).lower(),
    )

    records: list[dict] = []
    schema_path = benchmark_bundle_schema_path()
    for bundle_path in bundle_paths:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        try:
            validate_instance(bundle, schema_path, require_jsonschema=False)
        except Exception as exc:
            raise ValueError(f"{bundle_path}: schema validation failed: {exc}") from exc

        records.append(
            {
                "benchmark_id": str(bundle.get("benchmark_id", "")),
                "kind": bundle.get("kind"),
                "title": bundle.get("title"),
                "created_at": bundle.get("created_at"),
                "bundle_path": str(bundle_path.relative_to(open_root)).replace("\\", "/"),
                "bundle_hash": hash_dict(bundle),
            }
        )

    records.sort(key=lambda row: (str(row.get("benchmark_id", "")).lower(), str(row.get("bundle_path", "")).lower()))
    return records


def check_open_index_consistency(open_root: Path) -> tuple[bool, list[str]]:
    """Check that open benchmark index.json exists and matches rebuilt records."""

    index_path = open_root / "index.json"
    if not index_path.exists():
        return False, [f"missing index file: {index_path}"]

    try:
        current_index = json.loads(index_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"failed to parse index file {index_path}: {exc}"]

    if not isinstance(current_index, list):
        return False, [f"index file must contain a JSON list: {index_path}"]

    try:
        rebuilt = rebuild_open_index(open_root)
    except Exception as exc:
        return False, [str(exc)]

    if current_index == rebuilt:
        return True, []

    failures = ["index.json does not match rebuilt bundle metadata"]
    failures.append(f"index entries={len(current_index)} rebuilt entries={len(rebuilt)}")
    current_ids = sorted(str(entry.get("benchmark_id", "")) for entry in current_index if isinstance(entry, dict))
    rebuilt_ids = sorted(str(entry.get("benchmark_id", "")) for entry in rebuilt)
    if current_ids != rebuilt_ids:
        failures.append(f"benchmark_id mismatch: index={current_ids} rebuilt={rebuilt_ids}")

    return False, failures
