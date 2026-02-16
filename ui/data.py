"""Data helpers for Streamlit UI."""

from __future__ import annotations

import json
from pathlib import Path


def list_runs(results_root: Path) -> list[Path]:
    if not results_root.exists():
        return []
    registry = results_root / "run_registry.json"
    if registry.exists():
        try:
            payload = json.loads(registry.read_text(encoding="utf-8"))
            return [Path(entry["card_path"]) for entry in payload if entry.get("card_path")]
        except json.JSONDecodeError:
            pass
    return sorted(results_root.glob("**/reliability_card.json"))


def load_card(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def list_dataset_entries(results_root: Path) -> list[Path]:
    if not results_root.exists():
        return []
    return sorted(results_root.glob("**/dataset_entry.json"))


def load_dataset_entry(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
