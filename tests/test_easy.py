"""Tests for photonstrust.easy high-level API."""

import pytest

from photonstrust.easy import (
    simulate_qkd_link,
    compare_protocols,
    design_pic,
    plan_network,
    plan_satellite,
    QKDLinkResult,
    ProtocolComparison,
    PICDesignResult,
    NetworkPlan,
    SatellitePlan,
)


# ---------------------------------------------------------------------------
# simulate_qkd_link
# ---------------------------------------------------------------------------


class TestSimulateQKDLink:
    """Tests for the simulate_qkd_link power function."""

    def test_default_args(self):
        """simulate_qkd_link() returns QKDLinkResult with default args."""
        result = simulate_qkd_link(include_uncertainty=False)
        assert isinstance(result, QKDLinkResult)
        assert len(result.results) > 0

    def test_single_distance_sweep(self):
        """Float distance_km produces a sweep from 0 to that distance."""
        result = simulate_qkd_link(distance_km=50.0, include_uncertainty=False)
        assert isinstance(result, QKDLinkResult)
        distances = [r.distance_km for r in result.results]
        assert distances[0] == 0.0
        assert distances[-1] == pytest.approx(50.0)

    def test_list_distances(self):
        """List of distances produces exactly those evaluation points."""
        result = simulate_qkd_link(distance_km=[10, 20, 30], include_uncertainty=False)
        assert len(result.results) == 3
        assert [r.distance_km for r in result.results] == [10.0, 20.0, 30.0]

    def test_dict_distances(self):
        """Dict distance spec is expanded correctly: 0, 10, 20, 30, 40, 50 -> 6 points."""
        result = simulate_qkd_link(
            distance_km={"start": 0, "stop": 50, "step": 10},
            include_uncertainty=False,
        )
        assert len(result.results) == 6

    def test_protocol_tf_qkd(self):
        """TF-QKD protocol works via the easy API."""
        result = simulate_qkd_link(
            protocol="tf_qkd", distance_km=[10, 50], include_uncertainty=False,
        )
        assert isinstance(result, QKDLinkResult)
        assert len(result.results) == 2

    def test_protocol_cv_qkd(self):
        """CV-QKD protocol works via the easy API."""
        result = simulate_qkd_link(
            protocol="cv_qkd", distance_km=[10, 20], include_uncertainty=False,
        )
        assert isinstance(result, QKDLinkResult)

    def test_summary_non_empty(self):
        """summary() returns a non-empty string."""
        result = simulate_qkd_link(distance_km=[10], include_uncertainty=False)
        s = result.summary()
        assert isinstance(s, str)
        assert len(s) > 0

    def test_as_dict(self):
        """as_dict() returns a dict with results and config keys."""
        result = simulate_qkd_link(distance_km=[10], include_uncertainty=False)
        d = result.as_dict()
        assert isinstance(d, dict)
        assert "results" in d
        assert "config" in d

    def test_max_distance_km(self):
        """max_distance_km() returns a non-negative float."""
        result = simulate_qkd_link(distance_km=[5, 10, 20], include_uncertainty=False)
        md = result.max_distance_km()
        assert isinstance(md, float)
        assert md >= 0.0

    def test_key_rate_at(self):
        """key_rate_at() returns a float >= 0 for a known distance."""
        result = simulate_qkd_link(distance_km=[10, 20], include_uncertainty=False)
        rate = result.key_rate_at(10)
        assert isinstance(rate, float)
        assert rate >= 0.0


# ---------------------------------------------------------------------------
# compare_protocols
# ---------------------------------------------------------------------------


class TestCompareProtocols:
    """Tests for the compare_protocols power function."""

    def test_two_protocols(self):
        """Comparing two protocols returns a ProtocolComparison with both."""
        comp = compare_protocols(
            protocols=["bb84", "bbm92"],
            distances={"start": 0, "stop": 30, "step": 15},
        )
        assert isinstance(comp, ProtocolComparison)
        # The registry normalises bb84 -> bb84_decoy
        assert len(comp.protocols) == 2

    def test_winner_at(self):
        """winner_at() returns a protocol name string."""
        comp = compare_protocols(
            protocols=["bb84", "bbm92"],
            distances={"start": 0, "stop": 30, "step": 15},
        )
        winner = comp.winner_at(10)
        assert isinstance(winner, str)
        assert len(winner) > 0

    @pytest.mark.slow
    def test_all_protocols(self):
        """Comparing all protocols with explicit distances works."""
        comp = compare_protocols(
            protocols=None,
            distances={"start": 0, "stop": 50, "step": 25},
        )
        assert isinstance(comp, ProtocolComparison)
        # Some protocols may be skipped due to applicability checks
        assert len(comp.protocols) >= 1

    def test_summary_contains_protocol_names(self):
        """summary() includes the protocol names being compared."""
        comp = compare_protocols(
            protocols=["bb84", "bbm92"],
            distances=[10, 20],
        )
        s = comp.summary()
        assert isinstance(s, str)
        # Should contain at least one of the normalised protocol names
        assert "bb84_decoy" in s or "bbm92" in s


