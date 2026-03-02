"""Regenerate deterministic M2 compliance reference baselines."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.compliance.reference import build_reference_fixture


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_path = root / "tests" / "fixtures" / "compliance_reference_baselines.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = build_reference_fixture(root)
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(str(output_path.relative_to(root)))


if __name__ == "__main__":
    main()

