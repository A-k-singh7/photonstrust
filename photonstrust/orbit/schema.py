"""OrbitVerify pass envelope schema validation."""

from __future__ import annotations

import json
from pathlib import Path


class SchemaValidationError(ValueError):
    """Raised when an Orbit pass envelope config fails schema validation."""


def orbit_pass_schema_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "schemas" / "photonstrust.orbit_pass_envelope.v0_1.schema.json"


def validate_orbit_pass_config(config: dict, *, require_jsonschema: bool = False) -> None:
    """Validate an Orbit pass envelope config dict against the JSON Schema.

    `jsonschema` is treated as an optional runtime dependency for OSS use. The
    schema is still published and validated in CI/tests. Set
    `require_jsonschema=True` to enforce that the dependency is installed.
    """

    try:
        from jsonschema import validate
    except Exception as exc:  # pragma: no cover - optional runtime dependency
        if require_jsonschema:
            raise RuntimeError(
                "jsonschema is required for Orbit pass schema validation. "
                "Install dev dependencies (e.g., photonstrust[dev])."
            ) from exc
        return

    schema = json.loads(orbit_pass_schema_path().read_text(encoding="utf-8"))
    try:
        validate(instance=config, schema=schema)
    except Exception as exc:
        raise SchemaValidationError(str(exc)) from exc

