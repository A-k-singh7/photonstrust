"""KPI computation for QKD links and networks."""

from __future__ import annotations

from datetime import datetime, timezone

from photonstrust.analytics.types import KPI


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOWER_IS_BETTER = {"cost_per_key_bit", "link_loss_db"}


def _status(value: float, target: float | None, kpi_id: str) -> str:
    """Determine KPI status relative to its target."""
    if target is None:
        return "on_target"
    if kpi_id in _LOWER_IS_BETTER:
        return "on_target" if value <= target else "above_target"
    return "on_target" if value >= target else "below_target"


# ---------------------------------------------------------------------------
# Link KPIs
# ---------------------------------------------------------------------------

_DEFAULT_LINK_TARGETS: dict[str, float] = {
    "key_rate_efficiency": 0.5,
    "cost_per_key_bit": 1e-6,
    "qber_margin": 0.5,
    "link_loss_db": 20.0,
}


def compute_link_kpis(
    link_id: str,
    sim_result: dict,
    cost_result: dict,
    *,
    targets: dict | None = None,
) -> list[KPI]:
    """Compute KPIs for a single QKD link.

    Parameters
    ----------
    link_id:
        Identifier of the link.
    sim_result:
        Simulation output dict (key_rate, qber, loss_db, entanglement_rate_hz ...).
    cost_result:
        Cost-model output dict (cost_per_key_bit_usd ...).
    targets:
        Optional overrides for default KPI targets.
    """
    tgt = {**_DEFAULT_LINK_TARGETS, **(targets or {})}
    kpis: list[KPI] = []

    # 1. Key-rate efficiency
    actual_key_rate = float(sim_result.get("key_rate", 0))
    theoretical_max = max(float(sim_result.get("entanglement_rate_hz", 1e6)), 1)
    efficiency = actual_key_rate / theoretical_max
    kpis.append(KPI(
        kpi_id="key_rate_efficiency",
        name="Key-Rate Efficiency",
        value=round(efficiency, 6),
        unit="ratio",
        target=tgt.get("key_rate_efficiency"),
        status=_status(efficiency, tgt.get("key_rate_efficiency"), "key_rate_efficiency"),
    ))

    # 2. Cost per key bit
    cpb = float(cost_result.get("cost_per_key_bit_usd", 0))
    kpis.append(KPI(
        kpi_id="cost_per_key_bit",
        name="Cost per Key Bit",
        value=cpb,
        unit="USD/bit",
        target=tgt.get("cost_per_key_bit"),
        status=_status(cpb, tgt.get("cost_per_key_bit"), "cost_per_key_bit"),
    ))

    # 3. QBER margin  (1 - qber/0.11)
    qber = float(sim_result.get("qber", 0))
    qber_margin = 1.0 - qber / 0.11
    kpis.append(KPI(
        kpi_id="qber_margin",
        name="QBER Margin",
        value=round(qber_margin, 6),
        unit="ratio",
        target=tgt.get("qber_margin"),
        status=_status(qber_margin, tgt.get("qber_margin"), "qber_margin"),
    ))

    # 4. Link loss
    loss = float(sim_result.get("loss_db", 0))
    kpis.append(KPI(
        kpi_id="link_loss_db",
        name="Link Loss",
        value=round(loss, 4),
        unit="dB",
        target=tgt.get("link_loss_db"),
        status=_status(loss, tgt.get("link_loss_db"), "link_loss_db"),
    ))

    return kpis


# ---------------------------------------------------------------------------
# Network KPIs
# ---------------------------------------------------------------------------

def compute_network_kpis(
    network_sim_result: dict,
    network_cost_result: dict,
) -> list[KPI]:
    """Compute aggregate KPIs for an entire QKD network.

    Parameters
    ----------
    network_sim_result:
        Dict with a ``links`` list of per-link sim results.
    network_cost_result:
        Dict with ``total_capex_usd``, ``cost_per_key_bit_network_avg_usd``, etc.
    """
    links = network_sim_result.get("links", [])
    key_rates = [float(l.get("key_rate", 0)) for l in links]

    total_links = len(links)
    avg_rate = sum(key_rates) / max(total_links, 1)
    min_rate = min(key_rates) if key_rates else 0.0

    total_cost = float(network_cost_result.get("total_capex_usd", 0))
    avg_cpb = float(network_cost_result.get("cost_per_key_bit_network_avg_usd", 0))

    return [
        KPI(kpi_id="total_links", name="Total Links", value=float(total_links),
            unit="count", target=None, status="on_target"),
        KPI(kpi_id="average_key_rate", name="Average Key Rate", value=round(avg_rate, 4),
            unit="bps", target=None, status="on_target"),
        KPI(kpi_id="min_key_rate", name="Min Key Rate (Bottleneck)", value=round(min_rate, 4),
            unit="bps", target=None, status="on_target"),
        KPI(kpi_id="total_cost_usd", name="Total Cost", value=round(total_cost, 2),
            unit="USD", target=None, status="on_target"),
        KPI(kpi_id="average_cost_per_bit", name="Average Cost per Bit",
            value=avg_cpb, unit="USD/bit", target=None, status="on_target"),
    ]
