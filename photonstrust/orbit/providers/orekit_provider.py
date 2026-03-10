"""Orekit reference-lane provider via optional sidecar artifact."""

from __future__ import annotations

import json
import os
from pathlib import Path

from photonstrust.orbit.providers.analytic_provider import AnalyticOrbitProvider
from photonstrust.orbit.providers.base import OrbitProviderRequest, OrbitTrace, OrbitTraceSample


class OrekitReferenceProvider:
    """Reference provider that reads sidecar output or falls back explicitly."""

    provider_id = "orekit"

    def build_trace(self, request: OrbitProviderRequest) -> OrbitTrace:
        sidecar_trace = _load_sidecar_trace(request)
        if sidecar_trace is not None:
            return sidecar_trace

        analytic_trace = AnalyticOrbitProvider().build_trace(request)
        return OrbitTrace(
            provider_id=self.provider_id,
            provider_version="sidecar-unavailable",
            execution_mode=str(request.execution_mode or "preview"),
            trusted=False,
            compatibility="reference_fallback",
            samples=analytic_trace.samples,
            metadata={
                "fallback_provider": "analytic",
                "reason": "orekit_reference_sidecar_unavailable",
                "sidecar_env": "PHOTONTRUST_OREKIT_REFERENCE_JSON",
            },
            untrusted_reasons=("orekit_reference_sidecar_unavailable",),
        )


def _load_sidecar_trace(request: OrbitProviderRequest) -> OrbitTrace | None:
    raw = os.environ.get("PHOTONTRUST_OREKIT_REFERENCE_JSON")
    if raw is None or not str(raw).strip():
        return None
    path = Path(str(raw)).expanduser().resolve()
    if not path.is_file():
        return None

    payload = json.loads(path.read_text(encoding="utf-8"))
    samples_raw = payload.get("samples") if isinstance(payload, dict) else None
    if not isinstance(samples_raw, list) or not samples_raw:
        return None

    samples: list[OrbitTraceSample] = []
    for row in samples_raw:
        if not isinstance(row, dict):
            continue
        samples.append(
            OrbitTraceSample(
                t_s=float(row.get("t_s", 0.0) or 0.0),
                elevation_deg=float(row.get("elevation_deg", 0.0) or 0.0),
                slant_range_km=float(
                    row.get("slant_range_km", row.get("distance_km", 0.0)) or 0.0
                ),
            )
        )

    if not samples:
        return None
    samples.sort(key=lambda item: float(item.t_s))

    return OrbitTrace(
        provider_id="orekit",
        provider_version=str(payload.get("provider_version") or "sidecar"),
        execution_mode=str(request.execution_mode or "preview"),
        trusted=True,
        compatibility="sidecar",
        samples=tuple(samples),
        metadata={
            "source": str(path),
            "source_hash": str(payload.get("source_hash") or ""),
            "note": "sidecar-provided orekit reference trace",
        },
    )
