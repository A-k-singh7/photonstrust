"""Publish a local artifact pack for a measurement bundle (opt-in).

This creates a shareable folder (and zip) after running redaction scans.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from photonstrust.measurements import publish_artifact_pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish PhotonTrust artifact pack for measurement bundle JSON")
    parser.add_argument("bundle", type=Path, help="Path to measurement_bundle.json")
    parser.add_argument("output", type=Path, help="Output directory to place the pack")
    parser.add_argument("--pack-id", default=None, help="Override generated pack id")
    parser.add_argument("--allow-risk", action="store_true", help="Allow packaging even if scans detect issues")
    parser.add_argument("--no-zip", action="store_true", help="Do not create a zip archive")
    args = parser.parse_args()

    pack_root = publish_artifact_pack(
        args.bundle,
        args.output,
        pack_id=args.pack_id,
        allow_risk=bool(args.allow_risk),
        zip_pack=not bool(args.no_zip),
    )
    print(str(pack_root))


if __name__ == "__main__":
    main()
