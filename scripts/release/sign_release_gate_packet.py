"""Sign release gate packet with Ed25519 and emit signature artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from photonstrust.evidence.signing import SigningUnavailable, sign_bytes_ed25519, write_keypair
from release_gate_paths import (
    DEFAULT_PACKET_PATH,
    DEFAULT_PRIVATE_KEY_PATH,
    DEFAULT_PUBLIC_KEY_PATH,
    DEFAULT_SIGNATURE_PATH,
    normalize_relpath,
    resolve_repo_path,
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sign_release_gate_packet(
    *,
    repo_root: Path,
    packet_path: Path,
    signature_path: Path,
    private_key_path: Path,
    public_key_path: Path,
    generate_keypair: bool,
    key_id: str,
) -> tuple[bool, str]:
    resolved_packet = resolve_repo_path(repo_root, packet_path)
    resolved_signature = signature_path if signature_path.is_absolute() else (repo_root / signature_path)
    resolved_private_key = private_key_path if private_key_path.is_absolute() else (repo_root / private_key_path)
    resolved_public_key = public_key_path if public_key_path.is_absolute() else (repo_root / public_key_path)

    if not resolved_packet.exists():
        return False, f"missing packet: {resolved_packet}"

    if generate_keypair and (not resolved_private_key.exists() or not resolved_public_key.exists()):
        resolved_private_key.parent.mkdir(parents=True, exist_ok=True)
        resolved_public_key.parent.mkdir(parents=True, exist_ok=True)
        write_keypair(private_key_path=resolved_private_key, public_key_path=resolved_public_key)

    if not resolved_private_key.exists() or not resolved_public_key.exists():
        return False, "missing signing key(s); provide existing keys or pass --generate-keypair"

    packet_bytes = resolved_packet.read_bytes()
    packet_sha256 = _sha256_bytes(packet_bytes)
    signature_b64 = sign_bytes_ed25519(private_key_pem_path=resolved_private_key, message=packet_bytes)

    payload = {
        "schema_version": "0.1",
        "kind": "photonstrust.release_gate_packet_signature",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "key_id": key_id,
        "packet_path": normalize_relpath(packet_path),
        "packet_sha256": packet_sha256,
        "signature_algorithm": "ed25519",
        "signature_b64": signature_b64,
        "public_key_path": normalize_relpath(public_key_path),
    }

    resolved_signature.parent.mkdir(parents=True, exist_ok=True)
    with resolved_signature.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2) + "\n")
    return True, str(resolved_signature)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign release gate packet with Ed25519.")
    parser.add_argument(
        "--packet",
        type=Path,
        default=DEFAULT_PACKET_PATH,
        help="Path to release gate packet JSON.",
    )
    parser.add_argument(
        "--signature-output",
        type=Path,
        default=DEFAULT_SIGNATURE_PATH,
        help="Path to write signature JSON artifact.",
    )
    parser.add_argument(
        "--private-key",
        type=Path,
        default=DEFAULT_PRIVATE_KEY_PATH,
        help="Path to Ed25519 private key PEM.",
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default=DEFAULT_PUBLIC_KEY_PATH,
        help="Path to Ed25519 public key PEM.",
    )
    parser.add_argument(
        "--generate-keypair",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate keypair if key files are missing (default: true).",
    )
    parser.add_argument(
        "--key-id",
        default="release_gate_packet_2026-02-16",
        help="Logical key id embedded in signature artifact.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    try:
        ok, detail = sign_release_gate_packet(
            repo_root=repo_root,
            packet_path=args.packet,
            signature_path=args.signature_output,
            private_key_path=args.private_key,
            public_key_path=args.public_key,
            generate_keypair=bool(args.generate_keypair),
            key_id=str(args.key_id),
        )
    except SigningUnavailable as exc:
        print("Release gate packet sign: FAIL")
        print(f" - {exc}")
        return 2

    if ok:
        print("Release gate packet sign: PASS")
        print(detail)
        return 0

    print("Release gate packet sign: FAIL")
    print(f" - {detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
