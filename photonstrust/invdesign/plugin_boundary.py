"""Inverse-design external solver plugin boundary (metadata-only).

This module defines a license-safe boundary for optional external/GPL solver
integration. Open-core execution remains deterministic and self-contained while
recording policy-safe metadata about requested plugin usage.
"""

from __future__ import annotations

from typing import Any


_CORE_BACKEND_ALIASES = {"", "auto", "core", "builtin", "internal", "default"}
_ALLOWED_LICENSE_CLASSES = {"unknown", "permissive", "copyleft", "commercial", "proprietary"}


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_license_class(value: Any) -> str:
    cls = _clean_text(value).lower()
    if cls in _ALLOWED_LICENSE_CLASSES:
        return cls
    return "unknown"


def resolve_invdesign_solver_metadata(
    *,
    solver_backend: str | None,
    solver_plugin: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve policy-safe solver execution metadata.

    This is a boundary contract only. It does not execute external tools.
    """

    requested = _clean_text(solver_backend).lower() or "core"
    plugin = solver_plugin if isinstance(solver_plugin, dict) else {}

    plugin_id = _clean_text(plugin.get("plugin_id") or plugin.get("id")) or None
    plugin_version = _clean_text(plugin.get("plugin_version") or plugin.get("version")) or None
    license_class = _normalize_license_class(plugin.get("license_class"))

    if requested in _CORE_BACKEND_ALIASES:
        return {
            "backend_requested": requested or "core",
            "backend_used": "core",
            "runner_mode": "core",
            "plugin_id": plugin_id,
            "plugin_version": plugin_version,
            "license_class": license_class,
            "applicability": {"status": "core"},
            "fallback_reason": None,
            "policy": {
                "metadata_only": True,
                "allows_external_execution": False,
            },
        }

    plugin_enabled = bool(plugin.get("enabled", True))
    plugin_available = bool(plugin.get("available", False))
    fallback_reason = None
    if not plugin_enabled:
        fallback_reason = "plugin_disabled"
    elif not plugin_available:
        fallback_reason = "plugin_unavailable"

    if fallback_reason is None:
        backend_used = requested
        runner_mode = "plugin"
        applicability = {"status": "enabled"}
    else:
        backend_used = "core"
        runner_mode = "core"
        applicability = {"status": "fallback", "reason": fallback_reason}

    return {
        "backend_requested": requested,
        "backend_used": backend_used,
        "runner_mode": runner_mode,
        "plugin_id": plugin_id,
        "plugin_version": plugin_version,
        "license_class": license_class,
        "applicability": applicability,
        "fallback_reason": fallback_reason,
        "policy": {
            "metadata_only": True,
            "allows_external_execution": False,
        },
    }
