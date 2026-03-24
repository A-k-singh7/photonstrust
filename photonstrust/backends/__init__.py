"""Multi-fidelity backend framework."""

from __future__ import annotations

from photonstrust.backends.registry import (
    discover_backends,
    get_backend,
    get_backend_for_tier,
    list_backends,
    register_backend,
)
from photonstrust.backends.comparison import (
    build_multifidelity_evidence,
    run_cross_fidelity_comparison,
)
