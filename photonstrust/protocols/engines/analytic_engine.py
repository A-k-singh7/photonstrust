"""Analytic reference protocol engine."""

from __future__ import annotations

from photonstrust.protocols.engines.base import ProtocolEngine, ProtocolPrimitiveResult


class AnalyticProtocolEngine(ProtocolEngine):
    engine_id = "analytic"
    engine_version = "0.1"

    def supported_primitives(self) -> tuple[str, ...]:
        return ("swap_bsm_equal_bits",)

    def run_primitive(self, primitive: str, *, seed: int | None = None) -> ProtocolPrimitiveResult:
        _ = seed
        normalized = str(primitive or "").strip().lower()
        if normalized != "swap_bsm_equal_bits":
            raise ValueError(f"unsupported primitive {primitive!r} for analytic protocol engine")
        return ProtocolPrimitiveResult(
            engine_id=self.engine_id,
            primitive=normalized,
            metrics={"success_probability": 0.5},
            metadata={"reference_model": "closed_form"},
        )
