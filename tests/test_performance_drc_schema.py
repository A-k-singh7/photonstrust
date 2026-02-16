from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate

from photonstrust.verification.performance_drc import run_parallel_waveguide_crosstalk_check


def test_performance_drc_schema_minimal_instance(tmp_path: Path):
    report = run_parallel_waveguide_crosstalk_check(
        {
            "gap_um": 0.6,
            "parallel_length_um": 1000.0,
            "wavelength_sweep_nm": [1540.0, 1550.0, 1560.0],
            "target_xt_db": -40.0,
            "pdk": {"name": "generic_silicon_photonics"},
        },
        output_dir=tmp_path,
        run_id="test_run",
    )

    schema_path = Path("schemas") / "photonstrust.performance_drc.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)


def test_performance_drc_schema_routes_instance(tmp_path: Path):
    report = run_parallel_waveguide_crosstalk_check(
        {
            "routes": [
                {"route_id": "wg_a", "width_um": 0.5, "points_um": [[0.0, 0.0], [100.0, 0.0]]},
                {"route_id": "wg_b", "width_um": 0.5, "points_um": [[0.0, 1.0], [100.0, 1.0]]},
            ],
            "layout_extract": {"max_gap_um": 5.0, "min_parallel_length_um": 1.0},
            "wavelength_sweep_nm": [1550.0],
            "target_xt_db": -40.0,
            "pdk": {"name": "generic_silicon_photonics"},
            "loss_budget": {
                "max_route_loss_db": 1.0,
                "max_bends_per_route": 4,
                "max_crossings_per_route": 2,
            },
        },
        output_dir=tmp_path,
        run_id="test_run_routes",
    )

    schema_path = Path("schemas") / "photonstrust.performance_drc.v0.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validate(instance=report, schema=schema)

    assert report["results"]["loss_budget"] is not None
    assert isinstance(report["results"]["violations"], list)
    assert isinstance(report["results"]["violation_summary"], dict)
    assert isinstance(report["results"]["drc"]["violations_annotated"], list)
