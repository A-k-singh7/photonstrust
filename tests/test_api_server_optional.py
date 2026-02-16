from __future__ import annotations

import io
import json
from pathlib import Path
import zipfile

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402


def _qkd_graph(protocol_params: dict | None = None) -> dict:
    protocol_params = protocol_params or {"name": "BBM92"}
    return {
        "schema_version": "0.1",
        "graph_id": "api_qkd_link",
        "profile": "qkd_link",
        "metadata": {"title": "API QKD Graph", "description": "", "created_at": "2026-02-13"},
        "scenario": {
            "id": "api_qkd_link",
            "distance_km": 1,
            "band": "c_1550",
            "wavelength_nm": 1550,
            "execution_mode": "preview",
        },
        "uncertainty": {},
        "nodes": [
            {"id": "source_1", "kind": "qkd.source", "params": {"type": "emitter_cavity"}},
            {"id": "channel_1", "kind": "qkd.channel", "params": {"model": "fiber"}},
            {"id": "detector_1", "kind": "qkd.detector", "params": {"class": "snspd"}},
            {"id": "timing_1", "kind": "qkd.timing", "params": {"sync_drift_ps_rms": 10}},
            {"id": "protocol_1", "kind": "qkd.protocol", "params": dict(protocol_params)},
        ],
        "edges": [
            {"from": "source_1", "to": "channel_1", "kind": "optical"},
            {"from": "channel_1", "to": "detector_1", "kind": "optical"},
        ],
    }


def _pic_chain_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "api_pic_chain",
        "profile": "pic_circuit",
        "metadata": {"title": "API PIC Chain", "description": "", "created_at": "2026-02-13"},
        "circuit": {"id": "api_pic_chain", "wavelength_nm": 1550},
        "nodes": [
            {
                "id": "gc_in",
                "kind": "pic.grating_coupler",
                "params": {"insertion_loss_db": 2.5},
            },
            {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 2000, "loss_db_per_cm": 2.0}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {"insertion_loss_db": 1.5}},
        ],
        "edges": [
            {"from": "gc_in", "to": "wg_1", "kind": "optical"},
            {"from": "wg_1", "to": "ec_out", "kind": "optical"},
        ],
    }


def _pic_mzi_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "api_pic_mzi",
        "profile": "pic_circuit",
        "metadata": {"title": "API PIC MZI", "description": "", "created_at": "2026-02-13"},
        "circuit": {
            "id": "api_pic_mzi",
            "wavelength_nm": 1550,
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 1.0, "insertion_loss_db": 0.1}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in", "kind": "optical"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in", "kind": "optical"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1", "kind": "optical"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2", "kind": "optical"},
        ],
    }


def _orbit_pass_config() -> dict:
    return {
        "orbit_pass": {
            "id": "api_orbit_pass_envelope",
            "band": "c_1550",
            "dt_s": 30,
            "samples": [
                # Use a near-terrestrial free-space regime that yields non-zero key rate
                # with the current simplified multi-photon/QBER model (keeps diff tests stable).
                {"t_s": 0, "distance_km": 10, "elevation_deg": 20, "background_counts_cps": 0},
                {"t_s": 30, "distance_km": 50, "elevation_deg": 40, "background_counts_cps": 0},
                {"t_s": 60, "distance_km": 100, "elevation_deg": 70, "background_counts_cps": 0},
            ],
            "cases": [
                {"id": "median", "label": "Median", "channel_overrides": {}},
            ],
        },
        "source": {"type": "emitter_cavity", "g2_0": 0.0},
        "channel": {"model": "free_space"},
        "detector": {"class": "snspd"},
        "timing": {},
        "protocol": {"name": "BBM92"},
        "uncertainty": {},
    }


def test_api_healthz() -> None:
    client = TestClient(app)
    res = client.get("/healthz")
    assert res.status_code == 200
    payload = res.json()
    assert payload["status"] == "ok"


def test_api_registry_kinds() -> None:
    client = TestClient(app)
    res = client.get("/v0/registry/kinds")
    assert res.status_code == 200
    payload = res.json()
    assert payload["schema_version"] == "0.1"
    assert "registry_hash" in payload

    registry = payload["registry"]
    assert registry["schema_version"] == "0.1"
    kinds = registry["kinds"]
    kind_ids = {k["kind"] for k in kinds}
    assert "qkd.source" in kind_ids
    assert "pic.waveguide" in kind_ids

    # Security posture is published as metadata.
    touchstone = next(k for k in kinds if k["kind"] == "pic.touchstone_2port")
    assert touchstone["availability"]["api_enabled"] is False


