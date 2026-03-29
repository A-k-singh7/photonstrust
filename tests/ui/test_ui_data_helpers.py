from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui.data import (
    diagnose_api_runtime_error,
    get_ui_project_baseline,
    load_ui_product_state,
    promote_ui_project_baseline,
    save_ui_pic_run_bundle,
    save_ui_product_state,
    save_ui_run_profile,
    stable_json_hash,
)


def _disallowed_results_root() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / "photonstrust_test_results"
    return Path("/var/opt/photonstrust_test_results")


def test_stable_json_hash_is_order_independent() -> None:
    payload_a = {"b": 1, "a": {"y": 2, "x": [1, 2, 3]}}
    payload_b = {"a": {"x": [1, 2, 3], "y": 2}, "b": 1}
    assert stable_json_hash(payload_a) == stable_json_hash(payload_b)


def test_save_ui_run_profile_default_filename(tmp_path: Path) -> None:
    profile = {"schema_version": "0.1", "kind": "photonstrust.ui_run_profile", "builder_state": {"mu": 0.5}}
    path = save_ui_run_profile(results_root=tmp_path, profile=profile)
    assert path.exists()
    assert path.parent == tmp_path / "ui_profiles"
    assert path.name.startswith("profile_")
    assert path.suffix == ".json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == profile


def test_save_ui_run_profile_named_filename_is_sanitized(tmp_path: Path) -> None:
    profile = {"schema_version": "0.1", "kind": "photonstrust.ui_run_profile", "builder_state": {"mu": 0.5}}
    path = save_ui_run_profile(results_root=tmp_path, profile=profile, profile_name="My Profile 01!")
    assert path.exists()
    assert path.name == "my_profile_01.json"


def test_save_ui_run_profile_rejects_disallowed_results_root() -> None:
    profile = {"schema_version": "0.1", "kind": "photonstrust.ui_run_profile", "builder_state": {"mu": 0.5}}
    with pytest.raises(ValueError, match="results_root"):
        save_ui_run_profile(results_root=_disallowed_results_root(), profile=profile)


def test_diagnose_api_runtime_error_connectivity() -> None:
    diag = diagnose_api_runtime_error("Could not reach API at http://127.0.0.1:8000: Connection refused")
    assert diag["category"] == "connectivity"
    assert "Start API server" in diag["hint"]


def test_diagnose_api_runtime_error_validation_with_cert_hint() -> None:
    diag = diagnose_api_runtime_error(
        "API request failed (400): certification mode requires explicit pdk manifest context "
        "(provide payload.pdk or payload.pdk_manifest)"
    )
    assert diag["category"] == "input_validation"
    assert "preview" in diag["hint"].lower()


def test_diagnose_api_runtime_error_auth_scope() -> None:
    diag = diagnose_api_runtime_error("API request failed (403): forbidden")
    assert diag["category"] == "auth_scope"


def test_diagnose_api_runtime_error_backend_failure() -> None:
    diag = diagnose_api_runtime_error("API request failed (500): internal server error")
    assert diag["category"] == "backend_failure"


def test_ui_product_state_defaults(tmp_path: Path) -> None:
    state = load_ui_product_state(tmp_path)
    assert state["schema_version"] == "0.1"
    assert state["kind"] == "photonstrust.ui_product_state"
    assert state["baselines"] == {}


def test_ui_product_state_save_and_load_roundtrip(tmp_path: Path) -> None:
    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.ui_product_state",
        "baselines": {"default": {"scenario_id": "s1"}},
    }
    path = save_ui_product_state(tmp_path, payload)
    assert path.exists()
    loaded = load_ui_product_state(tmp_path)
    assert loaded["baselines"]["default"]["scenario_id"] == "s1"


def test_promote_and_get_project_baseline(tmp_path: Path) -> None:
    record, path = promote_ui_project_baseline(
        results_root=tmp_path,
        project_id="MyProject",
        baseline_record={
            "scenario_id": "scenario_a",
            "band": "c_1550",
            "card_path": "results/x/reliability_card.json",
            "key_rate_bps": 123.0,
            "qber_total": 0.01,
            "safe_use_label": "engineering_grade",
            "card_hash": "abc",
        },
    )
    assert path.exists()
    assert record["project_id"] == "myproject"
    loaded = get_ui_project_baseline(tmp_path, "MYPROJECT")
    assert loaded is not None
    assert loaded["scenario_id"] == "scenario_a"
    assert loaded["band"] == "c_1550"


def test_save_ui_pic_run_bundle_writes_expected_files(tmp_path: Path) -> None:
    request_payload = {
        "graph": {
            "schema_version": "0.1",
            "graph_id": "ui_pic_chain",
            "profile": "pic_circuit",
            "circuit": {"id": "ui_pic_chain", "wavelength_nm": 1550.0},
            "nodes": [],
            "edges": [],
        },
        "wavelength_nm": 1550.0,
    }
    response_payload = {
        "generated_at": "2026-02-18T00:00:00+00:00",
        "graph_hash": "abc123",
        "netlist": {"nodes": [], "edges": []},
        "results": {
            "chain_solver": {"eta_total": 0.5, "total_loss_db": 3.0},
            "scattering_solver": {"applicable": False, "reason": "circuit.solver is not 'scattering'"},
        },
    }

    saved = save_ui_pic_run_bundle(
        results_root=tmp_path,
        request_payload=request_payload,
        response_payload=response_payload,
    )
    bundle_dir = saved["bundle_dir"]
    assert bundle_dir.exists()
    assert bundle_dir.parent == tmp_path / "ui_pic_runs"

    for key in ("request_json", "response_json", "graph_json", "netlist_json", "summary_json", "summary_md"):
        assert key in saved
        assert saved[key].exists()

    summary = json.loads(saved["summary_json"].read_text(encoding="utf-8"))
    assert summary["kind"] == "photonstrust.ui_pic_run_bundle"
    assert summary["graph_id"] == "ui_pic_chain"
    assert summary["overview"]["mode"] == "single"
