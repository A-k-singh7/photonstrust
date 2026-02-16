"""Generate an external reproducibility pack for a PhotonTrust config."""

from __future__ import annotations

import argparse
from pathlib import Path

from photonstrust.benchmarks.repro_pack import generate_repro_pack


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PhotonTrust reproducibility pack (v0).")
    parser.add_argument("config", type=Path, help="Scenario config YAML file")
    parser.add_argument("output", type=Path, help="Output directory for the repro pack")
    parser.add_argument("--pack-id", type=str, default=None, help="Override pack ID (defaults from config)")
    args = parser.parse_args()

    generate_repro_pack(args.config, args.output, pack_id=args.pack_id)
    print(f"Repro pack written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