def test_api_compile_qkd_graph() -> None:
    client = TestClient(app)
    res = client.post("/v0/graph/compile", json={"graph": _qkd_graph(), "require_schema": True})
    assert res.status_code == 200
    payload = res.json()
    assert payload["profile"] == "qkd_link"
    assert isinstance(payload.get("compiled"), dict)
    assert isinstance(payload.get("assumptions_md"), str)
    assert "diagnostics" in payload


def test_api_qkd_run_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep tests hermetic: store API runs under tmp_path.
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)
    res = client.post(
        "/v0/qkd/run",
        json={"graph": _qkd_graph(), "execution_mode": "preview"},
    )
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()
    assert payload["results"]["cards"]

    registry_path = Path(payload["results"]["registry_path"])
    assert registry_path.exists()

    manifest_path = Path(payload["manifest_path"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_type"] == "qkd_run"
    assert manifest.get("input", {}).get("protocol_selected")
    assert manifest.get("artifacts", {}).get("multifidelity_report_json") == "multifidelity_report.json"
    assert manifest.get("artifacts", {}).get("protocol_steps_json") == "protocol_steps.json"
    assert manifest.get("artifacts", {}).get("event_trace_json") == "event_trace.json"
    assert manifest.get("outputs_summary", {}).get("qkd", {}).get("multifidelity", {}).get("present") is True
    assert manifest.get("outputs_summary", {}).get("qkd", {}).get("protocol_selected")
    assert (manifest.get("outputs_summary", {}).get("qkd", {}).get("protocol_steps") or {}).get("step_count", 0) >= 1
    assert (manifest.get("outputs_summary", {}).get("qkd", {}).get("event_trace") or {}).get("trace_hash")

    multifidelity_path = out_dir / "multifidelity_report.json"
    assert multifidelity_path.exists()
    assert (out_dir / "protocol_steps.json").exists()
    assert (out_dir / "event_trace.json").exists()

    cards = manifest.get("outputs_summary", {}).get("qkd", {}).get("cards") or []
    assert cards
    first = cards[0]
    assert "confidence_intervals" in first
    assert "finite_key_epsilon_ledger" in first
    assert "security_assumptions_metadata" in first
    assert "model_provenance" in first
    assert "protocol_family" in first["model_provenance"]
    assert "channel_model" in first["model_provenance"]

    runs_res = client.get("/v0/runs")
    assert runs_res.status_code == 200
    runs_payload = runs_res.json()
    matching = [r for r in (runs_payload.get("runs") or []) if str(r.get("run_id")) == str(payload.get("run_id"))]
    assert matching
    assert matching[0].get("multifidelity_present") is True


def test_api_qkd_bundle_includes_multifidelity_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)
    run = client.post("/v0/qkd/run", json={"graph": _qkd_graph(), "execution_mode": "preview"})
    assert run.status_code == 200
    run_payload = run.json()
    run_id = str(run_payload["run_id"])

    bundle = client.get(f"/v0/runs/{run_id}/bundle", params={"include_children": "false"})
    assert bundle.status_code == 200

    zf = zipfile.ZipFile(io.BytesIO(bundle.content))
    names = set(zf.namelist())
    bundle_root = f"photonstrust_evidence_bundle_{run_id}"
    assert f"{bundle_root}/runs/run_{run_id}/multifidelity_report.json" in names


@pytest.mark.parametrize(
    ("protocol_params", "expected_protocol_norm", "expected_plob_policy"),
    [
        ({"name": "BBM92"}, "bbm92", "apply"),
        ({"name": "MDI_QKD", "mu": 0.4, "nu": 0.1, "omega": 0.0, "sifting_factor": 1.0}, "mdi_qkd", "skip"),
        ({"name": "PM_QKD", "mu": 0.5, "phase_slices": 16, "sifting_factor": 1.0}, "pm_qkd", "skip"),
        ({"name": "TF_QKD", "mu": 0.5, "phase_slices": 16, "sifting_factor": 1.0}, "tf_qkd", "skip"),
    ],
)
def test_api_qkd_run_outputs_summary_trust_metadata_is_protocol_consistent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protocol_params: dict,
    expected_protocol_norm: str,
    expected_plob_policy: str,
) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)
    res = client.post(
        "/v0/qkd/run",
        json={"graph": _qkd_graph(protocol_params=protocol_params), "execution_mode": "preview"},
    )
    assert res.status_code == 200
    payload = res.json()

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    cards = manifest.get("outputs_summary", {}).get("qkd", {}).get("cards") or []
    assert cards
    first = cards[0]

    assert first["confidence_intervals"]["key_rate_bps"] is not None
    assert "enabled" in first["finite_key_epsilon_ledger"]
    assert first["security_assumptions_metadata"]["security_model"]
    assert first["model_provenance"]["protocol_normalized"] == expected_protocol_norm
    assert first["bound_gate_policy"]["plob_repeaterless_bound"] == expected_plob_policy
    assert manifest.get("outputs_summary", {}).get("qkd", {}).get("protocol_selected") == expected_protocol_norm


