"""Evidence bundle signing and verification.

PhotonTrust evidence bundles are zip exports produced by the API server.
They contain:
- run manifests + declared artifacts
- `bundle_manifest.json` with per-file sha256 hashes

Phase 40 adds signing/verification of the bundle manifest to make exports
tamper-evident outside the repo.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


class BundleVerificationError(ValueError):
    """Raised when a bundle fails integrity or signature verification."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = str(code)
        self.details = dict(details or {})


_SIG_REL_DEFAULT = "signatures/bundle_manifest.ed25519.sig.json"


@dataclass(frozen=True)
class BundleVerifyResult:
    ok: bool
    bundle_root: str
    manifest_sha256: str
    verified_files: int
    missing_files: int
    mismatched_files: int
    signature_verified: bool
    errors: list[dict[str, Any]]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json_bytes(obj: Any) -> bytes:
    # Deterministic JSON encoding used for signature input.
    # Keep this stable across releases.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _iter_top_level_roots(names: Iterable[str]) -> set[str]:
    roots: set[str] = set()
    for n in names:
        n = str(n).replace("\\", "/")
        if not n or "/" not in n:
            continue
        roots.add(n.split("/", 1)[0])
    return roots


def _detect_bundle_root(zf: zipfile.ZipFile) -> str:
    names = zf.namelist()
    # Prefer roots that contain bundle_manifest.json.
    candidates = []
    for n in names:
        n2 = str(n).replace("\\", "/")
        if n2.endswith("/bundle_manifest.json"):
            candidates.append(n2.split("/", 1)[0])
    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise BundleVerificationError(
            "multiple_bundle_roots",
            "Multiple bundle roots detected (multiple bundle_manifest.json entries).",
            details={"bundle_roots": candidates},
        )

    # Fallback: single top-level root.
    roots = sorted(_iter_top_level_roots(names))
    if len(roots) == 1:
        return roots[0]
    raise BundleVerificationError(
        "bundle_root_not_found",
        "Could not detect evidence bundle root directory inside zip.",
        details={"top_level_roots": roots},
    )


def _read_json_from_zip(zf: zipfile.ZipFile, path: str) -> tuple[dict[str, Any], bytes]:
    raw = zf.read(path)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise BundleVerificationError("invalid_json", f"Failed to parse JSON at {path}.") from exc
    if not isinstance(obj, dict):
        raise BundleVerificationError("invalid_json", f"Expected JSON object at {path}.")
    return obj, raw


def _zip_entry_sha256(zf: zipfile.ZipFile, name: str) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with zf.open(name, "r") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            size += len(chunk)
    return h.hexdigest(), int(size)


def verify_bundle_zip(
    zip_path: Path,
    *,
    public_key_pem_path: Path | None = None,
    require_signature: bool = False,
    signature_relpath: str = _SIG_REL_DEFAULT,
) -> BundleVerifyResult:
    """Verify an evidence bundle zip.

    Verification checks:
    - bundle_manifest.json parses as JSON object
    - for each manifest file entry, sha256 matches the zip entry bytes
    - optional: Ed25519 signature verifies over canonicalized manifest dict
    """

    zip_path = Path(zip_path)
    errors: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        bundle_root = _detect_bundle_root(zf)
        manifest_zip_path = f"{bundle_root}/bundle_manifest.json"
        if manifest_zip_path not in set(zf.namelist()):
            raise BundleVerificationError(
                "manifest_missing",
                "bundle_manifest.json not found in bundle.",
                details={"expected": manifest_zip_path},
            )
        manifest, manifest_raw = _read_json_from_zip(zf, manifest_zip_path)
        manifest_sha256 = _sha256_bytes(manifest_raw)

        files = manifest.get("files")
        if not isinstance(files, list) or not files:
            raise BundleVerificationError("manifest_files_missing", "Manifest 'files' list is missing or empty.")

        verified_files = 0
        missing_files = 0
        mismatched_files = 0

        seen_paths: set[str] = set()
        for rec in files:
            if not isinstance(rec, dict):
                errors.append({"code": "invalid_record", "message": "file record is not an object"})
                mismatched_files += 1
                continue
            rel = str(rec.get("path", "")).replace("\\", "/")
            if not rel:
                errors.append({"code": "invalid_record", "message": "file record missing path"})
                mismatched_files += 1
                continue
            if rel in seen_paths:
                errors.append({"code": "duplicate_path", "path": rel})
                mismatched_files += 1
                continue
            seen_paths.add(rel)

            expected_sha = str(rec.get("sha256", "")).strip().lower()
            expected_bytes = rec.get("bytes")
            zip_name = f"{bundle_root}/{rel}"
            if zip_name not in set(zf.namelist()):
                errors.append({"code": "missing_file", "path": rel})
                missing_files += 1
                continue
            actual_sha, actual_size = _zip_entry_sha256(zf, zip_name)
            if expected_sha and actual_sha != expected_sha:
                errors.append(
                    {
                        "code": "sha256_mismatch",
                        "path": rel,
                        "expected": expected_sha,
                        "actual": actual_sha,
                    }
                )
                mismatched_files += 1
                continue
            if isinstance(expected_bytes, int) and int(expected_bytes) != int(actual_size):
                errors.append(
                    {
                        "code": "size_mismatch",
                        "path": rel,
                        "expected": int(expected_bytes),
                        "actual": int(actual_size),
                    }
                )
                mismatched_files += 1
                continue
            verified_files += 1

        # Optional signature verification.
        signature_verified = False
        signature_relpath_posix = str(signature_relpath).replace("\\", "/")
        sig_zip_path = f"{bundle_root}/{signature_relpath_posix}"
        sig_present = sig_zip_path in set(zf.namelist())
        if require_signature and not sig_present:
            errors.append({"code": "signature_missing", "path": str(signature_relpath)})
        if sig_present and public_key_pem_path is not None:
            sig_obj, _ = _read_json_from_zip(zf, sig_zip_path)
            sig_b64 = str(sig_obj.get("signature_b64", ""))
            alg = str(sig_obj.get("signature_alg", "")).strip().lower()
            expected_manifest_canon_sha = str(sig_obj.get("manifest_canonical_sha256", "")).strip().lower()
            if alg != "ed25519":
                errors.append({"code": "unsupported_signature_alg", "alg": alg})
            else:
                canon = _canonical_json_bytes(manifest)
                canon_sha = hashlib.sha256(canon).hexdigest()
                if expected_manifest_canon_sha and expected_manifest_canon_sha != canon_sha:
                    errors.append(
                        {
                            "code": "manifest_canonical_sha256_mismatch",
                            "expected": expected_manifest_canon_sha,
                            "actual": canon_sha,
                        }
                    )
                else:
                    from photonstrust.evidence.signing import verify_bytes_ed25519

                    try:
                        verify_bytes_ed25519(
                            public_key_pem_path=Path(public_key_pem_path),
                            message=canon,
                            signature_b64=sig_b64,
                        )
                        signature_verified = True
                    except Exception as exc:
                        errors.append({"code": "signature_invalid", "message": str(exc)})

        if sig_present and public_key_pem_path is None and require_signature:
            errors.append(
                {
                    "code": "public_key_required",
                    "message": "public_key_pem_path is required to verify signature",
                }
            )

        ok = (missing_files == 0) and (mismatched_files == 0)
        if require_signature:
            ok = ok and bool(signature_verified)

        return BundleVerifyResult(
            ok=bool(ok),
            bundle_root=str(bundle_root),
            manifest_sha256=str(manifest_sha256),
            verified_files=int(verified_files),
            missing_files=int(missing_files),
            mismatched_files=int(mismatched_files),
            signature_verified=bool(signature_verified),
            errors=errors,
        )


