"""Check open benchmark bundles for drift."""

from __future__ import annotations

import argparse
from pathlib import Path

from photonstrust.benchmarks.open_benchmarks import check_open_benchmarks


def main() -> int:
    parser = argparse.ArgumentParser(description="Check PhotonTrust open benchmarks for drift.")
    parser.add_argument(
        "--open-root",
        type=Path,
        default=None,
        help="Path to open benchmark registry root (defaults to datasets/benchmarks/open).",
    )
    args = parser.parse_args()

    ok, failures = check_open_benchmarks(args.open_root)
    if ok:
        print("Open benchmarks: PASS")
        return 0
    print("Open benchmarks: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

