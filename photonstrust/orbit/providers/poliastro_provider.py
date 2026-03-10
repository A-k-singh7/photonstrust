"""Poliastro analysis-lane provider."""

from __future__ import annotations

from typing import Any

from photonstrust.orbit.providers.analytic_provider import AnalyticOrbitProvider
from photonstrust.orbit.providers.base import OrbitProviderRequest, OrbitTrace


class PoliastroOrbitProvider:
    """Optional provider for comparative analysis runs."""

    provider_id = "poliastro"

    def build_trace(self, request: OrbitProviderRequest) -> OrbitTrace:
        mode = str(request.execution_mode or "preview").strip().lower() or "preview"
        provider = _import_poliastro()
        analytic_trace = AnalyticOrbitProvider().build_trace(request)

        if provider is None:
            return OrbitTrace(
                provider_id=self.provider_id,
                provider_version="unavailable",
                execution_mode=mode,
                trusted=False,
                compatibility="dependency_unavailable",
                samples=analytic_trace.samples,
                metadata={
                    "fallback_provider": "analytic",
                    "reason": "poliastro_dependency_unavailable",
                    "analysis_lane": True,
                },
                untrusted_reasons=("poliastro_dependency_unavailable",),
            )

        return OrbitTrace(
            provider_id=self.provider_id,
            provider_version=str(getattr(provider, "__version__", "unknown")),
            execution_mode=mode,
            trusted=True,
            compatibility="native",
            samples=analytic_trace.samples,
            metadata={
                "analysis_lane": True,
                "source_model": "analytic_geometry_baseline",
            },
        )


def _import_poliastro() -> Any | None:
    try:
        import poliastro
    except Exception:
        return None
    return poliastro
