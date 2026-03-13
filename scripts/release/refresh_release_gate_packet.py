"""Refresh release gate packet and signature artifacts, then verify both."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, repo_root: Path) -> int:
    print("+", " ".join(cmd), flush=True)
    completed = subprocess.run(cmd, cwd=repo_root)
    return int(completed.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rebuild/sign/verify release gate packet artifacts.")
    parser.add_argument(
        "--packet",
        type=Path,
        default=Path("reports/specs/milestones/release_gate_packet_2026-02-16.json"),
        help="Path to release gate packet JSON.",
    )
    parser.add_argument(
        "--signature",
        type=Path,
        default=Path("reports/specs/milestones/release_gate_packet_2026-02-16.ed25519.sig.json"),
        help="Path to release gate packet signature JSON.",
    )
    parser.add_argument(
        "--private-key",
        type=Path,
        default=Path("results/release_gate_keys/release_gate_packet_2026-02-16.private.pem"),
        help="Path to Ed25519 private key PEM.",
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default=Path("results/release_gate_keys/release_gate_packet_2026-02-16.public.pem"),
        help="Path to Ed25519 public key PEM.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    steps = [
        [
            sys.executable,
            "scripts/release/build_release_gate_packet.py",
            "--output",
            str(args.packet),
        ],
        [
            sys.executable,
            "scripts/release/sign_release_gate_packet.py",
            "--packet",
            str(args.packet),
            "--signature-output",
            str(args.signature),
            "--private-key",
            str(args.private_key),
            "--public-key",
            str(args.public_key),
        ],
        [
            sys.executable,
            "scripts/release/verify_release_gate_packet.py",
            "--packet",
            str(args.packet),
        ],
        [
            sys.executable,
            "scripts/release/verify_release_gate_packet_signature.py",
            "--packet",
            str(args.packet),
            "--signature",
            str(args.signature),
            "--public-key",
            str(args.public_key),
        ],
    ]

    for cmd in steps:
        rc = _run(cmd, repo_root=repo_root)
        if rc != 0:
            print("Release gate packet refresh: FAIL")
            return rc

    print("Release gate packet refresh: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
