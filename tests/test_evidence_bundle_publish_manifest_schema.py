from __future__ import annotations

import json
from pathlib import Path

import pytest


pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from photonstrust.api.server import app  # noqa: E402
from photonstrust.benchmarks.schema import validate_instance  # noqa: E402
from photonstrust.workflow.schema import evidence_bundle_publish_manifest_schema_path  # noqa: E402


def _orbit_pass_config() -> dict:
    return {
        "orbit_pass": {
            "id": "publish_manifest_schema_orbit",
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


def test_evidence_bundle_publish_manifest_validates_against_schema(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOTONTRUST_API_RUNS_ROOT", str(tmp_path))
    client = TestClient(app)

    run = client.post("/v0/orbit/pass/run", json={"config": _orbit_pass_config()})
    assert run.status_code == 200
    run_id = str((run.json() or {}).get("run_id") or "")
    assert run_id

    publish = client.post(f"/v0/runs/{run_id}/bundle/publish", params={"include_children": "false"})
    assert publish.status_code == 200
    payload = publish.json()

    manifest_path = payload.get("publish_manifest_path")
    assert isinstance(manifest_path, str) and manifest_path
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))

    validate_instance(manifest, evidence_bundle_publish_manifest_schema_path())

    digest = str(payload.get("bundle_sha256") or "")
    verify = client.get(f"/v0/evidence/bundle/by-digest/{digest}/verify")
    assert verify.status_code == 200
    verify_payload = verify.json()
    assert (verify_payload.get("verify") or {}).get("ok") is True
