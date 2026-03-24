"""Tier-1 stochastic (Monte Carlo) physics backend."""

from __future__ import annotations

import numpy as np

from photonstrust.backends.analytic import AnalyticBackend


class StochasticBackend:
    """Monte Carlo wrapper around the analytic model (tier 1)."""

    @property
    def name(self) -> str:
        return "stochastic"

    @property
    def tier(self) -> int:
        return 1

    def simulate(
        self,
        component: str,
        inputs: dict,
        *,
        seed: int | None = None,
        mode: str = "preview",
    ) -> dict:
        rng = np.random.default_rng(seed)
        n_samples = int(inputs.get("mc_samples", 100))

        analytic = AnalyticBackend()
        base = analytic.simulate(component, inputs, seed=seed)

        rates: list[float] = []
        for _ in range(n_samples):
            perturbed = dict(inputs)
            perturbed["fiber_loss_db_per_km"] = max(
                0.0,
                float(inputs.get("fiber_loss_db_per_km", 0.2))
                + rng.normal(0, 0.01),
            )
            perturbed["pde"] = min(
                1.0,
                max(
                    0.0,
                    float(inputs.get("pde", 0.25)) + rng.normal(0, 0.02),
                ),
            )
            r = analytic.simulate(component, perturbed, seed=None)
            rates.append(r["key_rate_bps"])

        return {
            **base,
            "key_rate_mean": float(np.mean(rates)),
            "key_rate_std": float(np.std(rates)),
            "mc_samples": n_samples,
        }

    def applicability(self, inputs: dict) -> dict:
        return {"applicable": True, "warnings": []}

    def provenance(self) -> dict:
        return {"backend_name": "stochastic", "tier": 1, "version": "1.0.0"}
