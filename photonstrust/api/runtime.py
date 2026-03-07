"""Runtime metadata helpers for API responses."""

from __future__ import annotations

from datetime import datetime, timezone
import platform
import sys
from typing import Any

from photonstrust.api.application import photonstrust_version


def api_version() -> str:
    return photonstrust_version() or "0.0"


def generated_at_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def runtime_provenance() -> dict[str, Any]:
    return {
        "photonstrust_version": api_version(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
    }
