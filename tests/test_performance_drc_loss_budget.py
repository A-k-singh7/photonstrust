from __future__ import annotations

from photonstrust.verification.performance_drc import run_parallel_waveguide_crosstalk_check


def test_route_loss_budget_and_annotated_violations_present():
    report = run_parallel_waveguide_crosstalk_check(
        {
            "routes": [
                {"route_id": "route_a", "width_um": 0.5, "points_um": [[0.0, 0.0], [100.0, 0.0], [100.0, 100.0]]},
                {"route_id": "route_b", "width_um": 0.5, "points_um": [[50.0, -50.0], [50.0, 50.0]]},
                {"route_id": "route_c", "width_um": 0.5, "points_um": [[0.0, 1.0], [100.0, 1.0]]},
            ],
            "layout_extract": {"max_gap_um": 5.0, "min_parallel_length_um": 1.0},
            "wavelength_sweep_nm": [1550.0],
            "target_xt_db": -40.0,
            "pdk": {"name": "generic_silicon_photonics"},
            "loss_budget": {
                "waveguide_loss_db_per_cm": 2.0,
                "bend_loss_per_90deg_db": 0.005,
                "crossing_loss_db": 0.02,
                "max_route_loss_db": 0.01,
                "max_bends_per_route": 0,
                "max_crossings_per_route": 0,
            },
        }
    )

    assert report["results"]["status"] == "fail"

    loss_budget = report["results"]["loss_budget"]
    assert isinstance(loss_budget, dict)
    assert loss_budget["pass"] is False
    assert [r["route_id"] for r in loss_budget["routes"]] == ["route_a", "route_b", "route_c"]

    route_a = next(r for r in loss_budget["routes"] if r["route_id"] == "route_a")
    assert route_a["bend_count"] == 1
    assert route_a["crossing_count"] == 1
    assert route_a["route_loss_db"] > 0.01

    violations = report["results"]["violations"]
    assert violations
    for violation in violations:
        assert set(["id", "source", "code", "severity", "applicability", "entity_ref", "message", "location"]).issubset(
            violation.keys()
        )

    assert any(v["code"] == "pdrc.route_loss_budget" and v["applicability"] == "blocking" for v in violations)
    assert any(v["code"] == "pdrc.route_bend_count" and v["applicability"] == "reviewable" for v in violations)
    assert any(v["code"] == "pdrc.route_crossing_count" and v["applicability"] == "reviewable" for v in violations)
