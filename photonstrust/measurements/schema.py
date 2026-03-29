"""JSON schema validation utilities for measurement bundles and artifact packs."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.measurements._paths import schemas_dir


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


def measurement_bundle_schema_path() -> Path:
    return schemas_dir() / "photonstrust.measurement_bundle.v0.schema.json"


def artifact_pack_manifest_schema_path() -> Path:
    return schemas_dir() / "photonstrust.artifact_pack_manifest.v0.schema.json"