# ---------------------------------------------------------------------------
# design_pic
# ---------------------------------------------------------------------------


class TestDesignPIC:
    """Tests for the design_pic power function."""

    def test_basic_pic(self):
        """Basic PIC with two MMIs and one connection."""
        result = design_pic(
            components=["mmi_2x2", "mmi_2x2"],
            connections=[{"from": (0, "out1"), "to": (1, "in1")}],
        )
        assert isinstance(result, PICDesignResult)
        assert len(result.netlist["nodes"]) == 2
        assert len(result.netlist["edges"]) == 1

    def test_summary(self):
        """PICDesignResult.summary() returns a non-empty string."""
        result = design_pic(components=["mmi_2x2"], connections=[])
        s = result.summary()
        assert isinstance(s, str)
        assert "PIC netlist" in s

    def test_as_dict(self):
        """as_dict() returns a dict."""
        result = design_pic(components=["mmi_2x2"], connections=[])
        d = result.as_dict()
        assert isinstance(d, dict)
        assert "netlist" in d


# ---------------------------------------------------------------------------
# plan_network
# ---------------------------------------------------------------------------


class TestPlanNetwork:
    """Tests for the plan_network power function."""

    def test_three_node_network(self):
        """3-node linear network produces topology with paths."""
        result = plan_network(
            nodes=["A", "B", "C"],
            links=[
                {"a": "A", "b": "B", "distance_km": 20},
                {"a": "B", "b": "C", "distance_km": 30},
            ],
        )
        assert isinstance(result, NetworkPlan)
        assert len(result.topology["nodes"]) == 3
        assert len(result.topology["links"]) == 2
        assert len(result.paths) >= 1

    def test_summary(self):
        """NetworkPlan.summary() returns a non-empty string."""
        result = plan_network(
            nodes=["X", "Y"],
            links=[{"a": "X", "b": "Y", "distance_km": 10}],
        )
        s = result.summary()
        assert isinstance(s, str)
        assert "Network" in s

    def test_as_dict(self):
        """as_dict() returns a dict."""
        result = plan_network(
            nodes=["X", "Y"],
            links=[{"a": "X", "b": "Y", "distance_km": 10}],
        )
        d = result.as_dict()
        assert isinstance(d, dict)
        assert "topology" in d


# ---------------------------------------------------------------------------
# plan_satellite
# ---------------------------------------------------------------------------


class TestPlanSatellite:
    """Tests for the plan_satellite power function."""

    def test_default_leo(self):
        """Default LEO satellite plan returns a SatellitePlan."""
        result = plan_satellite()
        assert isinstance(result, SatellitePlan)
        assert result.constellation is not None
        assert result.schedule["n_passes"] >= 0

    def test_custom_altitude(self):
        """Custom altitude is reflected in constellation config."""
        result = plan_satellite(orbit_altitude_km=600)
        assert isinstance(result, SatellitePlan)
        assert result.constellation["altitude_km"] == 600

    def test_summary(self):
        """SatellitePlan.summary() returns a non-empty string."""
        result = plan_satellite()
        s = result.summary()
        assert isinstance(s, str)
        assert "Constellation" in s or "Scheduled" in s

    def test_as_dict(self):
        """as_dict() returns a dict."""
        result = plan_satellite()
        d = result.as_dict()
        assert isinstance(d, dict)
        assert "schedule" in d


# ---------------------------------------------------------------------------
# QKDLinkResult.summary() content checks
# ---------------------------------------------------------------------------


class TestResultDetails:
    """Verify result wrapper content."""

    def test_summary_contains_protocol(self):
        """QKDLinkResult.summary() mentions the protocol name."""
        result = simulate_qkd_link(
            protocol="bb84", distance_km=[10], include_uncertainty=False,
        )
        s = result.summary()
        # Normalised name should appear
        assert "bb84" in s.lower()

    def test_comparison_summary_contains_protocols(self):
        """ProtocolComparison.summary() mentions evaluated protocol names."""
        comp = compare_protocols(
            protocols=["bb84", "bbm92"],
            distances=[10],
        )
        s = comp.summary()
        assert "bb84_decoy" in s or "bbm92" in s


# ---------------------------------------------------------------------------
# Top-level import
# ---------------------------------------------------------------------------


class TestTopLevelImport:
    """Verify that power functions are importable from the top-level package."""

    def test_import_simulate_qkd_link(self):
        from photonstrust import simulate_qkd_link as fn
        assert callable(fn)

    def test_import_compare_protocols(self):
        from photonstrust import compare_protocols as fn
        assert callable(fn)

    def test_import_design_pic(self):
        from photonstrust import design_pic as fn
        assert callable(fn)

    def test_import_plan_network(self):
        from photonstrust import plan_network as fn
        assert callable(fn)

    def test_import_plan_satellite(self):
        from photonstrust import plan_satellite as fn
        assert callable(fn)
