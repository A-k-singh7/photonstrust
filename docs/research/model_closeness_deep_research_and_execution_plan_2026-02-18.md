# Model Closeness Deep Research + Execution Plan (2026-02-18)

## Executive answer

Yes, we can get much closer to published values.

Your current harness already shows this: median relative error drops from `0.611838` to `0.0594014` with only a `mu` sweep, which means the core model family is directionally correct. The remaining misses are structural (protocol/security/receiver specifics), not just parameter tuning.

## Current baseline (from repo)

- Script: `scripts/validation/compare_recent_research_benchmarks.py`
- Output: `results/research_validation/recent_research_benchmark_comparison.json`
- Current summary:
  - median baseline rel. error: `0.611838`
  - median best-fit rel. error (`mu` only): `0.0594014`
- Dominant outliers:
  - `tf_1002km_3.11e-12_bpp` (ultra-long finite-key regime)
  - `bb84_33km_7.58e-7_bpp` and `bb84_30km_6.06e-8_bpp` (SPS/GaN experiments mapped to BB84-WCP proxy)

## Deep research synthesis (what matters for closeness)

## 1) TF/PM-QKD: finite-key/security modeling is the big gap at extreme distance

- PM-QKD core equations are from Ma et al. PRX 2018 (gain/QBER/phase-slicing model): https://doi.org/10.1103/PhysRevX.8.031043 and https://arxiv.org/abs/1805.05538
- Extreme-distance TF results are finite-key dominated (not asymptotic-only); recent long-distance literature emphasizes composable finite-size analysis and statistical fluctuation handling:
  - https://arxiv.org/abs/2303.15795
  - https://arxiv.org/abs/2502.11860
  - https://arxiv.org/abs/1910.12416

Implication: `mu` fitting alone cannot recover the 1000+ km regime. You need protocol-specific finite-key terms and statistical bounds wired into TF lane.

## 2) MDI-QKD: core formula is fine, but experiment reproduction needs richer calibration dimensions

- MDI asymptotic structure remains Xu et al. Eq. (1) + decoy estimation: https://arxiv.org/abs/1305.6965
- Newer implementations add hardware-specific constraints and optimized decoy/intensity configurations:
  - https://doi.org/10.1038/s41534-025-01052-7
  - https://arxiv.org/abs/2502.11860

Implication: keep the current MDI core, but calibrate more than `mu` (decoys, alignment/noise, detector/time-window parameters).

## 3) BB84 proxy is not valid for SPS experiments

- Decoy BB84/WCP bounds and finite-key references:
  - https://arxiv.org/abs/1311.7129
  - https://doi.org/10.1103/PhysRevA.89.022307
- Recent SPS-focused comparisons show different behavior than WCP decoy assumptions:
  - https://arxiv.org/abs/2406.02045
  - https://arxiv.org/abs/2409.18502
  - https://arxiv.org/abs/2502.16875

Implication: add a dedicated SPS protocol surface instead of forcing SPS checkpoints through `bb84_decoy`.

## 4) Detector effects must be profile-specific at very low SKR

- Practical QKD afterpulsing models (memory kernels / geometric-exponential tails): https://arxiv.org/abs/1407.3320
- Dead-time/security implications in QKD systems: https://arxiv.org/abs/0708.0241

Implication: low-rate/high-loss points are highly sensitive to detector modeling; you need per-paper detector profiles (dead-time model, afterpulse model, gating/jitter windows).

## 5) SPDC statistics and source model-family separation

- Two-mode squeezed-vacuum/SPDC statistics differ from Poissonian WCP assumptions (PM-QKD and quantum optics literature context):
  - https://arxiv.org/abs/1805.05538
  - https://arxiv.org/abs/quant-ph/9412001

Implication: keep source-family-specific math strict (SPDC vs WCP vs SPS), avoid cross-family shortcuts.

## Full execution plan

## Workstream A: Protocol model separation (highest priority)

Goal: eliminate structural mismatch from protocol/source conflation.

1. Add `sps_qkd` protocol lane.
2. Keep `bb84_decoy` for WCP-only scenarios.
3. Require explicit source family in scenario (`wcp`, `spdc`, `sps`).
4. Add source-level checks that block invalid protocol-source pairings in strict mode.

Code targets:

- `photonstrust/qkd_protocols/registry.py`
- `photonstrust/qkd_protocols/__init__.py`
- new `photonstrust/qkd_protocols/sps_qkd.py`
- `photonstrust/qkd.py` dispatch + validation

Acceptance:

- SPS benchmark cases no longer use BB84 proxy.
- Outlier set excludes proxy-induced errors by construction.

## Workstream B: Finite-key realism upgrade (TF + BB84 + MDI)

Goal: replace surrogate penalty with protocol-aware composable finite-key accounting.

1. Extend `finite_key.py` from scalar penalty scaffold to protocol-specific backends:
   - `finite_key_bb84_decoy`
   - `finite_key_tf_pm`
   - `finite_key_mdi`
2. Implement epsilon-ledger accounting (correctness, secrecy, PE, EC, PA).
3. Support selectable fluctuation bounds (Chernoff/Hoeffding/Azuma-style profiles).
4. Plumb block-size and tail-bound choices into scenario schema.

