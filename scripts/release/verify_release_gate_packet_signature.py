"""Verify Ed25519 signature artifact for release gate packet."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from photonstrust.evidence.signing import SigningUnavailable, verify_bytes_ed25519
try:
    from scripts.release.release_gate_paths import DEFAULT_PACKET_PATH, DEFAULT_SIGNATURE_PATH, resolve_repo_path
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    from release_gate_paths import DEFAULT_PACKET_PATH, DEFAULT_SIGNATURE_PATH, resolve_repo_path


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_release_gate_packet_signature(
    *,
    repo_root: Path,
    packet_path: Path,
    signature_path: Path,
    public_key_path: Path | None,
) -> tuple[bool, list[str]]:
    failures: list[str] = []

    resolved_packet = resolve_repo_path(repo_root, packet_path)
    resolved_signature = resolve_repo_path(repo_root, signature_path)

    if not resolved_packet.exists():
        failures.append(f"missing packet: {resolved_packet}")
        return False, failures
    if not resolved_signature.exists():
        failures.append(f"missing signature artifact: {resolved_signature}")
        return False, failures

    try:
        signature_payload = json.loads(resolved_signature.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, [f"failed to parse signature artifact: {exc}"]

    if not isinstance(signature_payload, dict):
        return False, ["signature artifact must be a JSON object"]
    if str(signature_payload.get("kind") or "") != "photonstrust.release_gate_packet_signature":
        failures.append(f"unexpected signature kind: {signature_payload.get('kind')}")

    packet_bytes = resolved_packet.read_bytes()
    packet_sha256 = _sha256_bytes(packet_bytes)
    expected_sha = str(signature_payload.get("packet_sha256") or "")
    if expected_sha != packet_sha256:
        failures.append("packet_sha256 mismatch")

    signature_b64 = str(signature_payload.get("signature_b64") or "")
    if not signature_b64:
        failures.append("signature_b64 missing from signature artifact")

    if public_key_path is not None:
        resolved_public_key = resolve_repo_path(repo_root, public_key_path)
    else:
        key_field = signature_payload.get("public_key_path")
        resolved_public_key = resolve_repo_path(repo_root, Path(str(key_field)))
    if not resolved_public_key.exists():
        failures.append(f"missing public key: {resolved_public_key}")

    if failures:
        return False, failures

    try:
        verify_bytes_ed25519(
            public_key_pem_path=resolved_public_key,
            message=packet_bytes,
            signature_b64=signature_b64,
        )
    except Exception as exc:
        return False, [f"signature verification failed: {exc}"]

    return True, []


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify release gate packet signature artifact.")
    parser.add_argument(
        "--packet",
        type=Path,
        default=DEFAULT_PACKET_PATH,
        help="Path to release gate packet JSON.",
    )
    parser.add_argument(
        "--signature",
        type=Path,
        default=DEFAULT_SIGNATURE_PATH,
        help="Path to signature artifact JSON.",
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default=None,
        help="Optional public key path override.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    try:
        ok, failures = verify_release_gate_packet_signature(
            repo_root=repo_root,
            packet_path=args.packet,
            signature_path=args.signature,
            public_key_path=args.public_key,
        )
    except SigningUnavailable as exc:
        print("Release gate packet signature verify: FAIL")
        print(f" - {exc}")
        return 2

    if ok:
        print("Release gate packet signature verify: PASS")
        print(str(args.signature if args.signature.is_absolute() else (repo_root / args.signature)))
        return 0

    print("Release gate packet signature verify: FAIL")
    for line in failures:
        print(f" - {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
