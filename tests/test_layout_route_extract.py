from __future__ import annotations

import pytest

from photonstrust.layout.route_extract import extract_parallel_run_segments


def test_extract_parallel_runs_simple_horizontal_merges_colinear_points():
    routes = [
        {
            "route_id": "wg_a",
            "width_um": 0.5,
            "points_um": [[0.0, 0.0], [50.0, 0.0], [100.0, 0.0]],  # redundant interior point
        },
        {
            "route_id": "wg_b",
            "width_um": 0.5,
            "points_um": [[0.0, 1.0], [100.0, 1.0]],
        },
    ]
    runs = extract_parallel_run_segments(routes)
    assert len(runs) == 1
    r = runs[0]
    assert r["route_a"] == "wg_a"
    assert r["route_b"] == "wg_b"
    assert r["orientation"] == "horizontal"
    assert abs(float(r["parallel_length_um"]) - 100.0) < 1e-9

    # Centerline separation = 1.0, edge gap = 1.0 - (0.25 + 0.25) = 0.5 um
    assert abs(float(r["gap_um"]) - 0.5) < 1e-9


def test_extract_parallel_runs_lshape_filters_by_max_gap():
    routes = [
        {"route_id": "a", "width_um": 0.5, "points_um": [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0]]},
        {"route_id": "b", "width_um": 0.5, "points_um": [[0.0, 1.0], [50.0, 1.0], [50.0, 100.0]]},
    ]
    runs = extract_parallel_run_segments(routes, max_gap_um=5.0)
    # The vertical segments are far apart (x=100 vs x=50) and should be filtered out.
    assert len(runs) == 1
    r = runs[0]
    assert r["orientation"] == "horizontal"
    assert abs(float(r["parallel_length_um"]) - 50.0) < 1e-9


def test_extract_parallel_runs_rejects_diagonal_segments():
    routes = [
        {"route_id": "bad", "width_um": 0.5, "points_um": [[0.0, 0.0], [10.0, 10.0]]},
        {"route_id": "ok", "width_um": 0.5, "points_um": [[0.0, 0.0], [10.0, 0.0]]},
    ]
    with pytest.raises(ValueError, match="non-Manhattan"):
        extract_parallel_run_segments(routes)

