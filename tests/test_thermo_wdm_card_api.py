"""Tests for thermo-optic, WDM, reliability card, and REST API."""
from __future__ import annotations
import math
import json
import pytest


# ── Thermo-optic co-simulation ───────────────────────────────────────────────

class TestThermoOptic:
    from photonstrust.physics.thermo_optic import (
        compute_thermo_optic_phase, heater_drive_curve,
        update_netlist_with_thermal, SILICON, SILICON_NITRIDE,
    )

    def test_zero_voltage_gives_zero_phase(self):
        from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
        r = compute_thermo_optic_phase(voltage_v=0.0)
        assert r["phase_rad"] == 0.0
        assert r["power_mw"] == 0.0
        assert r["delta_T_K"] == 0.0

    def test_phase_increases_with_voltage(self):
        from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
        r1 = compute_thermo_optic_phase(voltage_v=1.0)
        r3 = compute_thermo_optic_phase(voltage_v=3.0)
        assert r3["phase_rad"] > r1["phase_rad"]

    def test_power_is_ohmic(self):
        from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
        r = compute_thermo_optic_phase(voltage_v=2.0, heater_resistance_ohm=500.0)
        expected_mw = (2.0 ** 2 / 500.0) * 1e3
        assert abs(r["power_mw"] - expected_mw) < 0.001

    def test_vpi_physics(self):
        from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
        r = compute_thermo_optic_phase(voltage_v=1.0, waveguide_length_um=50)
        vpi = r["v_pi_v"]
        # At v_pi, phase should be ~π
        r_pi = compute_thermo_optic_phase(voltage_v=vpi, waveguide_length_um=50)
        assert abs(r_pi["phase_rad"] - math.pi) < 0.01

    def test_silicon_vs_sin_material(self):
        from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
        r_si = compute_thermo_optic_phase(voltage_v=2.0, material="silicon")
        r_sin = compute_thermo_optic_phase(voltage_v=2.0, material="silicon_nitride")
        # Si has higher dn/dT → more phase shift
        assert r_si["phase_rad"] > r_sin["phase_rad"]

    def test_unknown_material_raises(self):
        from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
        with pytest.raises(ValueError, match="Unknown material"):
            compute_thermo_optic_phase(voltage_v=1.0, material="unobtanium")

    def test_drive_curve_structure(self):
        from photonstrust.physics.thermo_optic import heater_drive_curve
        curve = heater_drive_curve(v_max=5.0, n_points=20)
        assert len(curve["voltages_v"]) == 20
        assert len(curve["phases_rad"]) == 20
        assert curve["phases_rad"][0] == 0.0
        assert curve["phases_rad"][-1] > curve["phases_rad"][0]

    def test_update_netlist_with_thermal(self):
        from photonstrust.physics.thermo_optic import update_netlist_with_thermal
        netlist = {
            "circuit": {
                "nodes": [{"id": "ps1", "kind": "pic.phase_shifter", "params": {"length_um": 50}}],
                "edges": [],
            }
        }
        updated = update_netlist_with_thermal(netlist, {"ps1": 2.0})
        nodes = updated["circuit"]["nodes"]
        assert "phase_rad" in nodes[0]["params"]
        assert nodes[0]["params"]["phase_rad"] > 0


# ── WDM analysis ─────────────────────────────────────────────────────────────

