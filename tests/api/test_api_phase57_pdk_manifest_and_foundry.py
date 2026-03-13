from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api import runs as run_store  # noqa: E402
from photonstrust.api.server import app  # noqa: E402
from photonstrust.benchmarks.schema import validate_instance  # noqa: E402
from photonstrust.pdk import resolve_pdk_contract  # noqa: E402
from photonstrust.workflow.schema import (  # noqa: E402
    pic_foundry_drc_sealed_summary_schema_path,
    pic_foundry_lvs_sealed_summary_schema_path,
    pic_foundry_pex_sealed_summary_schema_path,
)


def _pic_chain_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "phase57_api_pic_chain",
        "profile": "pic_circuit",
        "metadata": {"title": "Phase57 API PIC Chain", "description": "", "created_at": "2026-02-16"},
        "circuit": {"id": "phase57_api_pic_chain", "wavelength_nm": 1550},
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


def _sample_pdk_manifest(*, execution_mode: str = "preview", source_run_id: str | None = None) -> dict:
    contract = resolve_pdk_contract({"name": "generic_silicon_photonics"})
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pdk_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": execution_mode,
        "source_run_id": source_run_id,
        "adapter": contract["adapter"],
        "request": contract["request"],
        "pdk": contract["pdk"],
        "capabilities": contract["capabilities"],
    }


def _write_manual_layout_source_run(
    run_id: str,
    *,
    include_pdk_context: bool,
    include_gds: bool,
) -> Path:
    run_dir = run_store.run_dir_for_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    ports = {
        "schema_version": "0.1",
        "kind": "pic.ports",
        "ports": [
            {"node": "gc_in", "kind": "pic.grating_coupler", "port": "out", "role": "out", "x_um": -20.0, "y_um": 0.0},
            {"node": "wg_1", "kind": "pic.waveguide", "port": "in", "role": "in", "x_um": 80.0, "y_um": 0.0},
            {"node": "wg_1", "kind": "pic.waveguide", "port": "out", "role": "out", "x_um": 120.0, "y_um": 0.0},
            {"node": "ec_out", "kind": "pic.edge_coupler", "port": "in", "role": "in", "x_um": 220.0, "y_um": 0.0},
        ],
    }
    routes = {
        "schema_version": "0.1",
        "kind": "pic.routes",
        "routes": [
            {
                "route_id": "e1:gc_in.out->wg_1.in",
                "width_um": 0.5,
                "points_um": [[-20.0, 0.0], [80.0, 0.0]],
                "source": {"edge": {"from": "gc_in", "from_port": "out", "to": "wg_1", "to_port": "in", "kind": "optical"}},
            },
            {
                "route_id": "e2:wg_1.out->ec_out.in",
                "width_um": 0.5,
                "points_um": [[120.0, 0.0], [220.0, 0.0]],
                "source": {
                    "edge": {
                        "from": "wg_1",
                        "from_port": "out",
                        "to": "ec_out",
                        "to_port": "in",
                        "kind": "optical",
                    }
                },
            },
        ],
    }

    (run_dir / "ports.json").write_text(json.dumps(ports, indent=2), encoding="utf-8")
    (run_dir / "routes.json").write_text(json.dumps(routes, indent=2), encoding="utf-8")
    if include_gds:
        (run_dir / "layout.gds").write_bytes(b"PHOTONTRUST_PHASE57_LAYOUT_GDS")

    artifacts: dict[str, str] = {
        "ports_json": "ports.json",
        "routes_json": "routes.json",
    }
    if include_gds:
        artifacts["layout_gds"] = "layout.gds"

    input_obj: dict[str, object] = {"project_id": "default"}
    if include_pdk_context:
        input_obj["pdk"] = "generic_silicon_photonics"
        (run_dir / "pdk_manifest.json").write_text(
            json.dumps(_sample_pdk_manifest(source_run_id=run_id), indent=2),
            encoding="utf-8",
        )
        artifacts["pdk_manifest_json"] = "pdk_manifest.json"

    run_store.write_run_manifest(
        run_dir,
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "run_type": "manual_layout_drop",
            "generated_at": "2026-02-16T00:00:00+00:00",
            "output_dir": str(run_dir),
            "input": input_obj,
            "outputs_summary": {},
            "artifacts": artifacts,
            "provenance": {"python": "0", "platform": "0"},
        },
    )
    return run_dir


