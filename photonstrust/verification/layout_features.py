"""Layout feature extraction helpers for verification (v0.1).

This module provides a thin, validation-heavy wrapper around route-level
feature extraction so performance DRC checks can consume deterministic geometry
features without binding to a specific layout tool (KLayout/gdsfactory).
"""

from __future__ import annotations

from typing import Any

from photonstrust.layout.route_extract import extract_parallel_run_segments


def extract_parallel_waveguide_runs_from_request(request: dict) -> dict[str, Any]:
    """Extract parallel waveguide run segments from a request payload.

    Expected payload fields:
      - routes: list[route]
      - layout_extract: optional object with:
        - max_gap_um: number | null
        - min_parallel_length_um: number
        - coord_tol_um: number
    """

    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    routes = request.get("routes")
    if not isinstance(routes, list):
        raise ValueError("routes must be provided as a list")

    settings = request.get("layout_extract")
    settings = settings if isinstance(settings, dict) else {}

    max_gap_um = settings.get("max_gap_um", None)
    if max_gap_um is not None:
        max_gap_um = float(max_gap_um)

    min_parallel_length_um = float(settings.get("min_parallel_length_um", 0.0) or 0.0)
    coord_tol_um = float(settings.get("coord_tol_um", 1e-9) or 1e-9)

    runs = extract_parallel_run_segments(
        routes,
        max_gap_um=max_gap_um,
        min_parallel_length_um=min_parallel_length_um,
        coord_tol_um=coord_tol_um,
    )

    summary = {
        "parallel_runs_count": int(len(runs)),
        "min_gap_um": min((float(r.get("gap_um")) for r in runs), default=None),
        "max_parallel_length_um": max((float(r.get("parallel_length_um")) for r in runs), default=None),
    }

    return {
        "schema_version": "0.1",
        "kind": "pic.parallel_run_segments",
        "settings": {
            "max_gap_um": float(max_gap_um) if max_gap_um is not None else None,
            "min_parallel_length_um": float(min_parallel_length_um),
            "coord_tol_um": float(coord_tol_um),
        },
        "summary": summary,
        "parallel_runs": runs,
    }

