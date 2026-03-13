# Protocol Expansion: Current Research and Code Incorporation (2026-02-18)

This note maps recent protocol research to PhotonTrust modeling coverage and benchmark integration.

## What is now benchmarked in code

Benchmark runner:

- `scripts/validation/compare_recent_research_benchmarks.py`

Protocols currently benchmarked:

- `tf_qkd` / `pm_qkd`
- `mdi_qkd`
- `amdi_qkd`
- `bb84_decoy`
- `bbm92` (added in this update)

Current run status (18 cases total):

- median paper-locked relative error: `0.00264468`
- median best-fit relative error: `0.000624053`
- cases <=1% in best-fit: `17/18`

Source: `results/research_validation/recent_research_benchmark_comparison.md`

## Newly added protocol checkpoints

Added benchmark cases:

- `bbm92_200km_440.8bps`
  - Source: https://doi.org/10.1103/PhysRevLett.134.230801
  - arXiv abstract reports 440.80 bit/s at 200 km and max distance 404 km:
    https://arxiv.org/abs/2408.04361
- `bbm92_26km_4.5bps`
  - Source: https://doi.org/10.1038/s41534-025-00991-5
- `bbm92_40km_245bps`
  - Source: https://arxiv.org/abs/2305.18696

Also added recent long-distance TF/PM and AMDI-style points:

- `tf_50km_1.27mbps` (without global phase locking): https://arxiv.org/abs/2212.04311
- `tf_952km_8.75e-12_bpp`, `tf_1002km_9.53e-12_bpp`: https://arxiv.org/abs/2303.15795
- `mdi_413km_590.61bps`, `mdi_508km_42.64bps`: https://doi.org/10.1103/PhysRevLett.130.250801

## Research landscape for other protocol families

### AMDI / Mode-Pairing QKD (not the same as canonical MDI)

Key references:

- Experimental MP/AMDI result (413 km, 508 km): https://doi.org/10.1103/PhysRevLett.130.250801
- Practical AMDI with advantage distillation: https://arxiv.org/abs/2407.03980
- AMDI protocol analysis: https://arxiv.org/abs/2302.14349

Status in code:

- Explicitly modeled as `amdi_qkd`:
  - `photonstrust/qkd_protocols/amdi_qkd.py`
  - protocol aliases wired in `photonstrust/qkd_protocols/registry.py`
  - schema fields wired in `photonstrust/registry/kinds.py`
- AMDI benchmark points now route through `amdi_qkd`.
- Current best-fit errors:
  - `mdi_413km_590.61bps`: `0.00187948`
  - `mdi_508km_42.64bps`: `0.000112049`

### CV-QKD (continuous-variable)

Key references:

- CV-QKD + classical coexistence over 120 km fiber: https://doi.org/10.1103/zy2d-m3ch
- High-rate self-referenced CV-QKD over high-loss free-space: https://arxiv.org/abs/2503.10168
- Free-space CV-QKD under high background noise: https://www.nature.com/articles/s41534-025-01009-w

Status in code:

- No CV protocol surface in current repository.
- Would require a dedicated CV channel/noise/reconciliation model.

### DI-QKD (device-independent)

Key references:

- DI-QKD over 100 km with single atoms (Science 2026): https://arxiv.org/abs/2602.09596
- Long-range photonic DI-QKD proposals: https://arxiv.org/abs/2507.23254

Status in code:

- No DI security model or Bell-violation finite-size engine in current repository.

## What to change next to incorporate these protocols correctly

1. Add `cv_qkd` protocol surface.
   - Include excess-noise model, trusted/untrusted detector assumptions, and CV reconciliation efficiency.

2. Add `di_qkd` protocol surface (later phase).
   - Bell-test statistics, detection-loophole thresholds, entropy-accumulation finite-size accounting.

3. Keep benchmark report split:
   - `paper_locked` for reproducibility.
   - `best_fit` for calibration ceiling.
   - Mark model-family mismatch cases explicitly (e.g., ultrabright BBM92 case where current model remains underfit).
