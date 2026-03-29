"""Path helpers for locating repository-level resources.

These tools are intentionally kept inside the package so they work from
editable installs and source checkouts. The benchmark tooling is a dev-facing
surface and may rely on repo-local schema files.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    # .../photonstrust/photonstrust/benchmarks/_paths.py -> parents[2] is repo root.
    return Path(__file__).resolve().parents[2]


def schemas_dir() -> Path:
    return repo_root() / "schemas"


def open_benchmarks_dir() -> Path:
    return repo_root() / "datasets" / "benchmarks" / "open"
