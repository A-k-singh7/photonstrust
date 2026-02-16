# Physics Engine Extension Plan (Multi-Fidelity + QuTiP/Qiskit)

Date: 2026-02-14

This document is the "scientist-grade" plan for extending PhotonTrust physics
without turning the project into an unmaintainable solver zoo.

Core idea:
- keep a fast analytic engine for iteration and product UX
- add higher-fidelity backends (QuTiP/Qiskit/external) as *optional* cross-checks
- treat multi-fidelity agreement as a trust gate and an evidence artifact

---

## 0) Why This Matters (Competitor Reality)

Competitors can beat you on solver depth, because they:
- have years of development
- have proprietary solvers and foundry partnerships

You can beat them on *trust closure* by:
- making results reproducible, bounded, and cross-validated
- producing evidence bundles that survive review

Multi-fidelity triangulation is how you "sound like a scientist" in product form:
you do not claim one model is truth; you show consistent conclusions across models.

---

## 1) Current Physics Layout in the Repo (Anchor)

Today:
- `photonstrust/physics/detector.py`
- `photonstrust/physics/emitter.py`
- `photonstrust/physics/memory.py`
- QKD model: `photonstrust/qkd.py` (analytic + stochastic detector option)

Immediate opportunity:
- formalize a backend interface so "physics upgrades" do not break the product surface.

---

## 2) Multi-Fidelity Ladder (Default Product Behavior)

Define three fidelity tiers across all domains (QKD, PIC, orbit/free-space):

Tier 0: Analytic (fast, explainable)
- used by default in UI sliders and preview runs
- bounded applicability (explicit range labels)

Tier 1: Stochastic / semi-empirical (calibration-friendly)
- Monte Carlo sampling for uncertainty
- variance reduction methods as needed
- supports fitting against measurement bundles

Tier 2: High-fidelity quantum / field solvers (cross-check and certification mode)
- QuTiP for open quantum system dynamics
- Qiskit for circuit-level representations of entanglement + repeater primitives
- optional external EM solvers for PIC component cross-checks

Key product rule:
- Tier 2 is optional and used as a trust amplifier, not the default runtime path.

---

## 3) Backend Interface (How We Keep It Maintainable)

### 3.1 Core API shape

Add a backend layer:
- `photonstrust/physics/backends/`
  - `base.py`
  - `analytic.py`
  - `stochastic.py`
  - `qutip_backend.py` (optional dependency group)
  - `qiskit_backend.py` (optional dependency group)

Base interface (conceptual):
- `simulate(component_or_protocol, inputs, *, seed, mode) -> outputs`
- `applicability(inputs) -> {status: pass/warn/fail, reasons: [...]}` (mandatory)
- `provenance() -> {backend_name, version, config_hash, ...}` (mandatory)

### 3.2 Determinism requirements

Each backend MUST:
- accept an explicit seed
- never use global RNG state
- record the seed and dependency versions in evidence

This is already trending in the codebase:
- QKD uncertainty now threads a seed deterministically (Phase 39)

---

## 4) Where QuTiP Helps (High-Value, Not Everywhere)

QuTiP is valuable when you need:
- density-matrix or quantum trajectory modeling
- open-system decoherence and measurement modeling
- explicit time dynamics rather than static algebra

Concrete PhotonTrust use cases (good ROI):

1) Entanglement source realism models
- model indistinguishability, dephasing, multi-photon contamination as a state evolution
- output: effective visibility / error terms that feed analytic QKD formulas

2) Memory models (quantum repeaters)
- decoherence vs storage time
- fidelity decay curves that become parameters in the higher-level network models

3) Detector "physics backend" beyond toy afterpulsing
- afterpulsing and dead-time as a stochastic process with memory
- jitter as a timing distribution feeding coincidence-window logic

Implementation principle:
- do not replace analytic models with QuTiP everywhere
- use QuTiP to generate/validate parameterizations and to provide evidence in certification mode

Source:
- QuTiP project site and release listing: https://qutip.org/download.html

