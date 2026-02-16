"""Minimal Ed25519 signing/verification helpers.

This module is intentionally small and only implements what PhotonTrust needs
for Phase 40 evidence bundle signing.

Optional dependency:
- cryptography
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class SigningUnavailable(RuntimeError):
    pass


def _require_cryptography() -> Any:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except Exception as exc:  # pragma: no cover
        raise SigningUnavailable(
            "Ed25519 signing/verification requires the optional dependency 'cryptography'. "
            "Install with: pip install -e .[signing]"
        ) from exc
    return serialization, Ed25519PrivateKey, Ed25519PublicKey


@dataclass(frozen=True)
class Ed25519KeyPair:
    private_pem: bytes
    public_pem: bytes


def generate_ed25519_keypair() -> Ed25519KeyPair:
    serialization, Ed25519PrivateKey, _ = _require_cryptography()
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    private_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return Ed25519KeyPair(private_pem=private_pem, public_pem=public_pem)


def write_keypair(*, private_key_path: Path, public_key_path: Path) -> None:
    kp = generate_ed25519_keypair()
    Path(private_key_path).write_bytes(kp.private_pem)
    Path(public_key_path).write_bytes(kp.public_pem)


def load_ed25519_private_key_pem(path: Path) -> Any:
    serialization, _, _ = _require_cryptography()
    data = Path(path).read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def load_ed25519_public_key_pem(path: Path) -> Any:
    serialization, _, _ = _require_cryptography()
    data = Path(path).read_bytes()
    return serialization.load_pem_public_key(data)


def sign_bytes_ed25519(*, private_key_pem_path: Path, message: bytes) -> str:
    priv = load_ed25519_private_key_pem(Path(private_key_pem_path))
    sig = priv.sign(bytes(message))
    return base64.b64encode(sig).decode("ascii")


def verify_bytes_ed25519(*, public_key_pem_path: Path, message: bytes, signature_b64: str) -> None:
    pub = load_ed25519_public_key_pem(Path(public_key_pem_path))
    sig = base64.b64decode(str(signature_b64).encode("ascii"))
    pub.verify(sig, bytes(message))
