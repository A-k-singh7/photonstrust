"""Local redaction/secret scans for measurement bundles (v0.1).

These checks are deliberately conservative: they aim to prevent accidental
publication of common secrets and sensitive key material.
"""

from __future__ import annotations

import re
from pathlib import Path


DEFAULT_BLOCKED_BASENAMES = {".env", "id_rsa", "id_ed25519"}
DEFAULT_BLOCKED_EXTS = {".pem", ".p12", ".pfx", ".key"}


_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key_block", re.compile(r"BEGIN\\s+PRIVATE\\s+KEY", re.IGNORECASE)),
    ("aws_access_key_id", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("github_token", re.compile(r"ghp_[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    ("stripe_live_key", re.compile(r"sk_live_[A-Za-z0-9]{10,}")),
]


def scan_measurement_bundle(
    bundle_root: str | Path,
    *,
    file_paths: list[str],
    max_text_bytes: int = 200_000,
) -> list[str]:
    """Return a list of issues discovered in the bundle."""

    root = Path(bundle_root).resolve()
    issues: list[str] = []

    for rel in file_paths:
        rel_s = str(rel).replace("\\", "/")
        if rel_s.startswith("/") or rel_s.startswith("..") or "/.." in rel_s:
            issues.append(f"illegal_path: {rel}")
            continue
        src = (root / rel_s).resolve()
        if root not in src.parents and src != root:
            issues.append(f"path_traversal: {rel}")
            continue
        if not src.exists() or not src.is_file():
            issues.append(f"missing_file: {rel}")
            continue

        base = src.name.lower()
        ext = src.suffix.lower()
        if base in DEFAULT_BLOCKED_BASENAMES or ext in DEFAULT_BLOCKED_EXTS:
            issues.append(f"blocked_filename: {rel}")
            continue

        if _is_text_like(src):
            try:
                text = src.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                issues.append(f"read_error: {rel}: {exc}")
                continue
            if len(text.encode("utf-8", errors="ignore")) > max_text_bytes:
                text = text[: max_text_bytes]
            for name, pat in _PATTERNS:
                if pat.search(text):
                    issues.append(f"secret_pattern:{name}:{rel}")

    return issues


def _is_text_like(path: Path) -> bool:
    ext = path.suffix.lower()
    if ext in {".txt", ".csv", ".json", ".yml", ".yaml", ".md", ".py"}:
        return True
    # Fallback to content_type heuristics (not available here); keep strict.
    return False

