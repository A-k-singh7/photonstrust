# Physics Models (QuTiP-first, expansion-ready)

This document sets physics-engine priorities for business expansion into:
- photonic chip verification, and
- satellite/space quantum link verification.

## Current baseline (repository reality)
- `photonstrust/physics/emitter.py`: analytic + QuTiP steady-state emitter model.
- `photonstrust/physics/memory.py`: analytic + QuTiP memory decay path.
- `photonstrust/physics/detector.py`: stochastic detector click model.
- `photonstrust/channels/fiber.py`: terrestrial fiber channel assumptions.
- OrbitVerify mission v0.1 foundations:
  - `photonstrust/channels/free_space.py`: decomposed free-space efficiency model.
  - `photonstrust/orbit/pass_envelope.py`: pass-envelope execution (time-segmented samples + summaries).
- ChipVerify PIC v0.1 foundations:
  - `photonstrust/components/pic/library.py`: minimal PIC component models (forward matrices).
  - `photonstrust/pic/simulate.py`: PIC netlist simulation (chain + feed-forward DAG).
  - `photonstrust/components/pic/touchstone.py`: Touchstone (S2P) compact model import (2-port).

The architecture is solid, but model scope is still MVP-level for foundry-grade
verification and space mission engineering decisions.

## Priority roadmap for the physics engine

## P0 (0-12 weeks): minimum viable technical credibility

## 1. Emitter-cavity realism
- Keep Jaynes-Cummings baseline.
- Add pulse-resolved transient solver path (not only steady-state summaries).
- Emit additional diagnostics:
  - linewidth proxy,
  - spectral purity,
  - mode-mismatch sensitivity.

## 2. Detector realism
- Extend to gated detector mode (windowed detection).
- Add saturation and count-rate rolloff behavior.
- Replace simple afterpulse injection with a stateful afterpulse/dead-time model.

## 3. Memory uncertainty quality
- Separate decoherence contributors in outputs:
  - amplitude damping term,
  - dephasing term.
- Publish diagnostics used to trust calibration:
  - effective sample size,
  - R-hat,
  - posterior predictive check status.

## 4. Free-space/satellite channel model
- Add free-space module alongside fiber:
  - geometric/pointing loss,
  - atmospheric transmission/elevation dependence,
  - turbulence proxy,
  - background daylight/noise conditions.

## 5. Fiber QKD deployment realism pack (deny-resistant demos)
Add the minimum set of terms that make fiber QKD outputs credible in realistic
telecom environments and review boards:
- QKD + classical traffic coexistence noise (Raman + background) with a
  calibration-friendly parameterization.
- Explicit misalignment / visibility term that sets the short-distance QBER
  floor (prevents "too-perfect at 0 km" skepticism).
- Optional finite-key penalty mode (non-asymptotic correction).
- Source spectral/indistinguishability proxy hooks that can degrade fidelity
  and propagate into QBER/error budget.

Implementation spec:
- `deep_dive/16_qkd_deployment_realism_pack.md`

## P1 (3-6 months): component-level verification expansion
- Build on the implemented v0.1 PIC execution path by adding higher-fidelity
  compact models and import surfaces:
  - ring resonator transfer functions (wavelength dependence; coupling/Q),
  - MZI and mesh blocks (as macro components + calibration hooks),
  - S-parameter / Touchstone import for black-box foundry/EDA models,
  - polarization and wavelength sweep semantics,
  - explicit validity ranges and uncertainty tags for imported models.
- Introduce parameter schemas and invariants per component class.
- Support batch component sweeps with cached outputs.

## P2 (6-12 months): interactive scale and certification quality
- Surrogate-model acceleration for drag-drop interactive loops.
- Multi-fidelity execution modes:
  - preview mode (fast, approximate),
  - certification mode (full fidelity + diagnostics gates).
- Signed/reproducible model bundles for external audits.

## Validation and acceptance gates

## Determinism and replay
- Fixed `seed` + config hash must reproduce outputs within defined tolerance.

## Physics consistency
- Monotonicity and boundedness checks for every output metric.
- Cross-check against at least one external reference curve per model family.

## Calibration quality
- No external report without passing diagnostics thresholds.
- Every external card must contain calibration diagnostics status.

## Runtime practicality
- Interactive preview: p95 under 5 seconds for common topologies.
- Full-fidelity runs: bounded envelopes per scenario class.

## References for tool cadence and model strategy
- QuTiP releases/download: https://qutip.org/download.html
- Qiskit release notes (2.x line example, 2.3.0):
  https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.3
- `12_web_research_update_2026-02-12.md`
- `13_business_expansion_and_build_plan_2026-02-12.md`
- `deep_dive/16_qkd_deployment_realism_pack.md`
