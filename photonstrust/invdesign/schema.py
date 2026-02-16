"""Schema path helpers for inverse-design artifact contracts."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    # .../photonstrust/invdesign/schema.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def invdesign_report_schema_path() -> Path:
    return (_repo_root() / "schemas" / "photonstrust.pic_invdesign_report.v0.schema.json").resolve()

