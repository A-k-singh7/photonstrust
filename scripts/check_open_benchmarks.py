"""Check open benchmark bundles for drift."""

from __future__ import annotations

import argparse
from pathlib import Path

from photonstrust.benchmarks._paths import open_benchmarks_dir
from photonstrust.benchmarks.open_index import check_open_index_consistency
from photonstrust.benchmarks.open_benchmarks import check_open_benchmarks


def run_checks(open_root: Path | None, *, check_index: bool = True) -> tuple[bool, list[str]]:
    resolved_open_root = Path(open_root) if open_root is not None else open_benchmarks_dir()

    ok, failures = check_open_benchmarks(resolved_open_root)
    combined_failures = list(failures)

    if check_index:
        index_ok, index_failures = check_open_index_consistency(resolved_open_root)
        if not index_ok:
            combined_failures.extend([f"index: {line}" for line in index_failures])

    return len(combined_failures) == 0, combined_failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PhotonTrust open benchmarks for drift.")
    parser.add_argument(
        "--open-root",
        type=Path,
        default=None,
        help="Path to open benchmark registry root (defaults to datasets/benchmarks/open).",
    )
    parser.add_argument(
        "--check-index",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Validate datasets/benchmarks/open/index.json consistency (default: true).",
    )
    args = parser.parse_args()

    ok, failures = run_checks(args.open_root, check_index=bool(args.check_index))
    if ok:
        print("Open benchmarks: PASS")
        return 0
    print("Open benchmarks: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
