"""Ingest a measurement bundle into the local open registry."""

from __future__ import annotations

import argparse
from pathlib import Path

from photonstrust.measurements import ingest_measurement_bundle_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PhotonTrust measurement bundle JSON")
    parser.add_argument("bundle", type=Path, help="Path to measurement_bundle.json")
    parser.add_argument("--open-root", type=Path, default=None, help="Override open measurements registry root")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing dataset_id entry")
    args = parser.parse_args()

    out = ingest_measurement_bundle_file(args.bundle, open_root=args.open_root, overwrite=bool(args.overwrite))
    print(str(out))


if __name__ == "__main__":
    main()
