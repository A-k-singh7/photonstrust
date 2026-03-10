"""Remove local generated artifacts that should not live in the repo."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_DIR_PATTERNS = (
    "**/__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "htmlcov",
    "photonstrust.egg-info",
    ".benchmarks",
    "web/dist",
    "web/playwright-report",
    "web/test-results",
)

DEFAULT_FILE_PATTERNS = (
    ".coverage",
    "coverage.xml",
    "web_dev.log",
)

EXCLUDED_TOP_LEVEL_DIRS = {".venv", ".venv.production", "open_source", "local"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _matches(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    found: dict[str, Path] = {}
    for pattern in patterns:
        for path in root.glob(pattern):
            rel_parts = path.resolve().relative_to(root.resolve()).parts
            if rel_parts and rel_parts[0] in EXCLUDED_TOP_LEVEL_DIRS:
                continue
            found[str(path.resolve())] = path
    return sorted(found.values(), key=lambda item: str(item).lower())


def _remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
        return
    path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove local generated workspace artifacts")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be removed")
    parser.add_argument(
        "--include-node-modules",
        action="store_true",
        help="Also remove web/node_modules",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = _repo_root()
    dir_patterns: list[str] = list(DEFAULT_DIR_PATTERNS)
    if bool(args.include_node_modules):
        dir_patterns.append("web/node_modules")

    targets = _matches(repo_root, tuple(dir_patterns)) + _matches(repo_root, DEFAULT_FILE_PATTERNS)
    if not targets:
        print("No generated local artifacts found.")
        return 0

    print("PhotonTrust local cleanup targets:")
    for path in targets:
        rel = path.resolve().relative_to(repo_root.resolve())
        print(f"- {rel}")

    if bool(args.dry_run):
        print("Dry run only; nothing removed.")
        return 0

    for path in targets:
        _remove_path(path)

    print(f"Removed {len(targets)} path(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
