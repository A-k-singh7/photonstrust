# Research Brief

## Metadata
- Work item ID: PT-PHASE-02
- Title: Stateful detector model (gating, saturation, afterpulse/dead-time coupling)
- Authors: PhotonTrust core team
- Date: 2026-02-12
- Related modules: `photonstrust/physics/detector.py`, detector schema fields, QKD stochastic path

## 1. Problem and motivation
Detector behavior strongly drives trust in QBER and key-rate predictions. The
existing detector model was stochastic but largely memoryless and did not expose
gating and saturation behavior, limiting realism for high-rate and
mission-like operating conditions.

## 2. Research questions and hypotheses
- RQ1: Can stateful detector logic be added without breaking existing API
  behavior and tests?
- RQ2: Do gating and saturation controls produce physically expected monotonic
  behavior under controlled scenarios?
- H1: Introducing gating with fixed period/width should reduce processed events
  and effective duty cycle.
- H2: Introducing finite saturation count rate should reduce effective PDE and
  click yield relative to unsaturated settings.

## 3. Related work and baseline methods
Operational detector behavior in QKD systems is sensitive to dead time,
afterpulsing, and rate effects. Engineering practice and literature on APD/SNSPD
operation motivate stateful models over independent Bernoulli clicks when
designing robust verification stacks.

## 4. Mathematical formulation
Signal detection remains probabilistic with PDE but uses a saturation-adjusted
effective PDE:
`pde_eff = pde / (1 + signal_rate / saturation_rate)` when a saturation limit
is configured.
Event processing uses a temporal state machine with dead-time suppression and
afterpulse generation.

## 5. Method design
A heap-based event queue was used to process signal and dark events in temporal
order. Dead-time filtering and afterpulse generation are applied in the same
stateful loop. Optional gate constraints are applied to arrivals before event
generation. Diagnostics include effective PDE, duty cycle, and processed-event
counts.

## 6. Experimental design
Controls:
- gating enabled vs disabled with all else fixed,
- saturation enabled vs disabled at high event rates,
- afterpulse + dead-time boundedness checks.
Metrics:
- `p_click`, `p_false`, `pde_effective`, `events_processed`, `duty_cycle`.

## 7. Risk and failure analysis
Risk: stateful logic could alter baseline behavior and break reproducibility.
Mitigation: preserve defaults for old configs, keep seed-based determinism, and
run existing detector invariant tests plus new stateful tests.

## 8. Reproducibility package
- deterministic seeds in all detector tests.
- backward compatibility validated by existing tests.
- new tests in `tests/test_detector_stateful.py`.

## 9. Acceptance criteria
- Existing detector tests continue to pass.
- New stateful tests confirm expected monotonic trends.
- Config and reliability schemas allow new optional detector fields.
- Full test suite passes.

## 10. Decision
- Decision: Proceeded and completed.
- Reviewer sign-off: Internal (2026-02-12).

## Sources
- High-performance photon-number-resolving SNSPD preprint (2025):
  https://arxiv.org/abs/2504.02202
- NIST SNSPD overview (device operation context):
  https://www.nist.gov/programs-projects/superconducting-nanowire-single-photon-detectors
- Detector timing jitter and count-rate considerations (Nature, 2022):
  https://www.nature.com/articles/s41586-022-04766-6
