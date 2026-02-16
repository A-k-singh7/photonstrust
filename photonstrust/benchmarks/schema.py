"""JSON schema validation utilities for benchmark bundles and repro packs."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.benchmarks._paths import schemas_dir


class SchemaValidationError(ValueError):
    """Raised when an instance fails schema validation."""


def _load_schema(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_instance(instance: dict, schema_path: Path, *, require_jsonschema: bool = True) -> None:
    try:
        from jsonschema import validate
    except Exception as exc:  # pragma: no cover - dev dependency
        if require_jsonschema:
            raise RuntimeError(
                "jsonschema is required for schema validation. "
                "Install dev dependencies (e.g., photonstrust[dev])."
            ) from exc
        return

    schema = _load_schema(schema_path)
    try:
        validate(instance=instance, schema=schema)
    except Exception as exc:
        raise SchemaValidationError(str(exc)) from exc


def benchmark_bundle_schema_path() -> Path:
    return schemas_dir() / "photonstrust.benchmark_bundle.v0.schema.json"


def repro_pack_manifest_schema_path() -> Path:
    return schemas_dir() / "photonstrust.repro_pack_manifest.v0.schema.json"
