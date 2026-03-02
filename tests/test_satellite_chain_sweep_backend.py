from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import photonstrust.pipeline.satellite_chain_sweep as sweep_mod


def _write_minimal_config(path: Path, mission_id: str) -> Path:
    payload = {
        "schema_version": "0.1",
        "satellite_qkd_chain": {
            "id": mission_id,
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_satellite_chain_sweep_local_backend_with_minimal_configs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_beta = _write_minimal_config(tmp_path / "beta.yml", "beta")
    cfg_alpha = _write_minimal_config(tmp_path / "alpha.yml", "alpha")

    def _fake_run_satellite_chain(config: dict, *, output_dir: Path):
        mission_id = str(((config.get("satellite_qkd_chain") or {}).get("id")) or "mission")
        output_dir.mkdir(parents=True, exist_ok=True)
        is_go = mission_id == "alpha"
        key_bits = 120.0 if is_go else 30.0
        mean_rate = 12.0 if is_go else 3.0
        cert_path = output_dir / "satellite_qkd_chain_certificate.json"
        cert_path.write_text("{}", encoding="utf-8")
        return {
            "decision": "GO" if is_go else "HOLD",
            "key_bits_accumulated": key_bits,
            "mean_key_rate_bps": mean_rate,
            "output_path": str(cert_path),
        }

    monkeypatch.setattr(sweep_mod, "run_satellite_chain", _fake_run_satellite_chain)

    payload = sweep_mod.run_satellite_chain_sweep(
        [cfg_beta, cfg_alpha],
        output_root=tmp_path / "sweep_out",
        backend="local",
        max_workers=2,
    )

    summary = payload["summary"]
    assert summary["backend"] == "local"
    assert summary["run_count"] == 2
    assert summary["decision_counts"] == {"GO": 1, "HOLD": 1}
    assert summary["key_bits_total"] == pytest.approx(150.0)
    assert summary["mean_key_rate_bps_avg"] == pytest.approx(7.5)

    runs = payload["runs"]
    assert [row["mission_id"] for row in runs] == ["alpha", "beta"]

    report_path = Path(str(payload["report_path"]))
    assert report_path.is_file()
    written = json.loads(report_path.read_text(encoding="utf-8"))
    assert written["kind"] == "satellite_qkd_chain_sweep"
    assert written["summary"]["run_count"] == 2


def test_satellite_chain_sweep_ray_backend_errors_when_ray_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg_alpha = _write_minimal_config(tmp_path / "alpha.yml", "alpha")
    monkeypatch.setitem(sys.modules, "ray", None)

    with pytest.raises(RuntimeError, match="Ray backend requested but ray is not installed"):
        sweep_mod.run_satellite_chain_sweep(
            [cfg_alpha],
            output_root=tmp_path / "sweep_out",
            backend="ray",
            max_workers=1,
        )

