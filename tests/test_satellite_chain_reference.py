from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from photonstrust.config import load_config
from photonstrust.pipeline.satellite_chain import run_satellite_chain


REPO_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "satellite_chain_reference.json"
REFERENCE_CONFIG = REPO_ROOT / "configs" / "satellite" / "eagle1_analog_berlin.yml"


def _path_to_repo_rel_or_placeholder(raw: object, *, repo_root: Path) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return "<MISSING_PATH>"
    try:
        rel = Path(raw).resolve().relative_to(repo_root.resolve())
        return rel.as_posix()
    except Exception:
        return "<ABS_PATH>"


def _round_floats(obj: Any) -> Any:
    if isinstance(obj, float):
        return round(float(obj), 12)
    if isinstance(obj, list):
        return [_round_floats(item) for item in obj]
    if isinstance(obj, tuple):
        return [_round_floats(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): _round_floats(value) for key, value in obj.items()}
    return obj


def _canonicalize_certificate(certificate: dict[str, Any], *, repo_root: Path) -> dict[str, Any]:
    payload = copy.deepcopy(certificate)
    payload["generated_at"] = "<GENERATED_AT>"
    payload["run_id"] = "<RUN_ID>"

    inputs = payload.get("inputs")
    if isinstance(inputs, dict):
        inputs["output_dir"] = "<OUTPUT_DIR>"
        signing_key = inputs.get("signing_key")
        if signing_key is not None:
            inputs["signing_key"] = _path_to_repo_rel_or_placeholder(signing_key, repo_root=repo_root)

    artifacts = payload.get("artifacts")
    if isinstance(artifacts, dict):
        if artifacts.get("pic_certificate_path") is not None:
            artifacts["pic_certificate_path"] = _path_to_repo_rel_or_placeholder(
                artifacts.get("pic_certificate_path"),
                repo_root=repo_root,
            )

    rounded = _round_floats(payload)
    assert isinstance(rounded, dict)
    return rounded


def test_satellite_chain_reference_fixture_locked(tmp_path: Path) -> None:
    if not REFERENCE_FIXTURE.exists():
        pytest.skip("Satellite-chain fixture missing. Run scripts/generate_satellite_chain_reference.py")

    config = load_config(REFERENCE_CONFIG)
    result = run_satellite_chain(config, output_dir=tmp_path / "satellite_chain_reference")
    certificate = result.get("certificate") if isinstance(result, dict) else None
    assert isinstance(certificate, dict)

    actual = _canonicalize_certificate(certificate, repo_root=REPO_ROOT)
    expected = json.loads(REFERENCE_FIXTURE.read_text(encoding="utf-8"))
    assert actual == expected
