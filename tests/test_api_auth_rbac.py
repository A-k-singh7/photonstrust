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


def _orbit_pass_config() -> dict:
    return {
        "orbit_pass": {
            "id": "api_orbit_pass_auth",
            "band": "c_1550",
            "dt_s": 30,
            "samples": [
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


def test_auth_header_mode_requires_headers_for_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    monkeypatch.setenv("PHOTONTRUST_API_AUTH_MODE", "header")
    client = TestClient(app)

    no_auth = client.get("/v0/runs")
    assert no_auth.status_code == 401

    ok = client.get("/v0/runs", headers=_headers(actor="viewer_a", roles="viewer"))
    assert ok.status_code == 200


def test_auth_project_scope_blocks_run_read(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    monkeypatch.setenv("PHOTONTRUST_API_AUTH_MODE", "header")
    client = TestClient(app)

    project_id = "pt_auth_proj"
    run_res = client.post(
        "/v0/orbit/pass/run",
        json={"config": _orbit_pass_config(), "project_id": project_id},
        headers=_headers(actor="runner_a", roles="runner", projects="*"),
    )
    assert run_res.status_code == 200
    run_id = str((run_res.json() or {}).get("run_id") or "")
    assert run_id

    denied = client.get(
        f"/v0/runs/{run_id}",
        headers=_headers(actor="viewer_b", roles="viewer", projects="other_proj"),
    )
    assert denied.status_code == 403

    allowed = client.get(
        f"/v0/runs/{run_id}",
        headers=_headers(actor="viewer_b", roles="viewer", projects=project_id),
    )
    assert allowed.status_code == 200


def test_auth_approver_role_required_for_approvals(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    monkeypatch.setenv("PHOTONTRUST_API_AUTH_MODE", "header")
    client = TestClient(app)

    project_id = "pt_auth_approval"
    run_res = client.post(
        "/v0/orbit/pass/run",
        json={"config": _orbit_pass_config(), "project_id": project_id},
        headers=_headers(actor="runner_a", roles="runner", projects="*"),
    )
    assert run_res.status_code == 200
    run_id = str((run_res.json() or {}).get("run_id") or "")
    assert run_id

    viewer_post = client.post(
        f"/v0/projects/{project_id}/approvals",
        json={"run_id": run_id, "actor": "payload_actor", "note": "viewer should fail"},
        headers=_headers(actor="viewer_a", roles="viewer", projects=project_id),
    )
    assert viewer_post.status_code == 403

    wrong_scope = client.post(
        f"/v0/projects/{project_id}/approvals",
        json={"run_id": run_id, "actor": "payload_actor", "note": "wrong scope"},
        headers=_headers(actor="approver_a", roles="approver", projects="other_proj"),
    )
    assert wrong_scope.status_code == 403

    ok = client.post(
        f"/v0/projects/{project_id}/approvals",
        json={"run_id": run_id, "actor": "payload_actor", "note": "approved"},
        headers=_headers(actor="approver_a", roles="approver", projects=project_id),
    )
    assert ok.status_code == 200
    event = (ok.json() or {}).get("event") or {}
    assert event.get("actor") == "approver_a"
