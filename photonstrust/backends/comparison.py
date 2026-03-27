"""Cross-fidelity comparison and multi-fidelity evidence building."""

from __future__ import annotations

from photonstrust.backends.registry import get_backend, list_backends
from photonstrust.backends.types import ComparisonResult, MultifidelityEvidence


def run_cross_fidelity_comparison(
    *,
    scenario: dict,
    backends: list[str] | None = None,
    seed: int | None = None,
    metrics: list[str] | None = None,
    tolerance_rel: float = 0.10,
) -> ComparisonResult:
    """Run the same scenario across multiple backends and compare outputs."""
    if backends is None:
        backends = [b["name"] for b in list_backends()]

    metrics = metrics or ["key_rate_bps", "qber_total", "loss_db"]

    results: dict[str, dict] = {}
    provenances: list[dict] = []

    for name in backends:
        backend = get_backend(name)
        result = backend.simulate("qkd_link", scenario, seed=seed)
        results[name] = result
        provenances.append(backend.provenance())

    deltas: dict[str, dict] = {}
    max_rel = 0.0

    for i, n1 in enumerate(backends):
        for n2 in backends[i + 1 :]:
            pair_key = f"{n1}_vs_{n2}"
            pair_deltas: dict[str, dict] = {}
            for m in metrics:
                v1 = float(results[n1].get(m, 0))
                v2 = float(results[n2].get(m, 0))
                ref = max(abs(v1), abs(v2), 1e-15)
                rel = abs(v1 - v2) / ref
                pair_deltas[m] = {"absolute": v1 - v2, "relative": rel}
                max_rel = max(max_rel, rel)
            deltas[pair_key] = pair_deltas

    verdict = "consistent" if max_rel < tolerance_rel else "divergent"

    return ComparisonResult(
        scenario_id=scenario.get("scenario_id", "unknown"),
        backends_compared=backends,
        results=results,
        deltas=deltas,
        consistency_verdict=verdict,
        max_relative_delta=max_rel,
        provenance=provenances,
    )


def build_multifidelity_evidence(
    comparison: ComparisonResult,
) -> MultifidelityEvidence:
    """Wrap a comparison result into a multi-fidelity evidence artifact."""
    tier_coverage: dict[int, str] = {}
    for b in list_backends():
        if b["name"] in comparison.backends_compared:
            tier_coverage[b["tier"]] = b["name"]

    recommendation = (
        "Use highest available tier"
        if comparison.consistency_verdict == "consistent"
        else "Investigate divergence before trusting results"
    )

    return MultifidelityEvidence(
        comparison=comparison,
        tier_coverage=tier_coverage,
        recommendation=recommendation,
    )
