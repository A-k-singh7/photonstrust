from __future__ import annotations

from pathlib import Path

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402


def _headers(*, actor: str, roles: str, projects: str = "*") -> dict[str, str]:
    return {
        "x-photonstrust-actor": actor,
        "x-photonstrust-roles": roles,
        "x-photonstrust-projects": projects,
    }


def _qkd_graph() -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "api_qkd_link_v1",
        "profile": "qkd_link",
        "metadata": {"title": "API QKD Graph v1", "description": "", "created_at": "2026-03-01"},
        "scenario": {
            "id": "api_qkd_link_v1",
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
            {"id": "protocol_1", "kind": "qkd.protocol", "params": {"name": "BBM92"}},
        ],
        "edges": [
            {"from": "source_1", "to": "channel_1", "kind": "optical"},
            {"from": "channel_1", "to": "detector_1", "kind": "optical"},
        ],
    }


def _orbit_pass_config() -> dict:
    return {
        "orbit_pass": {
            "id": "api_orbit_pass_v1_scope",
            "band": "c_1550",
            "dt_s": 30,
            "samples": [
                {"t_s": 0, "distance_km": 10, "elevation_deg": 20, "background_counts_cps": 0},
                {"t_s": 30, "distance_km": 50, "elevation_deg": 40, "background_counts_cps": 0},
                {"t_s": 60, "distance_km": 100, "elevation_deg": 70, "background_counts_cps": 0},
            ],
            "cases": [{"id": "median", "label": "Median", "channel_overrides": {}}],
        },
        "source": {"type": "emitter_cavity", "g2_0": 0.0},
        "channel": {"model": "free_space"},
        "detector": {"class": "snspd"},
        "timing": {},
        "protocol": {"name": "BBM92"},
        "uncertainty": {},
    }


def test_v1_runs_typed_list_includes_request_id_and_header(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    monkeypatch.setenv("PHOTONTRUST_API_AUTH_MODE", "header")
    client = TestClient(app)

    create = client.post("/v0/qkd/run", json={"graph": _qkd_graph(), "project_id": "v1_proj_a"})
    assert create.status_code == 200

    req_id = "req-v1-list-123"
    res = client.get(
        "/v1/runs",
        headers={**_headers(actor="viewer_a", roles="viewer", projects="v1_proj_a"), "x-request-id": req_id},
    )
    assert res.status_code == 200
    payload = res.json()

    assert res.headers.get("x-request-id") == req_id
    assert payload.get("request_id") == req_id
    runs = payload.get("runs") or []
    assert runs and isinstance(runs, list)
    first = runs[0]
    assert "run_id" in first
    assert "run_type" in first
    assert "project_id" in first


def test_v1_error_envelope_for_denied_scope_and_invalid_payload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    monkeypatch.setenv("PHOTONTRUST_API_AUTH_MODE", "header")
    client = TestClient(app)

    created = client.post(
        "/v0/orbit/pass/run",
        json={"config": _orbit_pass_config(), "project_id": "scope_project"},
    )
    assert created.status_code == 200

    denied = client.get(
        "/v1/runs",
        params={"project_id": "scope_project"},
        headers=_headers(actor="viewer_scope", roles="viewer", projects="other_project"),
    )
    assert denied.status_code == 403
    denied_payload = denied.json()
    assert denied_payload.get("error", {}).get("code") == "forbidden"
    assert denied_payload.get("error", {}).get("detail")
    assert denied_payload.get("error", {}).get("request_id") == denied.headers.get("x-request-id")
    assert denied_payload.get("error", {}).get("retryable") is False

    invalid = client.post("/v1/qkd/run", json={"execution_mode": "preview"})
    assert invalid.status_code == 422
    invalid_payload = invalid.json()
    assert invalid_payload.get("error", {}).get("code") == "validation_error"
    assert invalid_payload.get("error", {}).get("request_id") == invalid.headers.get("x-request-id")
    assert invalid_payload.get("error", {}).get("retryable") is False


def test_v0_v1_run_get_compatibility_for_core_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    created = client.post("/v0/qkd/run", json={"graph": _qkd_graph(), "project_id": "compat_proj"})
    assert created.status_code == 200
    run_id = str((created.json() or {}).get("run_id") or "")
    assert run_id

    v0 = client.get(f"/v0/runs/{run_id}")
    assert v0.status_code == 200
    v0_payload = v0.json()

    v1 = client.get(f"/v1/runs/{run_id}")
    assert v1.status_code == 200
    v1_payload = v1.json()
    v1_run = v1_payload.get("run") or {}

    assert v0_payload.get("run_id") == v1_run.get("run_id")
    assert v0_payload.get("run_type") == v1_run.get("run_type")
    assert (v0_payload.get("input") or {}).get("project_id") == (v1_run.get("input") or {}).get("project_id")
