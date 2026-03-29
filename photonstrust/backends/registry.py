"""Backend discovery and registry."""

from __future__ import annotations

from photonstrust.backends.types import PhysicsBackend

_REGISTRY: dict[str, PhysicsBackend] = {}


def register_backend(backend: PhysicsBackend) -> None:
    """Register a backend instance by name."""
    _REGISTRY[backend.name] = backend


def get_backend(name: str) -> PhysicsBackend:
    """Return a registered backend, auto-discovering if needed."""
    if name not in _REGISTRY:
        discover_backends()
    return _REGISTRY[name]  # KeyError if truly missing


def list_backends() -> list[dict]:
    """Return summary dicts for every registered backend."""
    if not _REGISTRY:
        discover_backends()
    return [{"name": b.name, "tier": b.tier} for b in _REGISTRY.values()]


def discover_backends() -> list[PhysicsBackend]:
    """Import and register all built-in backends."""
    from photonstrust.backends.analytic import AnalyticBackend
    from photonstrust.backends.stochastic import StochasticBackend

    if "analytic" not in _REGISTRY:
        register_backend(AnalyticBackend())
    if "stochastic" not in _REGISTRY:
        register_backend(StochasticBackend())

    return list(_REGISTRY.values())


def get_backend_for_tier(
    tier: int, *, fallback: bool = True
) -> PhysicsBackend | None:
    """Return a backend matching *tier*, optionally falling back to a lower tier."""
    if not _REGISTRY:
        discover_backends()

    for b in _REGISTRY.values():
        if b.tier == tier:
            return b

    if not fallback:
        return None

    candidates = sorted(
        [b for b in _REGISTRY.values() if b.tier < tier],
        key=lambda b: b.tier,
        reverse=True,
    )
    return candidates[0] if candidates else None