def test_api_orbit_pass_run_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep tests hermetic: store API runs under tmp_path.
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)
    res = client.post("/v0/orbit/pass/run", json={"config": _orbit_pass_config()})
    assert res.status_code == 200
    payload = res.json()

    assert payload.get("run_id")
    assert payload.get("results_path")
    assert payload.get("report_html_path")
    assert "diagnostics" in payload
    assert payload["diagnostics"]["summary"]["error_count"] == 0
    assert payload.get("results") and isinstance(payload["results"], dict)
    assert payload.get("manifest_path")
    assert payload.get("artifact_relpaths")

    results_path = Path(payload["results_path"])
    report_path = Path(payload["report_html_path"])
    out_dir = Path(payload["output_dir"])
    assert results_path.exists()
    assert report_path.exists()
    assert out_dir.exists()

    assert payload["results"]["pass_id"] == "api_orbit_pass_envelope"
    assert payload["results"]["band"] == "c_1550"

    manifest_path = Path(payload["manifest_path"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_type"] == "orbit_pass"
    orbit_summary = manifest.get("outputs_summary", {}).get("orbit_pass", {})
    assert orbit_summary.get("cases")
    assert orbit_summary.get("trust_label", {}).get("mode") in {"preview", "certification"}
    assert "avg_channel_outage_probability" in orbit_summary.get("cases", [])[0]
    assert "avg_background_counts_cps" in orbit_summary.get("cases", [])[0]
    assert isinstance(orbit_summary.get("cases", [])[0].get("finite_key"), dict)
    assert orbit_summary.get("finite_key", {}).get("enabled") is True


def test_api_performance_drc_routes_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep tests hermetic: store API runs under tmp_path.
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)
    res = client.post(
        "/v0/performance_drc/crosstalk",
        json={
            "routes": [
                {"route_id": "wg_a", "width_um": 0.5, "points_um": [[0.0, 0.0], [100.0, 0.0]]},
                {"route_id": "wg_b", "width_um": 0.5, "points_um": [[0.0, 1.0], [100.0, 1.0]]},
            ],
            "layout_extract": {"max_gap_um": 5.0, "min_parallel_length_um": 1.0},
            "wavelength_sweep_nm": [1550.0],
            "target_xt_db": -40.0,
            "pdk": {"name": "generic_silicon_photonics"},
        },
    )
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()

    manifest_path = Path(payload["manifest_path"])
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_type"] == "performance_drc"
    perf_summary = manifest.get("outputs_summary", {}).get("performance_drc", {})
    assert isinstance(perf_summary.get("violation_summary", {}), dict)
    assert isinstance(perf_summary.get("violations_annotated", []), list)

    report = payload.get("report", {})
    assert report.get("results", {}).get("layout", {}).get("parallel_runs_count") >= 1


def test_api_pic_layout_build_and_lvs_lite_write_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    res = client.post("/v0/pic/layout/build", json={"graph": _pic_chain_graph()})
    assert res.status_code == 200
    build_payload = res.json()

    build_run_id = str(build_payload["run_id"])
    out_dir = Path(build_payload["output_dir"])
    assert out_dir.exists()
    assert (out_dir / "ports.json").exists()
    assert (out_dir / "routes.json").exists()
    assert (out_dir / "layout_provenance.json").exists()
    assert Path(build_payload["manifest_path"]).exists()

    res = client.post("/v0/pic/layout/lvs_lite", json={"graph": _pic_chain_graph(), "layout_run_id": build_run_id})
    assert res.status_code == 200
    lvs_payload = res.json()

    lvs_out_dir = Path(lvs_payload["output_dir"])
    assert lvs_out_dir.exists()
    assert (lvs_out_dir / "lvs_lite_report.json").exists()
    assert Path(lvs_payload["manifest_path"]).exists()
    assert lvs_payload.get("report", {}).get("summary", {}).get("pass") is True
    lvs_manifest = json.loads(Path(lvs_payload["manifest_path"]).read_text(encoding="utf-8"))
    lvs_summary = lvs_manifest.get("outputs_summary", {}).get("pic_lvs_lite", {})
    assert isinstance(lvs_summary.get("violations_annotated", []), list)


def test_api_pic_klayout_pack_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep tests hermetic: store API runs under tmp_path.
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    # Keep tests hermetic: do not invoke external KLayout even if installed locally.
    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)
    client = TestClient(app)

    # Create a synthetic prior layout run containing a (dummy) GDS artifact.
    from photonstrust.api import runs as run_store

    layout_run_id = "a" * 12
    layout_dir = run_store.run_dir_for_id(layout_run_id)
    layout_dir.mkdir(parents=True, exist_ok=True)
    (layout_dir / "layout.gds").write_bytes(b"PHOTONTRUST_DUMMY_GDS")
    run_store.write_run_manifest(
        layout_dir,
        {
            "schema_version": "0.1",
            "run_id": layout_run_id,
            "run_type": "pic_layout_build",
            "generated_at": "2026-02-14T00:00:00+00:00",
            "output_dir": str(layout_dir),
            "input": {"project_id": "default"},
            "outputs_summary": {},
            "artifacts": {"layout_gds": "layout.gds"},
            "provenance": {"python": "0", "platform": "0"},
        },
    )

    res = client.post("/v0/pic/layout/klayout/run", json={"layout_run_id": layout_run_id})
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()
    assert (out_dir / "klayout_run_artifact_pack.json").exists()
    assert (out_dir / "klayout_stdout.txt").exists()
    assert (out_dir / "klayout_stderr.txt").exists()
    assert Path(payload["manifest_path"]).exists()

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_type"] == "pic_klayout_artifact_pack"
    assert manifest.get("input", {}).get("layout_run_id") == layout_run_id