---

## 5) Where Qiskit Helps (Specific, Focused)

Qiskit is valuable when you need:
- circuit-level representation of entanglement distribution steps
- stabilizer / Clifford simulation for QEC-coded repeater primitives
- a standardized way to express operations and noise channels at the circuit level

Concrete PhotonTrust use cases (good ROI):

1) Repeater primitive verification
- entanglement swapping + purification circuits expressed as circuit templates
- use Qiskit to simulate ideal vs noisy behavior and derive effective fidelity curves

2) Cross-check of simplified protocol models
- for small instances, compare analytic predictions with circuit simulation outputs

3) Education-grade artifacts
- export circuits (QASM / diagrams) alongside reliability cards for transparency

Important constraint:
- QKD protocol performance modeling is not "a circuit problem" end-to-end.
  Use Qiskit for the parts that are naturally circuits (repeaters/QEC), not for the whole link.

Source:
- Qiskit SDK release notes (IBM Quantum docs): https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.2

---

## 6) Cross-Fidelity Trust Gates (How We Become "Most Trustable")

Add "triangulation tests" for canonical scenarios:

Example: entanglement-based link
- Analytic model predicts QBER_total and key_rate
- QuTiP backend predicts effective fidelity under specified dephasing parameters
- The two must agree within a declared tolerance in a validated envelope

Example: repeater primitive
- simplified repeater math predicts fidelity after swapping + decoherence
- Qiskit circuit simulation yields a fidelity estimate
- require agreement (or require the result to be labeled "preview only")

Outputs:
- add to evidence bundles:
  - `multifidelity_report.json` summarizing the comparison
  - tool versions, seeds, tolerances, pass/fail

This is a defensible claim in review:
"We do not rely on a single model; we require cross-model agreement for certified claims."

---

## 7) Dependency and Licensing Strategy (Open-Core + Industry)

QuTiP and Qiskit integration should be:
- optional dependency groups (do not force-install heavy stacks)
- isolated so core remains fast and minimal

Recommended packaging:
- `photonstrust[quantum]` -> installs QuTiP + Qiskit extras
- core CI runs without them; optional CI job runs with them

Do NOT embed copyleft EM solvers into the commercial core.
If needed:
- keep them behind a plugin runner boundary (separate process/container)

(Not legal advice; treat as architecture guidance.)

---

## 8) Implementation Slices (Buildable Next Steps)

### Slice 1: Backend scaffolding + optional deps
- add backend interface
- add stub implementations
- add schema for multifidelity report artifact
- add tests that validate:
  - determinism
  - applicability flags required

### Slice 2: QuTiP backend for a single, narrow target
Pick one:
- memory decoherence curve generator
- entanglement source visibility model

Deliver:
- `photonstrust/physics/backends/qutip_backend.py`
- unit tests for consistency and determinism

### Slice 3: Qiskit backend for repeater primitives (small circuits)
Deliver:
- `photonstrust/protocols/circuits/` circuit templates
- `photonstrust/physics/backends/qiskit_backend.py`
- test(s) comparing simplified formulas to Qiskit results in small regimes

### Slice 4: Evidence integration
- include multi-fidelity report in evidence bundle export (Phases 35-36 compatible)
- display multi-fidelity pass/fail in UI trust panel

---

## 9) Acceptance Criteria (Definition of Done)

For QuTiP/Qiskit integration to be "trust-grade":

1) Optional installation works
- core install stays lightweight
- `photonstrust[quantum]` enables high-fidelity runs

2) Determinism
- fixed seed -> identical outputs across runs (within numerical tolerance)

3) Cross-fidelity gating
- canonical scenarios have triangulation tests in CI

4) Clear applicability bounds
- high-fidelity results label domain, parameter ranges, and limitations

5) Evidence artifacts
- multi-fidelity report is exported, schema-validated, and replayable

---

## Source Index (Web-validated, 2026-02-14)

- QuTiP: https://qutip.org/download.html
- Qiskit release notes (2.2): https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.2