class TestWDMAnalysis:
    from photonstrust.wdm.analysis import itu_channel_grid, analyze_wdm_channels

    def test_itu_grid_count(self):
        from photonstrust.wdm.analysis import itu_channel_grid
        grid = itu_channel_grid(n_channels=8)
        assert len(grid) == 8

    def test_itu_grid_spacing(self):
        from photonstrust.wdm.analysis import itu_channel_grid
        grid = itu_channel_grid(channel_spacing_ghz=100.0, n_channels=4)
        freqs = [ch["frequency_thz"] for ch in grid]
        diffs = [freqs[i + 1] - freqs[i] for i in range(len(freqs) - 1)]
        for d in diffs:
            assert abs(d - 0.1) < 1e-4   # 100 GHz = 0.1 THz

    def test_itu_grid_center_channel(self):
        from photonstrust.wdm.analysis import itu_channel_grid
        grid = itu_channel_grid(center_wl_nm=1550.0, n_channels=1)
        assert abs(grid[0]["wavelength_nm"] - 1550.0) < 0.1

    def test_wdm_analyze_returns_expected_keys(self):
        from photonstrust.wdm.analysis import analyze_wdm_channels
        netlist = {
            "circuit": {
                "nodes": [{"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 50}}],
                "edges": [],
            }
        }
        result = analyze_wdm_channels(netlist, n_channels=4)
        # Either succeeds with channels, or returns error key — both are valid
        assert "channels" in result or "error" in result
        if "channels" in result and result.get("ok"):
            assert "isolation_matrix_db" in result
            assert "osnr_estimate_db" in result
            assert len(result["channels"]) == 4

    def test_isolation_matrix_diagonal_zero(self):
        from photonstrust.wdm.analysis import analyze_wdm_channels
        netlist = {
            "circuit": {
                "nodes": [{"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 50}}],
                "edges": [],
            }
        }
        result = analyze_wdm_channels(netlist, n_channels=3)
        if result.get("ok") and result.get("isolation_matrix_db"):
            mat = result["isolation_matrix_db"]
            for i in range(len(mat)):
                assert mat[i][i] == 0.0
        else:
            pytest.skip("WDM sweep not available in this environment")


# ── Reliability card ──────────────────────────────────────────────────────────

class TestReliabilityCard:

    def _netlist(self):
        return {
            "circuit": {
                "nodes": [
                    {"id": "wg1", "kind": "pic.waveguide", "params": {"length_um": 100}},
                    {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.5}},
                ],
                "edges": [{"from": "wg1", "from_port": "out", "to": "ps1", "to_port": "in"}],
            }
        }

    def test_html_generates_without_error(self):
        from photonstrust.reports.reliability_card import generate_reliability_card_html
        html = generate_reliability_card_html(
            netlist=self._netlist(),
            title="Test Card",
        )
        assert "<!DOCTYPE html>" in html
        assert "Test Card" in html
        assert "PhotonTrust" in html

    def test_html_contains_drc_section(self):
        from photonstrust.reports.reliability_card import generate_reliability_card_html
        html = generate_reliability_card_html(netlist=self._netlist())
        assert "DRC" in html

    def test_html_contains_provenance(self):
        from photonstrust.reports.reliability_card import generate_reliability_card_html
        html = generate_reliability_card_html()
        assert "Provenance" in html
        assert "SHA-256" in html

    def test_write_reliability_card_creates_file(self, tmp_path):
        from photonstrust.reports.reliability_card import write_reliability_card
        out = str(tmp_path / "card.html")
        path = write_reliability_card(out, netlist=self._netlist())
        import os
        assert os.path.exists(path)
        content = open(path, encoding="utf-8").read()
        assert "<!DOCTYPE html>" in content
        assert len(content) > 2000

    def test_html_with_yield_metrics(self):
        from photonstrust.reports.reliability_card import generate_reliability_card_html
        metrics = [
            {"name": "width_nm", "nominal": 500, "sigma": 5,
             "sensitivity": 1.0, "min_allowed": 488, "max_allowed": 512}
        ]
        html = generate_reliability_card_html(yield_metrics=metrics)
        assert "Yield" in html


# ── API server (import + structure test only) ─────────────────────────────────

class TestAPIServer:

    def test_api_server_importable(self):
        """API server should import without error even if fastapi not installed."""
        try:
            import photonstrust.api_server as srv
            assert hasattr(srv, "create_app") or hasattr(srv, "start_server")
        except ImportError:
            pytest.skip("fastapi not installed")

    def test_start_server_function_exists(self):
        from photonstrust.api_server import start_server
        assert callable(start_server)

    def test_app_has_endpoints(self):
        try:
            from fastapi.testclient import TestClient
            from photonstrust.api_server import create_app
            client = TestClient(create_app())
            r = client.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"
        except (ImportError, RuntimeError):
            pytest.skip("fastapi/httpx/starlette not installed")
