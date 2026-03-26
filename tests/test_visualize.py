"""Tests for photonstrust.visualize."""

from __future__ import annotations

from dataclasses import dataclass

import matplotlib

matplotlib.use("Agg", force=True)
import matplotlib.figure
import matplotlib.pyplot as plt
import numpy as np
import pytest

from photonstrust.visualize import (
    _plob_bound,
    plot_constellation,
    plot_detector_comparison,
    plot_eye_diagram,
    plot_heatmap,
    plot_loss_budget,
    plot_network_topology,
    plot_passband,
    plot_pic_spectrum,
    plot_protocol_comparison,
    plot_qber_budget,
    plot_rate_distance,
    plot_yield_histogram,
)


# ---------------------------------------------------------------------------
# Lightweight mock for QKDResult (avoids importing heavy simulation modules)
# ---------------------------------------------------------------------------


@dataclass
class _MockQKDResult:
    distance_km: float = 10.0
    key_rate_bps: float = 1000.0
    qber_total: float = 0.05
    fidelity: float = 0.95
    loss_db: float = 2.0
    protocol_name: str = "mock"
    q_dark: float = 0.01
    q_timing: float = 0.005
    q_misalignment: float = 0.008
    q_source: float = 0.002


def _make_results(n: int = 5, protocol: str = "mock") -> list[_MockQKDResult]:
    """Generate a list of mock QKDResult objects at varying distances."""
    return [
        _MockQKDResult(
            distance_km=d,
            key_rate_bps=max(1e4 * (1 - d / 100), 1e-12),
            loss_db=d * 0.2,
            protocol_name=protocol,
        )
        for d in np.linspace(1, 80, n)
    ]


# ---------------------------------------------------------------------------
# Helper / PLOB bound tests
# ---------------------------------------------------------------------------


class TestPlobBound:
    def test_zero_distance(self):
        rates = _plob_bound([0.0])
        assert len(rates) == 1
        # At 0 km loss is 0, eta = 1.0 => rate = 0 (edge: eta < 1 is False)
        assert rates[0] == 0.0

    def test_positive_distance(self):
        rates = _plob_bound([10.0], fiber_loss_db_per_km=0.2)
        # loss=2 dB, eta=10^(-0.2)~0.631, rate=-log2(1-0.631)~1.44
        assert rates[0] > 0
        assert rates[0] == pytest.approx(-np.log2(1 - 10 ** (-2.0 / 10.0)), rel=1e-6)

    def test_monotonically_decreasing(self):
        distances = [1.0, 10.0, 50.0, 100.0]
        rates = _plob_bound(distances)
        for i in range(len(rates) - 1):
            assert rates[i] >= rates[i + 1]


# ---------------------------------------------------------------------------
# Plot function tests
# ---------------------------------------------------------------------------


class TestPlotRateDistance:
    def test_returns_figure_list_input(self):
        fig = plot_rate_distance(_make_results())
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_returns_figure_dict_input(self):
        fig = plot_rate_distance({"BB84": _make_results(), "BBM92": _make_results()})
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_save_path(self, tmp_path):
        out = tmp_path / "rate_dist.png"
        fig = plot_rate_distance(_make_results(), save_path=out)
        assert out.exists()
        assert out.stat().st_size > 0
        plt.close(fig)


class TestPlotProtocolComparison:
    def test_returns_figure(self):
        comparison = {"A": _make_results(protocol="A"), "B": _make_results(protocol="B")}
        fig = plot_protocol_comparison(comparison)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotPicSpectrum:
    def test_returns_figure(self):
        sweep = {
            "wavelengths_nm": np.linspace(1540, 1560, 50).tolist(),
            "transmission_db": (-10 * np.random.rand(50)).tolist(),
        }
        fig = plot_pic_spectrum(sweep)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotNetworkTopology:
    def test_returns_figure(self):
        net = {
            "nodes": [
                {"node_id": "A", "location": [0, 0]},
                {"node_id": "B", "location": [1, 0]},
                {"node_id": "C", "location": [0.5, 1]},
            ],
            "links": [
                {"node_a": "A", "node_b": "B", "distance_km": 50},
                {"node_a": "B", "node_b": "C", "distance_km": 30},
            ],
        }
        fig = plot_network_topology(net)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_auto_layout_no_locations(self):
        net = {
            "nodes": [{"node_id": "X"}, {"node_id": "Y"}],
            "links": [{"node_a": "X", "node_b": "Y"}],
        }
        fig = plot_network_topology(net)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotConstellation:
    def test_returns_figure(self):
        passes = [
            {"start_time_s": 0, "end_time_s": 300, "max_elevation_deg": 60, "ground_station_id": "GS1"},
            {"start_time_s": 500, "end_time_s": 800, "max_elevation_deg": 45, "ground_station_id": "GS2"},
        ]
        fig = plot_constellation(passes)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotDetectorComparison:
    def test_returns_figure_defaults(self):
        fig = plot_detector_comparison()
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_custom_detectors(self):
        custom = {
            "det_a": {"pde": 0.5, "dark_counts_cps": 200, "jitter_ps_fwhm": 40},
            "det_b": {"pde": 0.3, "dark_counts_cps": 600, "jitter_ps_fwhm": 90},
        }
        fig = plot_detector_comparison(custom)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotYieldHistogram:
    def test_returns_figure(self):
        yr = {
            "metric_samples": np.random.normal(50, 5, 200).tolist(),
            "spec_min": 40,
            "spec_max": 60,
        }
        fig = plot_yield_histogram(yr)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotHeatmap:
    def test_returns_figure_2d(self):
        data = np.random.rand(5, 8)
        fig = plot_heatmap(data, x_label="Freq", y_label="Temp", value_label="Loss")
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_single_value(self):
        """Edge case: 1x1 array."""
        fig = plot_heatmap([[42.0]])
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotEyeDiagram:
    def test_returns_figure(self):
        t = np.linspace(0, 1000, 500)
        v = np.sin(2 * np.pi * t / 100) + 0.1 * np.random.randn(500)
        td = {"time_ps": t.tolist(), "voltage_v": v.tolist()}
        fig = plot_eye_diagram(td)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotPassband:
    def test_returns_figure(self):
        wl = np.linspace(1540, 1560, 100)
        channels = [
            {"transmission_db": (-30 * np.abs(wl - c) / 10).tolist(), "label": f"Ch{i}"}
            for i, c in enumerate([1545, 1550, 1555])
        ]
        awg = {"wavelengths_nm": wl.tolist(), "channels": channels}
        fig = plot_passband(awg)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotQberBudget:
    def test_returns_figure_dataclass(self):
        fig = plot_qber_budget(_MockQKDResult())
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_returns_figure_dict(self):
        d = {"q_dark": 0.01, "q_timing": 0.005, "q_misalignment": 0.008, "q_source": 0.002, "qber_total": 0.025}
        fig = plot_qber_budget(d)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)


class TestPlotLossBudget:
    def test_returns_figure(self):
        fig = plot_loss_budget(_MockQKDResult(distance_km=50, loss_db=12.0))
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_save_path(self, tmp_path):
        out = tmp_path / "loss.png"
        fig = plot_loss_budget(_MockQKDResult(), save_path=out)
        assert out.exists()
        plt.close(fig)


class TestEmptyEdgeCases:
    def test_empty_results_list(self):
        fig = plot_rate_distance([], show_plob=False)
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)

    def test_empty_comparison(self):
        fig = plot_protocol_comparison({})
        assert isinstance(fig, matplotlib.figure.Figure)
        plt.close(fig)
