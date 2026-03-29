"""Tier-0 analytic physics backend."""

from __future__ import annotations

import math

from photonstrust.utils import binary_entropy


class AnalyticBackend:
    """Closed-form QKD link budget model (tier 0)."""

    @property
    def name(self) -> str:
        return "analytic"

    @property
    def tier(self) -> int:
        return 0

    def simulate(
        self,
        component: str,
        inputs: dict,
        *,
        seed: int | None = None,
        mode: str = "preview",
    ) -> dict:
        distance_km = float(inputs.get("distance_km", 50))
        fiber_loss = float(inputs.get("fiber_loss_db_per_km", 0.2))
        loss_db = fiber_loss * distance_km + float(
            inputs.get("connector_loss_db", 2.0)
        )
        eta = 10 ** (-loss_db / 10)

        pde = float(inputs.get("pde", 0.25))
        dark = float(inputs.get("dark_counts_cps", 1000))
        rep_rate = float(inputs.get("rep_rate_hz", 1e8))
        mu = float(inputs.get("mu", 0.5))

        # Simplified BB84 decoy gain approximation
        q_mu = 1 - (1 - pde * eta) * math.exp(-mu * eta * pde)
        e_det = 0.5 * dark / max(rep_rate * q_mu, 1)
        e_opt = float(inputs.get("misalignment_prob", 0.01))
        qber = min(0.5, e_det + e_opt)

        h2 = binary_entropy(qber)
        f_ec = float(inputs.get("ec_efficiency", 1.16))
        key_rate = max(0.0, rep_rate * q_mu * (1 - f_ec * h2 - h2))

        return {
            "key_rate_bps": key_rate,
            "qber_total": qber,
            "loss_db": loss_db,
            "eta_channel": eta,
        }

    def applicability(self, inputs: dict) -> dict:
        return {"applicable": True, "warnings": []}

    def provenance(self) -> dict:
        return {"backend_name": "analytic", "tier": 0, "version": "1.0.0"}
