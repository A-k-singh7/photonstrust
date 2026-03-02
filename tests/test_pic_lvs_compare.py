from __future__ import annotations

import pytest

from photonstrust.pic.lvs import compare_schematic_vs_routes


def _demo_pic_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "pic_lvs_compare_routes",
        "profile": "pic_circuit",
        "metadata": {"title": "pic_lvs_compare_routes", "created_at": "2026-02-16"},
        "circuit": {"id": "c1", "wavelength_nm": 1550.0},
        "nodes": [
            {
                "id": "wg1",
                "kind": "pic.waveguide",
                "params": {"length_um": 100.0, "loss_db_per_cm": 2.0},
            },
            {
                "id": "ps1",
                "kind": "pic.phase_shifter",
                "params": {"phase_rad": 0.0, "insertion_loss_db": 0.2},
            },
        ],
        "edges": [
            {
                "id": "e1",
                "from": "wg1",
                "from_port": "out",
                "to": "ps1",
                "to_port": "in",
                "kind": "optical",
            },
        ],
    }


@pytest.mark.parametrize(
    ("route_row", "route_id"),
    [
        (
            {
                "route_id": "r_source_edge",
                "source": {
                    "edge": {
                        "from": "wg1",
                        "to": "ps1",
                    }
                },
            },
            "r_source_edge",
        ),
        (
            {
                "route_id": "r_ab",
                "a": {"node": "wg1", "port": "out"},
                "b": {"node": "ps1", "port": "in"},
            },
            "r_ab",
        ),
        (
            {
                "route_id": "r_from_to",
                "from": "wg1",
                "to": "ps1",
            },
            "r_from_to",
        ),
    ],
    ids=["source_edge", "a_b", "from_to"],
)
def test_compare_schematic_vs_routes_parses_metadata_routes_when_ports_omitted(route_row: dict, route_id: str) -> None:
    result = compare_schematic_vs_routes(
        graph=_demo_pic_graph(),
        routes={"schema_version": "0.1", "kind": "pic.routes", "routes": [route_row]},
        ports=None,
        coord_tol_um=1e-6,
    )

    assert result["settings"] == {"coord_tol_um": 1e-6, "ports_provided": False}
    assert result["summary"] == {
        "pass": True,
        "missing_connections": 0,
        "extra_connections": 0,
        "port_mapping_mismatches": 0,
        "unconnected_ports": 0,
    }
    assert result["observed"]["connections_count"] == 1
    assert result["observed"]["warnings"] == []
    assert result["observed"]["dangling_routes"] == []

    observed = result["observed"]["connections"][0]
    assert observed["route_id"] == route_id
    assert observed["a"] == {"node": "wg1", "port": "out"}
    assert observed["b"] == {"node": "ps1", "port": "in"}