def sign_bundle_zip(
    zip_path: Path,
    *,
    private_key_pem_path: Path,
    output_zip_path: Path | None = None,
    signature_relpath: str = _SIG_REL_DEFAULT,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Create a signed copy of an evidence bundle zip.

    Produces a new zip that includes a detached signature JSON file at
    `<bundle_root>/<signature_relpath>`.

    The signature covers the canonicalized manifest dict bytes (sorted keys,
    compact JSON) so formatting changes to bundle_manifest.json do not affect
    signature validity.
    """

    zip_path = Path(zip_path)
    if output_zip_path is None:
        output_zip_path = zip_path.with_suffix(zip_path.suffix + ".signed.zip")
    output_zip_path = Path(output_zip_path)

    with zipfile.ZipFile(zip_path, "r") as zf:
        bundle_root = _detect_bundle_root(zf)
        manifest_zip_path = f"{bundle_root}/bundle_manifest.json"
        manifest, _ = _read_json_from_zip(zf, manifest_zip_path)
        canon = _canonical_json_bytes(manifest)
        canon_sha = hashlib.sha256(canon).hexdigest()

    from photonstrust.evidence.signing import sign_bytes_ed25519

    signature_b64 = sign_bytes_ed25519(private_key_pem_path=Path(private_key_pem_path), message=canon)
    created_at = created_at or datetime.now(timezone.utc).isoformat()
    sig_obj = {
        "schema_version": "0.1",
        "kind": "photonstrust.evidence_bundle_signature",
        "created_at": created_at,
        "bundle_root": str(bundle_root),
        "manifest_path": "bundle_manifest.json",
        "signature_alg": "ed25519",
        "manifest_canonical_sha256": canon_sha,
        "signature_b64": str(signature_b64),
    }
    sig_bytes = json.dumps(sig_obj, indent=2).encode("utf-8")

    # Write new zip with copied members plus signature member.
    with zipfile.ZipFile(zip_path, "r") as src, zipfile.ZipFile(output_zip_path, "w") as dst:
        for info in src.infolist():
            # Preserve deterministic timestamps if present.
            data = src.read(info.filename)
            out_info = zipfile.ZipInfo(info.filename)
            out_info.date_time = info.date_time
            out_info.compress_type = info.compress_type
            dst.writestr(out_info, data)

        signature_relpath_posix = str(signature_relpath).replace("\\", "/")
        sig_arc = f"{bundle_root}/{signature_relpath_posix}"
        sig_info = zipfile.ZipInfo(sig_arc)
        # Match evidence bundle fixed dt if possible.
        sig_info.date_time = (1980, 1, 1, 0, 0, 0)
        sig_info.compress_type = zipfile.ZIP_DEFLATED
        dst.writestr(sig_info, sig_bytes)

    return {
        "ok": True,
        "input_zip": str(zip_path),
        "output_zip": str(output_zip_path),
        "bundle_root": str(bundle_root),
        "manifest_canonical_sha256": canon_sha,
        "signature_relpath": str(signature_relpath),
    }