Code targets:

- `photonstrust/qkd_protocols/finite_key.py`
- protocol callers in `bb84_decoy.py`, `pm_qkd.py`, `mdi_qkd.py`
- `schemas/` + `photonstrust/registry/kinds.py`

Acceptance:

- 1002 km TF checkpoint becomes non-zero and within one order of magnitude before final calibration.
- Finite-key diagnostics reported in benchmark output (not hidden).

## Workstream C: Detector profile fidelity

Goal: make low-rate predictions stable and paper-reproducible.

1. Add detector profile presets keyed by paper/experiment family.
2. Support afterpulse kernel variants and parameterized decay models.
3. Keep dead-time model selectable (`nonparalyzable`, `paralyzable`) and expose in benchmark configs.
4. Add timing-window policies (fixed vs jitter-driven vs experiment-locked).

Code targets:

- `photonstrust/physics/detector.py`
- `photonstrust/qkd_protocols/common.py`
- benchmark scenario/profile files in `datasets/` or `benchmarks/`

Acceptance:

- For each benchmark paper, detector assumptions are explicit and reproducible.
- Sensitivity sweeps show monotonic/physically consistent behavior.

## Workstream D: Multi-parameter calibration and reproducibility

Goal: move from 1D `mu` fitting to constrained multi-parameter inverse fitting.

1. Extend benchmark fitter from `mu`-only to joint fitting:
   - `mu`, `nu`, `omega`, `misalignment`, `pde`, `dark_counts`, `window_ps`, finite-key block params.
2. Add per-paper priors + hard bounds from paper-reported values.
3. Use train/holdout split across distances per paper family to avoid overfit.
4. Report posterior ranges and identifiability flags.

Code targets:

- `scripts/validation/compare_recent_research_benchmarks.py`
- `photonstrust/calibrate/bayes.py` + `photonstrust/calibrate/priors.py`
- new paper-profile config files

Acceptance:

- median holdout relative error <= `0.10` in first pass, <= `0.05` in second pass.
- No parameter leaves physically plausible ranges.

## Workstream E: Validation gates in CI

Goal: prevent regressions once model closeness improves.

1. Add `research_closeness_gate` test stage with per-case thresholds.
2. Separate threshold classes:
   - `strict` (fully modeled cases),
   - `expected_gap` (known unresolved physics/hardware unknowns).
3. Fail CI on regressions against locked benchmark snapshots.

Code targets:

- `tests/` new benchmark-gate tests
- CI workflow in `.github/workflows/`
- `photonstrust/benchmarks/research_validation.py`

Acceptance:

- CI blocks closeness regressions automatically.
- Benchmark markdown/json artifacts published per run.

## Execution schedule (4-week aggressive pass)

Week 1:

- Implement Workstream A (SPS lane + protocol/source guards).
- Start Workstream D paper-profile schema + priors.

Week 2:

- Implement Workstream B finite-key backend split (TF first, then BB84/MDI).
- Add benchmark harness multi-parameter fitting.

Week 3:

- Implement Workstream C detector profile upgrades.
- Run calibration + holdout validation for all benchmark families.

Week 4:

- Implement Workstream E CI gates.
- Freeze benchmark baselines and ship reproducibility docs.

## Hard success criteria (definition of done)

1. Median holdout relative error <= `5%` across fully-modeled checkpoints.
2. No unresolved-case relative error > `2x` without explicit annotation.
3. TF ultra-long case (`1002 km`) is non-zero and within modeled finite-key uncertainty band.
4. SPS benchmarks are evaluated by `sps_qkd` (not BB84 proxy).
5. CI contains automated closeness regression gate.

## Immediate next actions (this week)

1. Create paper-profile config files for all current 10 benchmark cases.
2. Implement `sps_qkd` protocol and route the two GaN/SPS checkpoints to it.
3. Refactor `finite_key.py` into protocol-specific backends.
4. Upgrade benchmark script from 1D `mu` sweep to constrained multi-parameter fit.
5. Add first CI closeness test with conservative thresholds.

## Source links used for this plan

- PM-QKD/TF baseline model:
  - https://doi.org/10.1103/PhysRevX.8.031043
  - https://arxiv.org/abs/1805.05538
- TF/PM long-distance and finite-key direction:
  - https://arxiv.org/abs/2303.15795
  - https://arxiv.org/abs/2502.11860
  - https://arxiv.org/abs/1910.12416
- MDI core + recent experiment:
  - https://arxiv.org/abs/1305.6965
  - https://doi.org/10.1038/s41534-025-01052-7
- BB84 decoy finite-key and SPS comparisons:
  - https://arxiv.org/abs/1311.7129
  - https://doi.org/10.1103/PhysRevA.89.022307
  - https://arxiv.org/abs/2406.02045
  - https://arxiv.org/abs/2409.18502
  - https://arxiv.org/abs/2502.16875
- Detector realism:
  - https://arxiv.org/abs/1407.3320
  - https://arxiv.org/abs/0708.0241
- SPDC/TMSV statistics context:
  - https://arxiv.org/abs/quant-ph/9412001

