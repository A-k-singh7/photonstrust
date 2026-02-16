from pathlib import Path

import json
import pytest

from photonstrust.utils import hash_dict


def test_golden_report_hashes():
    root = Path(__file__).resolve().parents[1]
    fixture_path = root / "tests" / "fixtures" / "report_hashes.json"
    if not fixture_path.exists():
        pytest.skip("Golden report hashes not present. Run scripts/generate_golden_report.py")

    hashes = json.loads(fixture_path.read_text(encoding="utf-8"))
    report_paths = list((root / "results" / "golden").glob("**/report.html"))
    if not report_paths:
        pytest.skip("Golden reports not generated.")

    for report_path in report_paths:
        band = report_path.parent.name
        current_hash = hash_dict({"text": report_path.read_text(encoding="utf-8")})
        assert current_hash == hashes.get(band)
