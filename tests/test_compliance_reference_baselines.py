from __future__ import annotations

import json
from pathlib import Path

import pytest

from photonstrust.compliance.reference import build_reference_fixture


def test_compliance_reference_baselines_are_locked() -> None:
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "tests" / "fixtures" / "compliance_reference_baselines.json"
    if not fixture_path.exists():
        pytest.skip("Compliance baseline fixture not present. Run scripts/generate_compliance_reference_baselines.py")

    expected = json.loads(fixture_path.read_text(encoding="utf-8"))
    actual = build_reference_fixture(root)
    assert actual == expected

