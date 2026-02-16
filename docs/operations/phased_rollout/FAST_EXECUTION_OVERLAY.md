# Fast Execution Overlay (v1 -> v3) Mapped to Strict Phases

Date: 2026-02-14

This file is the operational bridge between:

- Fast plan: `../../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`
- Strict rollout protocol: this folder (`docs/operations/phased_rollout/`)

Goal: make the "fast path" executable without breaking the discipline:

1. Research brief
2. Implementation plan
3. Build log
4. Validation report
5. Downstream documentation updates

## Version Meaning (Local Definitions)

- v1: Trustable open core (determinism, schemas, gates, reproducibility artifacts)
- v2: Performance DRC + control surface (PIC workflow decisions, denial-resistant demo loop)
- v3: Photonic design control plane (inverse design primitives, PDK hooks, EDA interop seams, data flywheel)

Canonical reference for these definitions:

- `../../research/deep_dive/21_v1_to_v3_fast_execution_plan.md`

## High-Level Mapping (What Is Already Real in This Repo)

| Target | What it means in this repo | Phases that implement it | Acceptance (evidence) |
|--------|-----------------------------|--------------------------|-----------------------|
| v1 | Trustable engine + artifacts | Phase 01-22 | deterministic runs; schema validation; run registry + diffs + approvals |
| v2 | Performance DRC wedge | Phase 23-29 | layout features + crosstalk checks; API/web surfaces; replayable evidence bundles |
| v3 | Control plane primitives | Phase 30-39 | KLayout artifact pack; workflow chaining; attestation schemas; config validation; physics sanity gates |

## Capability-Level Mapping (Track View)

### Managed workflow surface (author -> run -> diff -> approve)

- Implemented phases: 13, 19, 20, 21, 22
- Acceptance signals:
  - Runs can be served and diffed (inputs and outputs summary scopes)
  - Approvals are append-only and tied to a project registry
  - Evidence bundles can be exported and replayed deterministically (Phases 35-36)

### PIC verification chain (layout -> LVS-lite -> KLayout pack -> SPICE export)

- Implemented phases: 27, 28, 29, 30, 31, 32, 34, 37
- Acceptance signals:
  - `layout.gds` emitted when `gdstk` is installed (Phase 37)
  - KLayout macro templates run in batch mode and produce an artifact pack (Phase 30-32)
  - LVS-lite mismatches are surfaced as structured diagnostics (Phase 27/34)
  - SPICE export artifacts exist and are deterministic (Phase 28/34)

### Evidence packs (replayable, reviewable artifacts)

- Implemented phases: 35, 36
- Acceptance signals:
  - Evidence bundle zip can be exported for a root workflow and its children
  - Bundle manifest and workflow report are schema-validated

### Physics-core "trust gates" (sanity bounds + deterministic uncertainty)

- Implemented phases: 38, 39
- Acceptance signals:
  - Scenario validation is fail-fast and has `--validate-only` CLI mode (Phase 38)
  - PLOB sanity test gate exists (`tests/test_qkd_plob_bound.py`) (Phase 39)
  - QKD uncertainty is seed-controlled (`uncertainty.seed` / `scenario.seed`) (Phase 39)
  - Free-space airmass uses Kasten & Young (1989) and warns at low elevation (Phase 39)

## What Still Blocks "Dominating Trust"

These are not "missing features". They are missing *trust closure* for external scrutiny.

| Blocker | Why it matters | Where it is specified | Proposed next phase |
|---------|----------------|-----------------------|---------------------|
| Evidence bundle publishing + signing | makes artifacts tamper-evident outside the repo | `../../audit/08_reliability_card_v1_1.md` and supply chain anchors | Phase 40 (Complete) |
| QKD deployment realism pack | prevents over-claiming for deployed fiber (coexistence, finite-key regimes) | `../../research/deep_dive/16_qkd_deployment_realism_pack.md` | Phase 41 (Complete) |
| Reliability card v1.1 | standardizes evidence tiering and operating envelope fields | `../../audit/08_reliability_card_v1_1.md` and `../../research/deep_dive/06_reliability_card_v1_1_draft.md` | Phase 42 (Complete) |
| Protocol expansion (MDI / TF / PM) | makes the platform relevant to modern QKD research directions | `../../audit/10_competitive_positioning.md` | Phase 43 (Complete) |
| QKD fidelity foundations (noise/dead-time/polarization) | removes unphysical probability/saturation semantics and aligns relay/direct models | internal phase backlog | Phase 44 (Complete) |
| Raman coexistence realism (effective-length) | replaces linear Raman scaling with attenuation-aware effective length; improves deployment realism | `../../research/deep_dive/16_qkd_deployment_realism_pack.md` | Phase 45 (Complete) |
| BBM92 coincidence model | replaces additive QBER proxy with coincidence-based multi-pair + noise accounting | `../../research/deep_dive/16_qkd_deployment_realism_pack.md` | Phase 46 (Complete) |

## Proposed Next Phases (Draft, Concrete)

### Phase 40: Evidence bundle publish + signing (project approvals integration)

Acceptance tests (target):

- Evidence bundle contains hashes for all artifacts and a detached signature file.
- A verification command exists that fails if any artifact is modified post-export.
- Approval events can reference a signed bundle hash.

Status:

- Completed in `phase_40_evidence_bundle_signing/`.

### Phase 41: QKD deployment realism pack (fiber)

Acceptance tests (completed):

- Canonical configs exist in `configs/canonical/` for key deployed regimes (metro, long-haul, coexistence).
- Key-rate outputs have literature-anchored trend gates (e.g., coexistence Raman power monotonicity).
- Finite-key toggles have explicit applicability bounds surfaced in cards.

Implementation:
- `phase_41_qkd_deployment_realism_pack/`

### Phase 42: Reliability card v1.1 (evidence tiers + operating envelope + standards anchors)

Acceptance tests (completed):

- `schemas/photonstrust.reliability_card.v1_1.schema.json` exists and is enforced by tests.
- Cards include provenance, evidence quality, and operating envelope fields consistently when `scenario.reliability_card_version: 1.1`.

### Phase 43: MDI-QKD and TF/PM-QKD model surfaces

Acceptance tests (target):

- Protocol selection is explicit in config and in artifacts.
- PLOB sanity gate is updated to avoid false positives for protocols that can exceed direct-link scaling.

Status:

- Completed in `phase_43_mdi_tf_pm_qkd_protocol_surfaces/`.

### Phase 44: QKD fidelity foundations

Acceptance tests (completed):

- Direct-link noise mapping uses Poisson arrivals and remains bounded.
- Dead-time saturation uses non-paralyzable default and is shared across protocol families.
- Fiber polarization coherence length is treated as visibility/misalignment (QBER) rather than attenuation.

Implementation:

- `phase_44_qkd_fidelity_foundations/`

### Phase 45: Raman coexistence effective-length model

Acceptance tests (completed):

- Effective-length model reduces to linear scaling when alpha -> 0.
- Under loss, Raman noise grows sublinearly with distance.
- Co- vs counter-propagation yields different received Raman counts.

Implementation:

- `phase_45_raman_coexistence_effective_length/`

### Phase 46: BBM92 coincidence model

Acceptance tests (completed):

- SPDC direct-link model uses explicit coincidence gain Q and accidentals Q_acc.
- Noise-only coincidences scale as (1-exp(-b))^2 (two-sided coincidence).
- QBER is computed as a true/accidental mixture rather than a linear sum of independent terms.

Implementation:

- `phase_46_bbm92_coincidence_model/`
