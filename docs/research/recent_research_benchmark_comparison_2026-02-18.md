# Recent Research Benchmark Comparison (2026-02-18)

This report summarizes a direct model-vs-literature comparison using:

- `scripts/compare_recent_research_benchmarks.py`
- output artifacts in `results/research_validation/`

## Scope

The benchmark set covers recent published checkpoints for:

- TF/PM-QKD (long-distance fiber)
- MDI-QKD (relay attenuation benchmark)
- BB84-like checkpoints (single-photon papers, mapped to BB84 proxy)

Primary sources used:

- https://doi.org/10.1007/s44214-023-00039-9
- https://doi.org/10.1038/s41467-023-36573-2
- https://doi.org/10.1038/s41534-025-01052-7
- https://arxiv.org/abs/2406.02045
- https://arxiv.org/abs/2409.18502

## Summary Metrics

From `results/research_validation/recent_research_benchmark_comparison.json`:

- median paper-locked relative error: `0.55771`
- median best-fit relative error (bounded multi-parameter fit): `0.000426045`
- cases within 1% error (paper-locked): `0/10`
- cases within 1% error (best-fit): `10/10`

Interpretation:

- One-parameter (`mu`) fitting is still insufficient on several hard checkpoints.
- Bounded multi-parameter calibration can match all current benchmark points to <1% relative error.
- A subset of fitted points requires aggressive parameter shifts (for example rep-rate changes on TF 615.6 km), so best-fit should be treated as a calibration ceiling, not paper-locked reproduction.

## Notable Outcomes

Strong alignment after bounded best-fit calibration:

- All 10 benchmark checkpoints fall below 1% relative error.

Persistent mismatch in paper-locked mode:

- TF 615.6 km and TF 1002 km remain high-error without additional parameter calibration.
- GaN BB84 proxy cases remain high-error when forced to strict paper-locked defaults.

## Recommended Next Model Upgrades

1. Separate `paper_locked` and `calibrated_best_fit` reporting in release gates (do not merge them into one score).
2. Add dedicated SPS/GaN protocol modeling (reduce reliance on BB84-decoy proxy compensation).
3. Add stronger finite-key realism for ultra-long-distance TF checkpoints.
4. Move from scalar bounds to per-paper parameter priors with explicit uncertainty envelopes.

## Reproduce

```bash
python scripts/compare_recent_research_benchmarks.py
```

Optional knobs:

```bash
python scripts/compare_recent_research_benchmarks.py --grid-size 41 --fit-passes 4
```

Artifacts:

- `results/research_validation/recent_research_benchmark_comparison.json`
- `results/research_validation/recent_research_benchmark_comparison.md`
