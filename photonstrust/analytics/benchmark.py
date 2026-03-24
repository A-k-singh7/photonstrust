"""Vendor benchmarking for QKD components."""

from __future__ import annotations

from collections import defaultdict

from photonstrust.analytics.types import VendorBenchmark


def benchmark_vendors(
    components: list[dict],
    *,
    category: str = "detector",
    scenario_defaults: dict | None = None,
) -> list[VendorBenchmark]:
    """Benchmark vendors for a given component category.

    Parameters
    ----------
    components:
        List of component dicts, each with at least ``vendor``,
        ``component_id``, and ``params`` keys.
    category:
        Component category label (e.g. ``"detector"``).
    scenario_defaults:
        Optional defaults merged into each component's params.
    """
    defaults = scenario_defaults or {}

    # Group by vendor
    by_vendor: dict[str, list[dict]] = defaultdict(list)
    for comp in components:
        vendor = comp.get("vendor", "unknown")
        by_vendor[vendor].append(comp)

    benchmarks: list[VendorBenchmark] = []
    for vendor, comps in by_vendor.items():
        scores: list[float] = []
        costs: list[float] = []
        reliabilities: list[float] = []
        comp_ids: list[str] = []

        for c in comps:
            params = {**defaults, **c.get("params", {})}
            pde = float(params.get("pde", 0.85))

            # Simplified key-rate proxy: PDE * 1000
            score = pde * 1000.0
            scores.append(score)

            # Cost per bit estimate
            est_cost = float(params.get("estimated_cost_usd", 50_000))
            bits_per_year = score * 3600.0 * 8760.0
            cpb = est_cost / max(bits_per_year, 1.0)
            costs.append(cpb)

            # Reliability from degradation model (default 0.95)
            rel = float(params.get("reliability", 0.95))
            reliabilities.append(rel)

            comp_ids.append(c.get("component_id", "unknown"))

        n = len(comps)
        benchmarks.append(VendorBenchmark(
            vendor=vendor,
            component_category=category,
            average_key_rate_bps=round(sum(scores) / n, 4),
            average_cost_per_bit_usd=sum(costs) / n,
            reliability_score=round(sum(reliabilities) / n, 4),
            sample_size=n,
            components_tested=comp_ids,
        ))

    # Sort by cost per bit ascending
    benchmarks.sort(key=lambda b: b.average_cost_per_bit_usd)
    return benchmarks
