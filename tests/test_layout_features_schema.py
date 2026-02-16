from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from photonstrust.verification.layout_features import extract_parallel_waveguide_runs_from_request


def test_layout_parallel_runs_schema_minimal_instance():
    result = extract_parallel_waveguide_runs_from_request(
        {
            "routes": [
                {"route_id": "wg_a", "width_um": 0.5, "points_um": [[0.0, 0.0], [100.0, 0.0]]},
                {"route_id": "wg_b", "width_um": 0.5, "points_um": [[0.0, 1.0], [100.0, 1.0]]},
            ],
            "layout_extract": {"max_gap_um": 5.0, "min_parallel_length_um": 1.0},
        }
    )

    schema_path = Path("schemas") / "photonstrust.layout_parallel_runs.v0_1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=result, schema=schema)

