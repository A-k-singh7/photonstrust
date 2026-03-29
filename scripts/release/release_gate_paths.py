"""Shared release gate artifact paths and compatibility helpers."""

from __future__ import annotations

from pathlib import Path


TRACKED_MILESTONES_DIR = Path("reports/specs/milestones")
FALLBACK_MILESTONES_DIR = Path("research docs/milestones")

PACKET_BASENAME = "release_gate_packet_2026-02-16.json"
SIGNATURE_BASENAME = "release_gate_packet_2026-02-16.ed25519.sig.json"
PUBLIC_KEY_BASENAME = "release_gate_packet_2026-02-16.public.pem"
PRIVATE_KEY_BASENAME = "release_gate_packet_2026-02-16.private.pem"
APPROVALS_BASENAME = "release_approvals_2026-02-16.json"

DEFAULT_PACKET_PATH = TRACKED_MILESTONES_DIR / PACKET_BASENAME
DEFAULT_SIGNATURE_PATH = TRACKED_MILESTONES_DIR / SIGNATURE_BASENAME
DEFAULT_PUBLIC_KEY_PATH = TRACKED_MILESTONES_DIR / PUBLIC_KEY_BASENAME
DEFAULT_PRIVATE_KEY_PATH = Path("results/release_gate_keys") / PRIVATE_KEY_BASENAME
DEFAULT_APPROVALS_PATH = TRACKED_MILESTONES_DIR / APPROVALS_BASENAME


def normalize_relpath(path: Path | str) -> str:
    """Return a repo-style forward-slash relative path string."""
    return str(Path(path)).replace("\\", "/")


def resolve_repo_path(repo_root: Path, path: Path | str) -> Path:
    """Resolve a repo-relative path with compatibility fallback for moved milestones."""
    raw = Path(path)
    if raw.is_absolute():
        return raw

    normalized = normalize_relpath(raw)
    candidates = [repo_root / raw]

    tracked_prefix = f"{TRACKED_MILESTONES_DIR.as_posix()}/"
    fallback_prefix = f"{FALLBACK_MILESTONES_DIR.as_posix()}/"
    if normalized.startswith(tracked_prefix):
        candidates.append(repo_root / FALLBACK_MILESTONES_DIR / raw.name)
    elif normalized.startswith(fallback_prefix):
        candidates.append(repo_root / TRACKED_MILESTONES_DIR / raw.name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]
