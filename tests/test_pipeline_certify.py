from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

import photonstrust.pipeline.certify as certify_mod
from photonstrust.pipeline.certify import run_certify


REPO_ROOT = Path(__file__).resolve().parents[1]


def _graph(*, width_um: float = 0.5) -> dict:
    return {
        "schema_version": "0.1",
        "graph_id": "pic_qkd_cert_test_graph",
        "profile": "pic_circuit",
        "circuit": {"id": "pic_qkd_cert_test_graph", "wavelength_nm": 1550.0},
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {}},
            {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 200.0, "width_um": float(width_um)}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {}},
        ],
        "edges": [
            {"from": "gc_in", "to": "wg_1", "kind": "optical"},
            {"from": "wg_1", "to": "ec_out", "kind": "optical"},
        ],
    }


def test_run_certify_dry_run_returns_payload_and_writes_certificate(tmp_path: Path) -> None:
    out_dir = tmp_path / "certify_dry_run"
    result = run_certify(
        _graph(),
        output_dir=out_dir,
        dry_run=True,
        distances_km=[0.0, 25.0, 50.0],
        target_distance_km=50.0,
    )

    assert result["decision"] == "GO"
    assert isinstance(result["certificate"], dict)
    assert result["output_path"] is not None

    certificate_path = Path(str(result["output_path"]))
    assert certificate_path.exists()

    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    assert certificate["kind"] == "photonstrust.pic_qkd_certificate"
    assert certificate["decision"] == "GO"
    assert certificate["inputs"]["dry_run"] is True
    assert certificate["qkd_sweep"] is None
    assert certificate["artifacts"]["certificate_path"] == str(certificate_path)


def test_run_certify_dry_run_does_not_import_simulator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = certify_mod.importlib.import_module

    def _guarded_import(name: str, *args, **kwargs):
        if name == "photonstrust.pic.simulate":
            raise ModuleNotFoundError("simulator import should not happen in dry-run")
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(certify_mod.importlib, "import_module", _guarded_import)
    result = run_certify(_graph(), output_dir=tmp_path / "dry_run_guarded", dry_run=True)
    assert result["decision"] == "GO"
    assert result["certificate"]["inputs"]["dry_run"] is True
    assert result["certificate"]["pex_summary"]["status"] == "pass"


def test_run_certify_hold_when_drc_or_lvs_fail_fixture(tmp_path: Path) -> None:
    out_dir = tmp_path / "certify_hold_case"
    result = run_certify(_graph(width_um=0.1), output_dir=out_dir, dry_run=True)

    assert result["decision"] == "HOLD"
    certificate = result["certificate"]
    assert certificate["drc_summary"]["status"] == "fail"
    assert certificate["signoff"]["decision"] == "HOLD"


def test_run_certify_full_mode_handles_missing_simulator_import_as_hold(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_import_module = certify_mod.importlib.import_module

    def _guarded_import(name: str, *args, **kwargs):
        if name == "photonstrust.pic.simulate":
            raise ModuleNotFoundError("simulator unavailable")
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(certify_mod.importlib, "import_module", _guarded_import)
    result = run_certify(_graph(), output_dir=tmp_path / "full_mode_missing_sim", dry_run=False)

    assert result["decision"] == "HOLD"
    certificate = result["certificate"]
    assert certificate["pex_summary"]["status"] == "error"
    assert certificate["pex_summary"]["failed_check_ids"] == ["PEX.SIMULATION_ERROR"]
    assert certificate["target_distance_summary"]["reason"] == "simulation_failed"
    assert certificate["signoff"]["decision"] == "HOLD"


def test_cli_certify_require_go_exits_non_zero_on_hold(tmp_path: Path) -> None:
    graph_path = tmp_path / "hold_graph.json"
    graph_path.write_text(json.dumps(_graph(width_um=0.1), indent=2), encoding="utf-8")

    out_dir = tmp_path / "cli_hold_output"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "photonstrust.cli",
            "certify",
            str(graph_path),
            "--output",
            str(out_dir),
            "--dry-run",
            "--require-go",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1, completed.stdout + completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["decision"] == "HOLD"
    assert Path(out_dir / "certificate.json").exists()
