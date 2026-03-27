from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api import runs as run_store  # noqa: E402
from photonstrust.api.server import app  # noqa: E402


def _fixture_graph() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "phase58_w36_flagship_invdesign_component_graph.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_flagship_fixture_replay_and_signoff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    graph = _fixture_graph()

    res = client.post(
        "/v0/pic/workflow/invdesign_chain",
        json={
            "graph": graph,
            "execution_mode": "certification",
            "invdesign": {
                "kind": "mzi_phase",
                "phase_node_id": "ps1",
                "target_output_node": "cpl_out",
                "target_output_port": "out1",
                "target_power_fraction": 0.85,
                "steps": 31,
                "wavelength_sweep_nm": [1550.0],
                "robustness_cases": [
                    {"id": "nominal", "label": "Nominal", "overrides": {}},
                    {"id": "corner_fast", "label": "Fast", "overrides": {"cpl_out": {"coupling_ratio": 0.45}}},
                ],
                "robustness_thresholds": {
                    "min_worst_case_fraction": 0.30,
                    "max_objective": 1.0,
                    "max_degradation_from_nominal": 0.80,
                },
                "solver_backend": "adjoint_gpl",
                "solver_plugin": {
                    "plugin_id": "ext.adjoint.demo",
                    "plugin_version": "0.1",
                    "license_class": "copyleft",
                    "available": False,
                },
            },
            "layout": {
                "pdk": {"name": "generic_silicon_photonics"},
                "settings": {"ui_scale_um_per_unit": 1.0},
            },
            "lvs_lite": {
                "settings": {"coord_tol_um": 1.0e-6},
                "signoff_bundle": {
                    "design_rule_envelope": {
                        "waveguides": [{"id": "wg_ok", "width_um": 0.5}],
                    }
                },
            },
            "klayout": {"enabled": False},
            "spice": {
                "settings": {
                    "top_name": "PT_TOP",
                    "subckt_prefix": "PT",
                    "include_stub_subckts": True,
                }
            },
        },
    )
    assert res.status_code == 200
    wf = res.json()
    assert wf.get("status") == "pass"

    steps = wf.get("steps") or {}
    inv_run_id = str((steps.get("invdesign") or {}).get("run_id") or "")
    layout_run_id = str((steps.get("layout_build") or {}).get("run_id") or "")
    lvs_run_id = str((steps.get("lvs_lite") or {}).get("run_id") or "")
    spice_run_id = str((steps.get("spice_export") or {}).get("run_id") or "")
    assert inv_run_id and layout_run_id and lvs_run_id and spice_run_id

    inv_dir = run_store.run_dir_for_id(inv_run_id)
    inv_report = json.loads((inv_dir / "invdesign_report.json").read_text(encoding="utf-8"))
    inv_solver = ((inv_report.get("execution") or {}).get("solver") or {})
    assert inv_solver.get("backend_requested") == "adjoint_gpl"
    assert inv_solver.get("backend_used") == "core"
    assert (inv_solver.get("applicability") or {}).get("status") == "fallback"
    assert inv_solver.get("fallback_reason") == "plugin_unavailable"

    robust_eval = ((inv_report.get("best") or {}).get("robustness_eval") or {})
    assert isinstance(robust_eval.get("worst_case"), dict)
    assert isinstance(robust_eval.get("metrics"), dict)
    assert (robust_eval.get("threshold_eval") or {}).get("required") is True

    lvs_dir = run_store.run_dir_for_id(lvs_run_id)
    lvs_report = json.loads((lvs_dir / "lvs_lite_report.json").read_text(encoding="utf-8"))
    lvs_summary = lvs_report.get("summary") or {}
    assert lvs_summary.get("pass") is True
    assert lvs_summary.get("signoff_pass") is True
    assert int(lvs_summary.get("signoff_total_checks") or 0) >= 1

    wf_id = str(wf.get("run_id") or "")
    bundle_res = client.get(f"/v0/runs/{wf_id}/bundle", params={"include_children": "true", "rebuild": "true"})
    assert bundle_res.status_code == 200
    assert "application/zip" in str(bundle_res.headers.get("content-type", "")).lower()

    zf = zipfile.ZipFile(io.BytesIO(bundle_res.content))
    names = set(zf.namelist())
    bundle_root = f"photonstrust_evidence_bundle_{wf_id}"
    assert f"{bundle_root}/runs/run_{wf_id}/workflow_report.json" in names
    assert f"{bundle_root}/runs/run_{inv_run_id}/invdesign_report.json" in names
    assert f"{bundle_root}/runs/run_{layout_run_id}/layout_build_report.json" in names
    assert f"{bundle_root}/runs/run_{lvs_run_id}/lvs_lite_report.json" in names
    assert f"{bundle_root}/runs/run_{spice_run_id}/spice_export_report.json" in names

    replay_res = client.post("/v0/pic/workflow/invdesign_chain/replay", json={"workflow_run_id": wf_id})
    assert replay_res.status_code == 200
    replay_payload = replay_res.json()
    replay_wf = replay_payload.get("workflow") or {}
    replay_id = str(replay_wf.get("run_id") or "")
    assert replay_id and replay_id != wf_id
    assert replay_payload.get("replayed_from_run_id") == wf_id