def test_api_pic_klayout_pack_accepts_source_run_id_and_explicit_gds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Keep tests hermetic: store API runs under tmp_path.
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    # Keep tests hermetic: do not invoke external KLayout even if installed locally.
    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)
    client = TestClient(app)

    # Create a synthetic prior run containing multiple (dummy) GDS artifacts.
    from photonstrust.api import runs as run_store

    source_run_id = "b" * 12
    source_dir = run_store.run_dir_for_id(source_run_id)
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "first.gds").write_bytes(b"PHOTONTRUST_DUMMY_GDS_1")
    (source_dir / "second.gds").write_bytes(b"PHOTONTRUST_DUMMY_GDS_2")
    run_store.write_run_manifest(
        source_dir,
        {
            "schema_version": "0.1",
            "run_id": source_run_id,
            "run_type": "manual_layout_drop",
            "generated_at": "2026-02-14T00:00:00+00:00",
            "output_dir": str(source_dir),
            "input": {"project_id": "default"},
            "outputs_summary": {},
            "artifacts": {"first_layout_gds": "first.gds", "second_layout_gds": "second.gds"},
            "provenance": {"python": "0", "platform": "0"},
        },
    )

    res = client.post(
        "/v0/pic/layout/klayout/run",
        json={"source_run_id": source_run_id, "gds_artifact_path": "second.gds"},
    )
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()
    assert (out_dir / "klayout_run_artifact_pack.json").exists()
    assert (out_dir / "klayout_stdout.txt").exists()
    assert (out_dir / "klayout_stderr.txt").exists()
    assert Path(payload["manifest_path"]).exists()

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_type"] == "pic_klayout_artifact_pack"
    assert manifest.get("input", {}).get("source_run_id") == source_run_id
    assert manifest.get("input", {}).get("source_gds_artifact_path") == "second.gds"
    assert manifest.get("input", {}).get("layout_run_id") is None


