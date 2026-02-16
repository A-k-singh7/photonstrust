"""Generate golden report snapshot hash."""

from __future__ import annotations

import json
from pathlib import Path

from photonstrust.config import build_scenarios, load_config
from photonstrust.sweep import run_scenarios
from photonstrust.utils import hash_dict


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_root = root / "results" / "golden"
    config = load_config(root / "configs" / "demo1_default.yml")
    scenarios = build_scenarios(config)
    result = run_scenarios(scenarios, output_root)

    report_hashes = {}
    for card in result["cards"]:
        report_path = Path(card["artifacts"]["report_html_path"])
        if report_path.exists():
            report_hashes[card["band"]] = _hash_text(report_path.read_text(encoding="utf-8"))

    output_path = root / "tests" / "fixtures" / "report_hashes.json"
    output_path.write_text(json.dumps(report_hashes, indent=2), encoding="utf-8")


def _hash_text(text: str) -> str:
    return hash_dict({"text": text})


if __name__ == "__main__":
    main()
