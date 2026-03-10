from __future__ import annotations

from pathlib import Path

import photonstrust.pipeline.satellite_chain_sweep as sweep_mod
from photonstrust.benchmarks.schema import validate_instance
from photonstrust.workflow.schema import satellite_qkd_chain_sweep_schema_path


def _write_minimal_config(path: Path, mission_id: str) -> Path:
    path.write_text(
        f"schema_version: '0.1'\nsatellite_qkd_chain:\n  id: {mission_id}\n",
        encoding="utf-8",
    )
    return path


def test_sweep_report_validates_against_schema(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cfg_path = _write_minimal_config(tmp_path / "alpha.yml", "alpha")

    def _fake_run_satellite_chain(config: dict, *, output_dir: Path):
        _ = config
        output_dir.mkdir(parents=True, exist_ok=True)
        cert_path = output_dir / "satellite_qkd_chain_certificate.json"
        cert_path.write_text("{}", encoding="utf-8")
        return {
            "decision": "GO",
            "key_bits_accumulated": 12.0,
            "mean_key_rate_bps": 3.0,
            "output_path": str(cert_path),
        }

    monkeypatch.setattr(sweep_mod, "run_satellite_chain", _fake_run_satellite_chain)

    payload = sweep_mod.run_satellite_chain_sweep(
        [cfg_path],
        output_root=tmp_path / "out",
        backend="local",
        max_workers=1,
        tracking_mode=None,
    )
    validate_instance(payload, satellite_qkd_chain_sweep_schema_path())