def test_phase57_layout_signoff_runs_emit_pdk_manifest_preview(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    graph = _pic_chain_graph()

    layout_res = client.post(
        "/v0/pic/layout/build",
        json={
            "graph": graph,
            "pdk": {"name": "generic_silicon_photonics"},
            "execution_mode": "preview",
        },
    )
    assert layout_res.status_code == 200
    layout_payload = layout_res.json()
    layout_dir = Path(layout_payload["output_dir"])
    assert (layout_dir / "pdk_manifest.json").exists()
    assert layout_payload.get("artifact_relpaths", {}).get("pdk_manifest_json") == "pdk_manifest.json"

    lvs_res = client.post(
        "/v0/pic/layout/lvs_lite",
        json={
            "graph": graph,
            "layout_run_id": layout_payload["run_id"],
            "execution_mode": "preview",
        },
    )
    assert lvs_res.status_code == 200
    lvs_payload = lvs_res.json()
    assert (Path(lvs_payload["output_dir"]) / "pdk_manifest.json").exists()
    assert lvs_payload.get("artifact_relpaths", {}).get("pdk_manifest_json") == "pdk_manifest.json"

    gds_rel = "phase57_preview_layout.gds"
    (layout_dir / gds_rel).write_bytes(b"PHOTONTRUST_PHASE57_GDS")
    klayout_res = client.post(
        "/v0/pic/layout/klayout/run",
        json={
            "source_run_id": layout_payload["run_id"],
            "gds_artifact_path": gds_rel,
            "execution_mode": "preview",
        },
    )
    assert klayout_res.status_code == 200
    klayout_payload = klayout_res.json()
    assert (Path(klayout_payload["output_dir"]) / "pdk_manifest.json").exists()
    assert klayout_payload.get("artifact_relpaths", {}).get("pdk_manifest_json") == "pdk_manifest.json"

    perf_res = client.post(
        "/v0/performance_drc/crosstalk",
        json={
            "gap_um": 0.6,
            "parallel_length_um": 1000.0,
            "wavelength_sweep_nm": [1550.0],
            "target_xt_db": -40.0,
            "pdk": {"name": "generic_silicon_photonics"},
            "execution_mode": "preview",
        },
    )
    assert perf_res.status_code == 200
    perf_payload = perf_res.json()
    assert (Path(perf_payload["output_dir"]) / "pdk_manifest.json").exists()
    assert perf_payload.get("artifact_relpaths", {}).get("pdk_manifest_json") == "pdk_manifest.json"


def test_phase57_lvs_certification_requires_pdk_manifest_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)
    graph = _pic_chain_graph()

    missing_ctx_run = "e" * 12
    _write_manual_layout_source_run(missing_ctx_run, include_pdk_context=False, include_gds=False)

    res = client.post(
        "/v0/pic/layout/lvs_lite",
        json={
            "graph": graph,
            "layout_run_id": missing_ctx_run,
            "execution_mode": "certification",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "pdk_manifest" in detail or "certification" in detail


def test_phase57_klayout_certification_requires_pdk_manifest_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))

    import photonstrust.layout.pic.klayout_runner as klr

    monkeypatch.setattr(klr, "find_klayout_exe", lambda: None)

    client = TestClient(app)
    missing_ctx_run = "f" * 12
    _write_manual_layout_source_run(missing_ctx_run, include_pdk_context=False, include_gds=True)

    res = client.post(
        "/v0/pic/layout/klayout/run",
        json={
            "source_run_id": missing_ctx_run,
            "gds_artifact_path": "layout.gds",
            "execution_mode": "certification",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "pdk_manifest" in detail or "certification" in detail


def test_phase57_performance_drc_certification_requires_explicit_pdk_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    res = client.post(
        "/v0/performance_drc/crosstalk",
        json={
            "gap_um": 0.6,
            "parallel_length_um": 1000.0,
            "wavelength_sweep_nm": [1550.0],
            "target_xt_db": -40.0,
            "execution_mode": "certification",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "pdk" in detail and "certification" in detail


def test_phase57_foundry_drc_sealed_run_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "a" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_drc/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "deck_fingerprint": "sha256:phase57-demo",
            "mock_result": {
                "checks": [
                    {"id": "DRC.WG.MIN_WIDTH", "name": "wg_min_width", "status": "pass"},
                    {"id": "DRC.WG.MIN_SPACING", "name": "wg_min_spacing", "status": "fail"},
                    {"id": "DRC.WG.MIN_BEND_RADIUS", "name": "wg_min_bend_radius", "status": "pass"},
                    {"id": "DRC.WG.MIN_ENCLOSURE", "name": "wg_min_enclosure", "status": "pass"},
                ]
            },
        },
    )
    assert res.status_code == 200
    payload = res.json()

    out_dir = Path(payload["output_dir"])
    assert (out_dir / "foundry_drc_sealed_summary.json").exists()
    assert (out_dir / "pdk_manifest.json").exists()

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    validate_instance(summary, pic_foundry_drc_sealed_summary_schema_path())
    assert summary.get("status") == "fail"

    manifest = json.loads(Path(payload["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["run_type"] == "pic_foundry_drc_sealed"
    assert manifest.get("artifacts", {}).get("pdk_manifest_json") == "pdk_manifest.json"


def test_phase57_foundry_drc_certification_requires_pdk_manifest_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "b" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=False, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_drc/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "certification",
            "backend": "mock",
            "mock_result": {"checks": []},
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "pdk_manifest" in detail or "certification" in detail


def test_phase57_foundry_drc_rejects_invalid_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "c" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_drc/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "unknown_backend",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "backend must be one of" in detail


def test_phase57_foundry_drc_rejects_invalid_run_id_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "d" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_drc/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "run_id": "BAD-RUN-ID",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "run_id must match" in detail


def test_phase57_foundry_drc_certification_rejects_mock_backend(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "e" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_drc/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "certification",
            "backend": "mock",
            "mock_result": {"checks": []},
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "non-mock" in detail and "foundry drc" in detail


def test_phase57_foundry_lvs_sealed_run_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "f" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_lvs/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "deck_fingerprint": "sha256:phase57-lvs",
            "mock_result": {
                "checks": [
                    {"id": "LVS.DEVICE.MATCH", "name": "device_match", "status": "pass"},
                ]
            },
        },
    )
    assert res.status_code == 200
    payload = res.json()
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    validate_instance(summary, pic_foundry_lvs_sealed_summary_schema_path())
    assert summary.get("status") == "pass"
    assert (Path(payload["output_dir"]) / "foundry_lvs_sealed_summary.json").exists()
    assert (Path(payload["output_dir"]) / "pdk_manifest.json").exists()


def test_phase57_foundry_pex_sealed_run_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "1" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        "/v0/pic/layout/foundry_pex/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "deck_fingerprint": "sha256:phase57-pex",
            "mock_result": {
                "checks": [
                    {"id": "PEX.RC.BOUNDS", "name": "rc_bounds", "status": "fail"},
                ]
            },
        },
    )
    assert res.status_code == 200
    payload = res.json()
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    validate_instance(summary, pic_foundry_pex_sealed_summary_schema_path())
    assert summary.get("status") == "fail"
    assert (Path(payload["output_dir"]) / "foundry_pex_sealed_summary.json").exists()
    assert (Path(payload["output_dir"]) / "pdk_manifest.json").exists()


def test_phase57_foundry_pex_local_backend_run_writes_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = "8" * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    routes = {
        "schema_version": "0.1",
        "kind": "pic.routes",
        "routes": [
            {
                "route_id": "e1:gc_in.out->wg_1.in",
                "points_um": [[-20.0, 0.0], [80.0, 0.0]],
                "coupling_coeff": 0.01,
                "source": {
                    "edge": {"from": "gc_in", "from_port": "out", "to": "wg_1", "to_port": "in", "kind": "optical"}
                },
            },
            {
                "route_id": "e2:wg_1.out->ec_out.in",
                "points_um": [[120.0, 0.0], [220.0, 0.0]],
                "coupling_coeff": 0.02,
                "source": {
                    "edge": {"from": "wg_1", "from_port": "out", "to": "ec_out", "to_port": "in", "kind": "optical"}
                },
            },
        ],
    }
    pdk_rules = {
        "design_rules": {
            "resistance_ohm_per_um": 0.02,
            "capacitance_ff_per_um": 0.002,
            "max_total_resistance_ohm": 5000.0,
            "max_total_capacitance_ff": 10000.0,
            "max_rc_delay_ps": 50000.0,
            "max_coupling_coeff": 0.1,
            "min_net_coverage_ratio": 1.0,
        }
    }

    res = client.post(
        "/v0/pic/layout/foundry_pex/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "local_pex",
            "deck_fingerprint": "sha256:phase57-pex-local",
            "graph": _pic_chain_graph(),
            "routes": routes,
            "pdk": pdk_rules,
        },
    )
    assert res.status_code == 200
    payload = res.json()
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    validate_instance(summary, pic_foundry_pex_sealed_summary_schema_path())
    assert summary.get("execution_backend") == "local_pex"
    assert summary.get("status") == "pass"
    assert (Path(payload["output_dir"]) / "foundry_pex_sealed_summary.json").exists()
    assert (Path(payload["output_dir"]) / "pdk_manifest.json").exists()


@pytest.mark.parametrize(
    ("endpoint", "stage"),
    [
        ("/v0/pic/layout/foundry_lvs/run", "foundry lvs"),
        ("/v0/pic/layout/foundry_pex/run", "foundry pex"),
    ],
)
def test_phase57_foundry_lvs_pex_certification_rejects_mock_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    stage: str,
) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = ("2" if "lvs" in endpoint else "3") * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        endpoint,
        json={
            "source_run_id": src_run,
            "execution_mode": "certification",
            "backend": "mock",
            "mock_result": {"checks": []},
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "non-mock" in detail and stage in detail


@pytest.mark.parametrize(
    "endpoint",
    [
        "/v0/pic/layout/foundry_lvs/run",
        "/v0/pic/layout/foundry_pex/run",
    ],
)
def test_phase57_foundry_lvs_pex_reject_invalid_run_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = ("4" if "lvs" in endpoint else "5") * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        endpoint,
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "run_id": "BAD-RUN-ID",
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "run_id must match" in detail


@pytest.mark.parametrize(
    ("endpoint", "backend"),
    [
        ("/v0/pic/layout/foundry_lvs/run", "unsupported"),
        ("/v0/pic/layout/foundry_pex/run", "local_lvs"),
    ],
)
def test_phase57_foundry_lvs_pex_reject_invalid_backend(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: str,
    backend: str,
) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    src_run = ("6" if "lvs" in endpoint else "7") * 12
    _write_manual_layout_source_run(src_run, include_pdk_context=True, include_gds=True)

    res = client.post(
        endpoint,
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": backend,
        },
    )
    assert res.status_code == 400
    detail = str((res.json() or {}).get("detail", "")).lower()
    assert "backend must be one of" in detail
