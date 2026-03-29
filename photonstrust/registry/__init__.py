"""Backend-owned registries for UI/runtime interoperability.

These registries are intended to make scientific meaning explicit (units,
defaults, ranges) while keeping thin clients (web/UI) non-authoritative.
"""

from .kinds import build_kinds_registry

__all__ = ["build_kinds_registry"]
