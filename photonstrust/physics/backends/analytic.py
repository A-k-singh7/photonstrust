"""Analytic backend wrappers for emitter and memory domains."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from photonstrust.physics.backends.base import ApplicabilityReport, PhysicsBackend, normalize_component_name
from photonstrust.physics.emitter import get_emitter_stats
from photonstrust.physics.memory import simulate_memory


class AnalyticBackend(PhysicsBackend):
    backend_name = "analytic"
    backend_version = "0.1"

    def simulate(
        self,
        component: str,
        inputs: Mapping[str, Any],
        *,
        seed: int | None = None,
        mode: str | None = None,
    ) -> Any:
        normalized = normalize_component_name(component)
        if normalized == "emitter":
            payload = copy.deepcopy(dict(inputs))
            payload["physics_backend"] = "analytic"
            if seed is not None:
                payload["seed"] = int(seed)
            if mode is not None:
                payload["emission_mode"] = str(mode)
            return get_emitter_stats(payload)

        if normalized == "memory":
            memory_cfg, wait_time_ns = _parse_memory_inputs(inputs)
            memory_cfg["physics_backend"] = "analytic"
            if seed is not None:
                memory_cfg["seed"] = int(seed)
            return simulate_memory(memory_cfg, wait_time_ns=wait_time_ns)

        raise ValueError(f"Analytic backend does not support component: {component!r}")

    def applicability(self, component: str, inputs: Mapping[str, Any]) -> ApplicabilityReport:
        normalized = normalize_component_name(component)
        if normalized in {"emitter", "memory"}:
            return ApplicabilityReport(status="pass", reasons=())
        return ApplicabilityReport(
            status="fail",
            reasons=(f"component '{normalized}' is not implemented by analytic backend",),
        )


def _parse_memory_inputs(inputs: Mapping[str, Any]) -> tuple[dict[str, Any], float]:
    if "memory_cfg" in inputs:
        raw_cfg = inputs.get("memory_cfg")
        if not isinstance(raw_cfg, Mapping):
            raise ValueError("memory_cfg must be a mapping")
        cfg = copy.deepcopy(dict(raw_cfg))
        wait_time_ns = float(inputs.get("wait_time_ns", 0.0) or 0.0)
        return cfg, wait_time_ns

    cfg = copy.deepcopy(dict(inputs))
    wait_time_ns = float(cfg.pop("wait_time_ns", 0.0) or 0.0)
    return cfg, wait_time_ns
