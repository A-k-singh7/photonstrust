"""Path helpers for graph tooling."""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    # .../photonstrust/photonstrust/graph/_paths.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def schemas_dir() -> Path:
    return repo_root() / "schemas"

