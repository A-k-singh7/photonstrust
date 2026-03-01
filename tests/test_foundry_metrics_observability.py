from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api import foundry_metrics as foundry_metrics_store  # noqa: E402
from photonstrust.api import runs as run_store  # noqa: E402
from photonstrust.api.server import app  # noqa: E402
from photonstrust.pdk import resolve_pdk_contract  # noqa: E402


def _sample_pdk_manifest(*, source_run_id: str | None = None) -> dict:
    contract = resolve_pdk_contract({"name": "generic_silicon_photonics"})
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.pdk_manifest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "execution_mode": "preview",
        "source_run_id": source_run_id,
        "adapter": contract["adapter"],
        "request": contract["request"],
        "pdk": contract["pdk"],
        "capabilities": contract["capabilities"],
    }


def _write_manual_layout_source_run(run_id: str) -> Path:
    run_dir = run_store.run_dir_for_id(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "ports.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "kind": "pic.ports",
                "ports": [
                    {
                        "node": "gc_in",
                        "kind": "pic.grating_coupler",
                        "port": "out",
                        "role": "out",
                        "x_um": -20.0,
                        "y_um": 0.0,
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "routes.json").write_text(
        json.dumps(
            {
                "schema_version": "0.1",
                "kind": "pic.routes",
                "routes": [
                    {
                        "route_id": "e1:gc_in.out->gc_out.in",
                        "width_um": 0.5,
                        "points_um": [[-20.0, 0.0], [80.0, 0.0]],
                        "source": {
                            "edge": {
                                "from": "gc_in",
                                "from_port": "out",
                                "to": "gc_out",
                                "to_port": "in",
                                "kind": "optical",
                            }
                        },
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "layout.gds").write_bytes(b"PHOTONTRUST_TEST_LAYOUT_GDS")
    (run_dir / "pdk_manifest.json").write_text(
        json.dumps(_sample_pdk_manifest(source_run_id=run_id), indent=2),
        encoding="utf-8",
    )

    run_store.write_run_manifest(
        run_dir,
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "run_type": "manual_layout_drop",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "output_dir": str(run_dir),
            "input": {"project_id": "default", "pdk": "generic_silicon_photonics"},
            "outputs_summary": {},
            "artifacts": {
                "ports_json": "ports.json",
                "routes_json": "routes.json",
                "layout_gds": "layout.gds",
                "pdk_manifest_json": "pdk_manifest.json",
            },
            "provenance": {"python": "0", "platform": "0"},
        },
    )
    return run_dir


def test_foundry_metrics_aggregation_rates_and_percentiles() -> None:
    events = [
        {"execution_backend": "generic_cli", "outcome": "success", "duration_ms": 100},
        {"execution_backend": "generic_cli", "outcome": "success", "duration_ms": 200},
        {"execution_backend": "generic_cli", "outcome": "timeout", "duration_ms": 300},
        {"execution_backend": "generic_cli", "outcome": "nonzero", "duration_ms": 400},
        {"execution_backend": "generic_cli", "outcome": "error", "duration_ms": 500},
        {"execution_backend": "mock", "outcome": "success", "duration_ms": 50},
        {"execution_backend": "mock", "outcome": "success", "duration_ms": 60},
    ]

    summary = foundry_metrics_store.aggregate_foundry_metrics(events)
    by_backend = summary.get("by_backend", {})

    assert by_backend["generic_cli"]["total"] == 5
    assert by_backend["generic_cli"]["success"] == 2
    assert by_backend["generic_cli"]["timeout"] == 1
    assert by_backend["generic_cli"]["nonzero"] == 1
    assert by_backend["generic_cli"]["error"] == 1
    assert by_backend["generic_cli"]["success_rate"] == 0.4
    assert by_backend["generic_cli"]["timeout_rate"] == 0.2
    assert by_backend["generic_cli"]["nonzero_rate"] == 0.2
    assert by_backend["generic_cli"]["duration_ms"]["p50"] == 300
    assert by_backend["generic_cli"]["duration_ms"]["p95"] == 500

    assert by_backend["mock"]["total"] == 2
    assert by_backend["mock"]["success"] == 2
    assert by_backend["mock"]["success_rate"] == 1.0
    assert by_backend["mock"]["duration_ms"]["p50"] == 50
    assert by_backend["mock"]["duration_ms"]["p95"] == 60


def test_foundry_metrics_outcome_classification_timeout_nonzero() -> None:
    assert foundry_metrics_store.classify_foundry_outcome(status="error", error_code="timeout") == "timeout"
    assert foundry_metrics_store.classify_foundry_outcome(status="error", error_code="generic_cli_timeout") == "timeout"
    assert foundry_metrics_store.classify_foundry_outcome(status="error", error_code="command_failed") == "nonzero"
    assert foundry_metrics_store.classify_foundry_outcome(status="error", error_code="generic_cli_nonzero_exit") == "nonzero"
    assert foundry_metrics_store.classify_foundry_outcome(status="pass", error_code=None) == "success"
    assert foundry_metrics_store.classify_foundry_outcome(status="fail", error_code=None) == "success"
    assert foundry_metrics_store.classify_foundry_outcome(status="error", error_code="other_error") == "error"


def test_foundry_endpoints_emit_metrics_events_and_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runs_root = tmp_path / "api_runs"
    results_root = tmp_path / "results"
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(runs_root))
    monkeypatch.setenv("PHOTONTRUST_RESULTS_ROOT", str(results_root))

    client = TestClient(app)
    src_run = "9" * 12
    _write_manual_layout_source_run(src_run)

    drc = client.post(
        "/v0/pic/layout/foundry_drc/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "deck_fingerprint": "sha256:day8-drc",
            "mock_result": {"checks": [{"id": "DRC.WG.MIN_WIDTH", "status": "pass"}]},
        },
    )
    assert drc.status_code == 200

    lvs = client.post(
        "/v0/pic/layout/foundry_lvs/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "deck_fingerprint": "sha256:day8-lvs",
            "mock_result": {"checks": [{"id": "LVS.DEVICE.MATCH", "status": "pass"}]},
        },
    )
    assert lvs.status_code == 200

    pex = client.post(
        "/v0/pic/layout/foundry_pex/run",
        json={
            "source_run_id": src_run,
            "execution_mode": "preview",
            "backend": "mock",
            "deck_fingerprint": "sha256:day8-pex",
            "mock_result": {"checks": [{"id": "PEX.RC.BOUNDS", "status": "fail"}]},
        },
    )
    assert pex.status_code == 200

    events = foundry_metrics_store.read_foundry_metric_events(limit=100)
    run_ids = {str(drc.json().get("run_id")), str(lvs.json().get("run_id")), str(pex.json().get("run_id"))}
    run_events = [row for row in events if str(row.get("run_id")) in run_ids]
    assert len(run_events) == 3

    for row in run_events:
        assert row.get("kind") == "photonstrust.foundry_metric_event"
        assert row.get("execution_backend") == "mock"
        assert row.get("outcome") == "success"
        assert isinstance(row.get("duration_ms"), int)
        assert row.get("duration_ms") >= 0

    summary_res = client.get("/v0/metrics/foundry/summary", params={"limit": 100})
    assert summary_res.status_code == 200
    summary_payload = summary_res.json()
    assert int(summary_payload.get("event_count", 0)) >= 3
    summary_obj = summary_payload.get("summary") if isinstance(summary_payload.get("summary"), dict) else {}
    mock_row = (summary_obj.get("by_backend") or {}).get("mock")
    assert isinstance(mock_row, dict)
    assert mock_row.get("total", 0) >= 3
    assert mock_row.get("timeout_rate") == 0.0
    assert mock_row.get("nonzero_rate") == 0.0
    assert 0.0 <= float(mock_row.get("success_rate", 0.0)) <= 1.0