def test_api_pic_invdesign_coupler_ratio_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    graph = {
        "schema_version": "0.1",
        "graph_id": "api_inv_coupler_ratio",
        "profile": "pic_circuit",
        "metadata": {"title": "API Invdesign Coupler Ratio", "description": "", "created_at": "2026-02-14"},
        "circuit": {
            "id": "api_inv_coupler_ratio",
            "wavelength_nm": 1550.0,
            "inputs": [
                {"node": "cpl", "port": "in1", "amplitude": 1.0},
                {"node": "cpl", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [{"id": "cpl", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.0}}],
        "edges": [],
    }

    res = client.post(
        "/v0/pic/invdesign/coupler_ratio",
        json={
            "graph": graph,
            "coupler_node_id": "cpl",
            "target_output_node": "cpl",
            "target_output_port": "out1",
            "target_power_fraction": 0.9,
            "steps": 32,
            "wavelength_sweep_nm": [1550.0],
            "robustness_cases": [{"id": "nominal", "label": "Nominal", "overrides": {}}],
            "wavelength_objective_agg": "mean",
            "case_objective_agg": "mean",
        },
    )
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()
    assert (out_dir / "invdesign_report.json").exists()
    assert (out_dir / "optimized_graph.json").exists()
    assert Path(payload["manifest_path"]).exists()

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_type"] == "invdesign"
    assert manifest.get("input", {}).get("kind") == "pic.invdesign.coupler_ratio"


def test_api_pic_spice_export_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    res = client.post("/v0/pic/spice/export", json={"graph": _pic_chain_graph()})
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()
    assert (out_dir / "netlist.sp").exists()
    assert (out_dir / "spice_map.json").exists()
    assert (out_dir / "spice_provenance.json").exists()
    assert Path(payload["manifest_path"]).exists()


def test_api_pic_invdesign_workflow_chain_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    # Keep tests hermetic: do not invoke external KLayout even if installed locally.
    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    res = client.post(
        "/v0/pic/workflow/invdesign_chain",
        json={
            "graph": _pic_mzi_graph(),
            "invdesign": {
                "kind": "mzi_phase",
                "phase_node_id": "ps1",
                "target_output_node": "cpl_out",
                "target_output_port": "out1",
                "target_power_fraction": 0.9,
                "steps": 31,
                "wavelength_sweep_nm": [1550.0],
            },
            "layout": {"pdk": {"name": "generic_silicon_photonics"}, "settings": {"ui_scale_um_per_unit": 1.0}},
            "lvs_lite": {"settings": {"coord_tol_um": 1.0e-6}},
            "klayout": {"settings": {}},
            "spice": {"settings": {"top_name": "PT_TOP", "subckt_prefix": "PT", "include_stub_subckts": True}},
            "require_schema": False,
        },
    )
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert out_dir.exists()
    assert (out_dir / "workflow_report.json").exists()
    assert (out_dir / "workflow_request.json").exists()
    assert Path(payload["manifest_path"]).exists()

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_type"] == "pic_workflow_invdesign_chain"

    steps = payload.get("steps") or {}
    inv_run_id = str((steps.get("invdesign") or {}).get("run_id") or "")
    layout_run_id = str((steps.get("layout_build") or {}).get("run_id") or "")
    lvs_run_id = str((steps.get("lvs_lite") or {}).get("run_id") or "")
    spice_run_id = str((steps.get("spice_export") or {}).get("run_id") or "")
    assert inv_run_id and layout_run_id and lvs_run_id and spice_run_id

    from photonstrust.api import runs as run_store

    assert (run_store.run_dir_for_id(inv_run_id) / "run_manifest.json").exists()
    assert (run_store.run_dir_for_id(layout_run_id) / "run_manifest.json").exists()
    assert (run_store.run_dir_for_id(lvs_run_id) / "run_manifest.json").exists()
    assert (run_store.run_dir_for_id(spice_run_id) / "run_manifest.json").exists()

    klayout_run_id = (steps.get("klayout_pack") or {}).get("run_id")
    if klayout_run_id:
        assert (run_store.run_dir_for_id(str(klayout_run_id)) / "run_manifest.json").exists()


def test_api_runs_bundle_returns_zip_for_workflow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    # Keep tests hermetic: do not invoke external KLayout even if installed locally.
    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    res = client.post(
        "/v0/pic/workflow/invdesign_chain",
        json={
            "graph": _pic_mzi_graph(),
            "invdesign": {
                "kind": "mzi_phase",
                "phase_node_id": "ps1",
                "target_output_node": "cpl_out",
                "target_output_port": "out1",
                "target_power_fraction": 0.9,
                "steps": 21,
                "wavelength_sweep_nm": [1550.0],
            },
            "layout": {"pdk": {"name": "generic_silicon_photonics"}, "settings": {"ui_scale_um_per_unit": 1.0}},
            "lvs_lite": {"settings": {"coord_tol_um": 1.0e-6}},
            "spice": {"settings": {"top_name": "PT_TOP", "subckt_prefix": "PT", "include_stub_subckts": True}},
        },
    )
    assert res.status_code == 200
    wf = res.json()
    wf_id = str(wf["run_id"])

    res = client.get(f"/v0/runs/{wf_id}/bundle")
    assert res.status_code == 200
    assert "application/zip" in str(res.headers.get("content-type", "")).lower()

    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = set(zf.namelist())
    bundle_root = f"photonstrust_evidence_bundle_{wf_id}"

    assert f"{bundle_root}/README.md" in names
    assert f"{bundle_root}/bundle_manifest.json" in names
    assert f"{bundle_root}/runs/run_{wf_id}/run_manifest.json" in names
    assert f"{bundle_root}/runs/run_{wf_id}/workflow_report.json" in names
    assert f"{bundle_root}/runs/run_{wf_id}/workflow_request.json" in names

    steps = wf.get("steps") or {}
    inv_run_id = str((steps.get("invdesign") or {}).get("run_id") or "")
    layout_run_id = str((steps.get("layout_build") or {}).get("run_id") or "")
    lvs_run_id = str((steps.get("lvs_lite") or {}).get("run_id") or "")
    spice_run_id = str((steps.get("spice_export") or {}).get("run_id") or "")
    assert inv_run_id and layout_run_id and lvs_run_id and spice_run_id

    assert f"{bundle_root}/runs/run_{inv_run_id}/run_manifest.json" in names
    assert f"{bundle_root}/runs/run_{layout_run_id}/run_manifest.json" in names
    assert f"{bundle_root}/runs/run_{lvs_run_id}/run_manifest.json" in names
    assert f"{bundle_root}/runs/run_{spice_run_id}/run_manifest.json" in names
    assert f"{bundle_root}/runs/run_{spice_run_id}/netlist.sp" in names


def test_api_pic_invdesign_workflow_chain_replay_creates_new_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    # Keep tests hermetic: do not invoke external KLayout even if installed locally.
    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    res = client.post("/v0/pic/workflow/invdesign_chain", json={"graph": _pic_mzi_graph(), "invdesign": {"kind": "mzi_phase"}})
    assert res.status_code == 200
    wf = res.json()
    wf_id = str(wf["run_id"])

    res = client.post("/v0/pic/workflow/invdesign_chain/replay", json={"workflow_run_id": wf_id})
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("replayed_from_run_id") == wf_id

    new_wf = payload.get("workflow") or {}
    new_id = str(new_wf.get("run_id") or "")
    assert new_id and new_id != wf_id

    manifest = json.loads(Path(new_wf["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_type"] == "pic_workflow_invdesign_chain"
    assert manifest.get("input", {}).get("replayed_from_run_id") == wf_id

def test_api_runs_registry_and_artifact_serving(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    run = client.post("/v0/orbit/pass/run", json={"config": _orbit_pass_config()})
    assert run.status_code == 200
    run_payload = run.json()
    run_id = str(run_payload["run_id"])
    pass_id = str(run_payload["results"]["pass_id"])
    band = str(run_payload["results"]["band"])

    res = client.get("/v0/runs")
    assert res.status_code == 200
    runs_payload = res.json()
    run_ids = {r.get("run_id") for r in (runs_payload.get("runs") or [])}
    assert run_id in run_ids

    res = client.get(f"/v0/runs/{run_id}")
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["run_id"] == run_id
    assert manifest["run_type"] == "orbit_pass"
    assert manifest.get("outputs_summary", {}).get("orbit_pass")

    report_rel = f"{pass_id}/{band}/orbit_pass_report.html"
    res = client.get(f"/v0/runs/{run_id}/artifact", params={"path": report_rel})
    assert res.status_code == 200
    assert "text/html" in str(res.headers.get("content-type", "")).lower()
    assert "Orbit Pass Report" in str(res.text)

    results_rel = f"{pass_id}/{band}/orbit_pass_results.json"
    res = client.get(f"/v0/runs/{run_id}/artifact", params={"path": results_rel})
    assert res.status_code == 200
    assert "application/json" in str(res.headers.get("content-type", "")).lower()
    payload = res.json()
    assert payload["pass_id"] == pass_id
    assert payload["band"] == band

    res = client.get(f"/v0/runs/{run_id}/artifact", params={"path": "../nope.txt"})
    assert res.status_code == 400


def test_api_runs_diff_reports_input_changes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    cfg_a = _orbit_pass_config()
    cfg_b = _orbit_pass_config()
    cfg_b["orbit_pass"]["dt_s"] = 15

    res = client.post("/v0/orbit/pass/run", json={"config": cfg_a})
    assert res.status_code == 200
    run_a = res.json()

    res = client.post("/v0/orbit/pass/run", json={"config": cfg_b})
    assert res.status_code == 200
    run_b = res.json()

    lhs = str(run_a["run_id"])
    rhs = str(run_b["run_id"])
    res = client.post("/v0/runs/diff", json={"lhs_run_id": lhs, "rhs_run_id": rhs, "scope": "input", "limit": 50})
    assert res.status_code == 200
    payload = res.json()

    assert payload["scope"] == "input"
    changes = payload["diff"]["changes"]
    assert isinstance(changes, list) and changes
    assert payload["diff"]["summary"]["change_count"] == len(changes)
    assert payload["diff"]["summary"]["change_count"] <= 50
    assert any(c.get("path") == "/config_hash" for c in changes)

    res = client.post("/v0/runs/diff", json={"lhs_run_id": lhs, "rhs_run_id": rhs, "scope": "outputs_summary", "limit": 50})
    assert res.status_code == 200
    payload = res.json()
    changes = payload["diff"]["changes"]
    assert isinstance(changes, list) and changes
    assert any(c.get("path") == "/orbit_pass/cases" for c in changes)


def test_api_runs_diff_outputs_summary_includes_violation_diff(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    from photonstrust.api import runs as run_store

    lhs_run_id = "c" * 12
    rhs_run_id = "d" * 12
    lhs_dir = run_store.run_dir_for_id(lhs_run_id)
    rhs_dir = run_store.run_dir_for_id(rhs_run_id)

    lhs_manifest = {
        "schema_version": "0.1",
        "run_id": lhs_run_id,
        "run_type": "performance_drc",
        "generated_at": "2026-02-16T00:00:00+00:00",
        "output_dir": str(lhs_dir),
        "input": {"project_id": "default"},
        "outputs_summary": {
            "performance_drc": {
                "violations_annotated": [
                    {
                        "id": "shared-app-change",
                        "code": "pdrc.shared",
                        "entity_ref": "route:r0",
                        "message": "shared route issue",
                        "applicability": "advisory",
                    },
                    {
                        "code": "pdrc.legacy",
                        "entity_ref": "route:r1",
                        "message": "legacy route issue",
                        "applicability": "blocking",
                    },
                ]
            }
        },
        "artifacts": {},
        "provenance": {"python": "0", "platform": "0"},
    }
    rhs_manifest = {
        "schema_version": "0.1",
        "run_id": rhs_run_id,
        "run_type": "performance_drc",
        "generated_at": "2026-02-16T00:00:01+00:00",
        "output_dir": str(rhs_dir),
        "input": {"project_id": "default"},
        "outputs_summary": {
            "performance_drc": {
                "violations_annotated": [
                    {
                        "id": "shared-app-change",
                        "code": "pdrc.shared",
                        "entity_ref": "route:r0",
                        "message": "shared route issue",
                        "applicability": "blocking",
                    },
                    {
                        "code": "pdrc.new",
                        "entity_ref": "route:r2",
                        "message": "new route issue",
                        "applicability": "advisory",
                    },
                ]
            }
        },
        "artifacts": {},
        "provenance": {"python": "0", "platform": "0"},
    }

    run_store.write_run_manifest(lhs_dir, lhs_manifest)
    run_store.write_run_manifest(rhs_dir, rhs_manifest)

    res = client.post(
        "/v0/runs/diff",
        json={"lhs_run_id": lhs_run_id, "rhs_run_id": rhs_run_id, "scope": "outputs_summary", "limit": 50},
    )
    assert res.status_code == 200
    payload = res.json()

    vdiff = ((payload.get("diff") or {}).get("violation_diff") or {})
    summary = vdiff.get("summary") or {}
    assert summary.get("new_count") == 1
    assert summary.get("resolved_count") == 1
    assert summary.get("applicability_changed_count") == 1

    assert len(vdiff.get("new") or []) == 1
    assert len(vdiff.get("resolved") or []) == 1
    assert len(vdiff.get("applicability_changed") or []) == 1

    assert (vdiff.get("new") or [])[0].get("code") == "pdrc.new"
    assert (vdiff.get("resolved") or [])[0].get("code") == "pdrc.legacy"
    app_change = (vdiff.get("applicability_changed") or [])[0]
    assert app_change.get("lhs_applicability") == "advisory"
    assert app_change.get("rhs_applicability") == "blocking"


def test_api_qkd_external_import_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    external = {
        "schema_version": "0.1",
        "kind": "photonstrust.external_sim_result",
        "simulator_name": "netsquid",
        "simulator_version": "1.2.0",
        "scenario_description": {"scenario_id": "interop_case_1", "band": "c_1550", "wavelength_nm": 1550.0, "protocol": "BB84"},
        "metrics": {"key_rate_bps": 123.4, "qber_total": 0.021, "fidelity_est": 0.98, "distance_km": 40.0},
        "provenance": {"seed": 7, "input_hash": "abc"},
    }

    res = client.post("/v0/qkd/import_external", json={"external_result": external, "project_id": "default"})
    assert res.status_code == 200
    payload = res.json()

    run_dir = Path(payload["output_dir"])
    assert run_dir.exists()
    assert (run_dir / "external_sim_result.json").exists()
    assert (run_dir / "reliability_card.json").exists()

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest.get("run_type") == "qkd_external_import"
    summary = manifest.get("outputs_summary", {}).get("qkd_external_import", {})
    assert summary.get("source") == "external_import"
    assert summary.get("simulator_name") == "netsquid"
    assert summary.get("key_rate_bps") == 123.4


def test_api_runs_diff_includes_interop_block(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    native = client.post("/v0/qkd/run", json={"graph": _qkd_graph(), "execution_mode": "preview"})
    assert native.status_code == 200
    native_id = str(native.json().get("run_id"))

    external = {
        "schema_version": "0.1",
        "kind": "photonstrust.external_sim_result",
        "simulator_name": "sequence",
        "metrics": {"key_rate_bps": 10.0, "qber_total": 0.03, "fidelity_est": 0.95, "distance_km": 20.0},
    }
    imported = client.post("/v0/qkd/import_external", json={"external_result": external})
    assert imported.status_code == 200
    imported_id = str(imported.json().get("run_id"))

    diff = client.post(
        "/v0/runs/diff",
        json={"lhs_run_id": native_id, "rhs_run_id": imported_id, "scope": "outputs_summary", "limit": 200},
    )
    assert diff.status_code == 200
    payload = diff.json()
    interop = payload.get("diff", {}).get("interop_diff", {})
    assert interop.get("lhs_source") == "native"
    assert interop.get("rhs_source") == "external_import"
    assert "key_rate_bps_delta" in interop


def test_api_projects_and_approvals(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    project_id = "pt_test_proj"
    run = client.post("/v0/orbit/pass/run", json={"config": _orbit_pass_config(), "project_id": project_id})
    assert run.status_code == 200
    run_payload = run.json()
    run_id = str(run_payload["run_id"])

    res = client.get("/v0/projects")
    assert res.status_code == 200
    payload = res.json()
    projects = payload.get("projects") or []
    assert isinstance(projects, list) and projects
    project_ids = {p.get("project_id") for p in projects if isinstance(p, dict)}
    assert project_id in project_ids

    res = client.get("/v0/runs", params={"project_id": project_id})
    assert res.status_code == 200
    payload = res.json()
    runs = payload.get("runs") or []
    assert isinstance(runs, list) and runs
    assert all(r.get("project_id") == project_id for r in runs if isinstance(r, dict))

    res = client.get(f"/v0/projects/{project_id}/approvals")
    assert res.status_code == 200
    payload = res.json()
    assert payload.get("project_id") == project_id
    assert payload.get("approvals") == []

    res = client.post(
        f"/v0/projects/{project_id}/approvals",
        json={"run_id": run_id, "actor": "tester", "note": "approve for review"},
    )
    assert res.status_code == 200
    payload = res.json()
    event = payload.get("event") or {}
    assert event.get("event_type") == "run_approved"
    assert event.get("project_id") == project_id
    assert event.get("run_id") == run_id
    assert event.get("run_manifest_hash")
    assert event.get("outputs_summary_hash")

    res = client.get(f"/v0/projects/{project_id}/approvals", params={"limit": 10})
    assert res.status_code == 200
    payload = res.json()
    approvals = payload.get("approvals") or []
    assert any(a.get("event_id") == event.get("event_id") for a in approvals if isinstance(a, dict))

    res = client.post(f"/v0/projects/otherproj/approvals", json={"run_id": run_id})
    assert res.status_code == 400


def test_api_orbit_pass_validate_returns_diagnostics() -> None:
    client = TestClient(app)
    res = client.post("/v0/orbit/pass/validate", json={"config": _orbit_pass_config(), "require_schema": True})
    assert res.status_code == 200
    payload = res.json()
    diags = payload["diagnostics"]
    assert diags["summary"]["error_count"] == 0


def test_api_pic_simulate_chain() -> None:
    client = TestClient(app)
    res = client.post("/v0/pic/simulate", json={"graph": _pic_chain_graph()})
    assert res.status_code == 200
    payload = res.json()
    assert payload["results"]["chain_solver"]["applicable"] is True
    assert payload["results"]["chain_solver"]["eta_total"] <= 1.0


def test_api_pic_simulate_mzi_requires_inputs_is_handled() -> None:
    client = TestClient(app)
    res = client.post("/v0/pic/simulate", json={"graph": _pic_mzi_graph()})
    assert res.status_code == 200
    payload = res.json()
    outs = payload["results"]["dag_solver"]["external_outputs"]
    assert len(outs) >= 1


def test_api_pic_touchstone_is_rejected() -> None:
    client = TestClient(app)
    graph = {
        "schema_version": "0.1",
        "graph_id": "api_pic_touchstone",
        "profile": "pic_circuit",
        "metadata": {"title": "API PIC Touchstone", "description": "", "created_at": "2026-02-13"},
        "circuit": {"id": "api_pic_touchstone", "wavelength_nm": 1550},
        "nodes": [
            {
                "id": "s2p",
                "kind": "pic.touchstone_2port",
                "params": {"path": "fixtures/demo.s2p"},
            }
        ],
        "edges": [],
    }
    res = client.post("/v0/pic/simulate", json={"graph": graph})
    assert res.status_code == 400
    detail = (res.json() or {}).get("detail", "")
    assert "disabled" in str(detail).lower()


def test_api_graph_validate_catches_pic_port_errors() -> None:
    client = TestClient(app)
    g = _pic_mzi_graph()
    g["edges"][0]["from_port"] = "nope"
    res = client.post("/v0/graph/validate", json={"graph": g, "require_schema": True})
    assert res.status_code == 200
    payload = res.json()
    diags = payload["diagnostics"]
    assert diags["summary"]["error_count"] >= 1
    codes = {d["code"] for d in diags["errors"]}
    assert "edge.from_port" in codes
