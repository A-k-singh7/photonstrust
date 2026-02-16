"""Stochastic backend wrappers for detector-domain simulation."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from photonstrust.physics.backends.base import ApplicabilityReport, PhysicsBackend, normalize_component_name
from photonstrust.physics.detector import simulate_detector


class StochasticBackend(PhysicsBackend):
    backend_name = "stochastic"
    backend_version = "0.1"

    def simulate(
        self,
        component: str,
        inputs: Mapping[str, Any],
        *,
        seed: int | None = None,
        mode: str | None = None,
    ) -> Any:
        del mode
        normalized = normalize_component_name(component)
        if normalized != "detector":
            raise ValueError(f"Stochastic backend does not support component: {component!r}")

        detector_cfg, arrival_times_ps = _parse_detector_inputs(inputs)
        detector_cfg["physics_backend"] = "stochastic"
        if seed is not None:
            detector_cfg["seed"] = int(seed)
        return simulate_detector(detector_cfg, arrival_times_ps)

    def applicability(self, component: str, inputs: Mapping[str, Any]) -> ApplicabilityReport:
        del inputs
        normalized = normalize_component_name(component)
        if normalized == "detector":
            return ApplicabilityReport(status="pass", reasons=())
        return ApplicabilityReport(
            status="fail",
            reasons=(f"component '{normalized}' is not implemented by stochastic backend",),
        )


def _parse_detector_inputs(inputs: Mapping[str, Any]) -> tuple[dict[str, Any], list[float]]:
    if "detector_cfg" in inputs:
        raw_cfg = inputs.get("detector_cfg")
        if not isinstance(raw_cfg, Mapping):
            raise ValueError("detector_cfg must be a mapping")
        cfg = copy.deepcopy(dict(raw_cfg))
        arrivals = list(inputs.get("arrival_times_ps", []) or [])
        return cfg, [float(v) for v in arrivals]

    cfg = copy.deepcopy(dict(inputs))
    arrivals = list(cfg.pop("arrival_times_ps", []) or [])
    return cfg, [float(v) for v in arrivals]
