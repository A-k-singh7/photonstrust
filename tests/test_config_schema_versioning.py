from __future__ import annotations

import subprocess
import sys

import pytest

from photonstrust.config import ConfigSchemaVersionError, load_config


def _scenario_config_yaml(*, schema_version: str | None) -> str:
    version_line = f'schema_version: "{schema_version}"\n' if schema_version is not None else ""
    return (
        version_line
        + """
scenario:
  id: schema_versioning_smoke
  distance_km: 1.0
  band: c_1550
  wavelength_nm: null

source:
  type: emitter_cavity
  physics_backend: analytic
  rep_rate_mhz: 100
  collection_efficiency: 0.35
  coupling_efficiency: 0.6
  g2_0: 0.02

channel:
  fiber_loss_db_per_km: 0.2
  connector_loss_db: 1.5
  dispersion_ps_per_km: 5

detector:
  class: snspd
  pde: 0.3
  dark_counts_cps: 100
  jitter_ps_fwhm: 30
  dead_time_ns: 100
  afterpulsing_prob: 0.001

timing:
  sync_drift_ps_rms: 10
  coincidence_window_ps: null

protocol:
  name: BBM92
  sifting_factor: 0.5
  ec_efficiency: 1.16

uncertainty: {}
"""
    )


def test_load_config_migrates_missing_schema_version(tmp_path) -> None:
    cfg_path = tmp_path / "legacy_missing_schema.yml"
    cfg_path.write_text(_scenario_config_yaml(schema_version=None), encoding="utf-8")

    config = load_config(cfg_path)

    assert config["schema_version"] == "0.1"


def test_load_config_migrates_legacy_zero_schema_version(tmp_path) -> None:
    cfg_path = tmp_path / "legacy_zero_schema.yml"
    cfg_path.write_text(_scenario_config_yaml(schema_version="0"), encoding="utf-8")

    config = load_config(cfg_path)

    assert config["schema_version"] == "0.1"


def test_load_config_rejects_unsupported_schema_version(tmp_path) -> None:
    cfg_path = tmp_path / "unsupported_schema.yml"
    cfg_path.write_text(_scenario_config_yaml(schema_version="9.9"), encoding="utf-8")

    with pytest.raises(ConfigSchemaVersionError) as exc_info:
        load_config(cfg_path)

    msg = str(exc_info.value)
    assert "Unsupported scenario config schema_version '9.9'" in msg
    assert "docs/audit/03_configuration_validation.md" in msg


def test_cli_validate_only_fails_fast_for_unsupported_schema_version(tmp_path) -> None:
    cfg_path = tmp_path / "unsupported_schema_cli.yml"
    cfg_path.write_text(_scenario_config_yaml(schema_version="2.0"), encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, "-m", "photonstrust.cli", "run", str(cfg_path), "--validate-only"],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "Unsupported scenario config schema_version '2.0'" in completed.stderr
