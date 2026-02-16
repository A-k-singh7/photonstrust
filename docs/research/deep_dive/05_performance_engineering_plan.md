# Performance Engineering Plan

This document defines runtime goals and optimization strategy.

## Performance targets
- Single scenario, quick mode: under 10 seconds
- Single scenario, full uncertainty mode: under 2 minutes
- Batch benchmark generation: linear scaling with scenario count

## Bottleneck map
- QuTiP trajectory simulation
- Large posterior propagation runs
- Repeated event scheduling at long distances

## Optimization tactics
- Cache physics outputs by parameter hash
- Batch trajectory runs where possible
- Reuse event graph skeletons across parameter sweeps
- Enable approximate mode for UI previews

## Rare-event handling
- Use importance sampling for long-distance heralding estimates
- Preserve unbiased estimators with weight normalization

## Profiling workflow
- Add timing hooks around major pipeline stages
- Capture profiling output per benchmark scenario

## Resource strategy
- CPU-first implementation with optional parallel workers
- Document memory usage limits for large sweeps

## Definition of done
- All flagship scenarios meet target runtime envelopes.
- Performance regression test included in CI smoke checks.


## Inline citations (web, verified 2026-02-12)
Applied to: bottleneck map, optimization tactics, profiling workflow, and scaling targets.
- QuTiP benchmark process and plots: https://qutip.org/qutip-benchmark/
- QuTiP release line and migration context: https://qutip.org/download.html
- qutip-qip package separation: https://github.com/qutip/qutip-qip
- Qiskit primitives guide: https://qiskit.org/documentation/guides/primitives.html
- Qiskit transpiler stages: https://qiskit.org/documentation/guides/transpiler-stages.html
- Bayesian optimization for repeater protocol search: https://arxiv.org/abs/2502.02208

