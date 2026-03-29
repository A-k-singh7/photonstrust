"""Graph schema validation."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.graph._paths import schemas_dir


class SchemaValidationError(ValueError):
    """Raised when a graph fails schema validation."""


def graph_schema_path() -> Path:
    return schemas_dir() / "photonstrust.graph.v0_1.schema.json"


def validate_graph(graph: dict, *, require_jsonschema: bool = False) -> None:
    """Validate a graph dict against the JSON Schema.

    The OSS core keeps `jsonschema` as a dev dependency. By default we do not
    hard-require it at runtime, but we still publish schemas and validate them
    in CI/tests. Set `require_jsonschema=True` to enforce schema validation.
    """

    try:
        from jsonschema import validate
    except Exception as exc:  # pragma: no cover - optional runtime dependency
        if require_jsonschema:
            raise RuntimeError(
                "jsonschema is required for graph schema validation. "
                "Install dev dependencies (e.g., photonstrust[dev])."
            ) from exc
        return

    schema = json.loads(graph_schema_path().read_text(encoding="utf-8"))
    try:
        validate(instance=graph, schema=schema)
    except Exception as exc:
        raise SchemaValidationError(str(exc)) from exc
