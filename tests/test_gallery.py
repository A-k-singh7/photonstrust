"""Tests for photonstrust.gallery scenario gallery."""

import pytest

from photonstrust.gallery import (
    list_scenarios,
    load_scenario,
    describe_scenario,
    scenario_names,
    run_scenario,
    ScenarioMeta,
)


class TestListScenarios:
    """Tests for the list_scenarios function."""

    def test_returns_at_least_15(self):
        """list_scenarios() returns >= 15 entries."""
        all_scenarios = list_scenarios()
        assert len(all_scenarios) >= 15

    def test_filter_by_category_qkd(self):
        """list_scenarios(category='qkd') returns only QKD scenarios."""
        qkd = list_scenarios(category="qkd")
        assert len(qkd) > 0
        assert all(s.category == "qkd" for s in qkd)

    def test_filter_by_difficulty_beginner(self):
        """list_scenarios(difficulty='beginner') returns only beginner scenarios."""
        beginners = list_scenarios(difficulty="beginner")
        assert len(beginners) > 0
        assert all(s.difficulty == "beginner" for s in beginners)

    def test_combined_filter(self):
        """Combined category + difficulty filter narrows results correctly."""
        filtered = list_scenarios(category="qkd", difficulty="beginner")
        assert len(filtered) > 0
        assert all(s.category == "qkd" and s.difficulty == "beginner" for s in filtered)
        # Must be a subset of each individual filter
        assert len(filtered) <= len(list_scenarios(category="qkd"))
        assert len(filtered) <= len(list_scenarios(difficulty="beginner"))


class TestScenarioNames:
    """Tests for scenario_names and uniqueness."""

    def test_all_names_unique(self):
        """All scenario names are unique."""
        names = scenario_names()
        assert len(names) == len(set(names))

    def test_names_are_sorted(self):
        """scenario_names() returns a sorted list."""
        names = scenario_names()
        assert names == sorted(names)


class TestLoadScenario:
    """Tests for load_scenario."""

    def test_bb84_metro_returns_dict(self):
        """load_scenario('bb84_metro') returns a dict with expected keys."""
        cfg = load_scenario("bb84_metro")
        assert isinstance(cfg, dict)
        assert "protocol" in cfg
        assert cfg["protocol"] == "bb84"
        assert cfg["distance_km"] == 20

    def test_unknown_raises_key_error(self):
        """Unknown scenario name raises KeyError."""
        with pytest.raises(KeyError, match="Unknown scenario"):
            load_scenario("nonexistent_scenario_xyz")


class TestDescribeScenario:
    """Tests for describe_scenario."""

    def test_bb84_metro_description_length(self):
        """describe_scenario('bb84_metro') returns a string > 100 chars."""
        desc = describe_scenario("bb84_metro")
        assert isinstance(desc, str)
        assert len(desc) > 100


class TestRunScenario:
    """Tests for run_scenario — integration with easy.py."""

    def test_run_bb84_metro(self):
        """run_scenario('bb84_metro') completes and result has .summary()."""
        result = run_scenario("bb84_metro")
        summary = result.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_run_network_3node(self):
        """run_scenario('network_3node') completes without error."""
        result = run_scenario("network_3node")
        summary = result.summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_run_unknown_raises(self):
        """run_scenario with unknown name raises KeyError."""
        with pytest.raises(KeyError, match="Unknown scenario"):
            run_scenario("totally_fake_scenario")
