# Phase 43: MDI-QKD + TF/PM-QKD Protocol Surfaces (Implementation Plan)

Date: 2026-02-14

## Scope

Deliver a protocol-family dispatch layer for QKD runs, and implement the
published analytical key-rate models for MDI-QKD and TF/PM-QKD (PM-QKD model,
with TF-QKD exposed as a protocol alias/variant).

In-scope:

- Extend config / registry surfaces so `protocol.name` can be one of:
  - `BBM92` (existing)
  - `MDI_QKD` (new)
  - `TF_QKD` (new)
  - `PM_QKD` (new)
- Add a QKD protocol dispatcher so key-rate computation is selected by protocol.
- Update sanity gates so PLOB is only enforced for direct-link families.
- Ensure Reliability Cards capture protocol family and relay assumptions.
- Implement analytical models anchored to primary sources:
  - MDI-QKD: Xu et al. (arXiv:1305.6965) Eq. (1), Table 2 (two-decoy bounds), Appendix B (system model)
  - PM-QKD: Ma et al. (arXiv:1805.05538) Eq. (1)-(4), Appendix B.2 (simulation formulas)

Out-of-scope (for this phase unless explicitly pulled in):

- Protocol optimization loops (auto-tuning intensities/probabilities across distance).
- Multi-node network simulation and routing.
- Any claim of composable security beyond what is explicitly implemented.

## Work items

### 1) Protocol registry + config validation surface

Update:

- `photonstrust/photonstrust/registry/kinds.py`
  - expand `qkd.protocol.name` enum to include new protocol families.

Optional (if we expose coherent-pulse parameters in the UI registry):

- `photonstrust/photonstrust/registry/kinds.py`
  - extend `qkd.source.type` to include `wcp` (weak coherent pulse)

Acceptance:

- Config validation still passes for existing configs.
- New configs with `protocol.name: MDI_QKD` etc. validate and are serialized into artifacts.

### 2) QKD protocol dispatch layer

Add:

- `photonstrust/photonstrust/qkd_protocols/` (new package)
  - `mdi_qkd.py` (MDI-QKD analytical model)
  - `pm_qkd.py` (PM-QKD analytical model; TF-QKD alias supported)
  - `common.py` helpers (relay split, parameter parsing, sanity checks)

Update:

- `photonstrust/photonstrust/qkd.py`
  - keep public API stable (`compute_point`, `compute_sweep`), but dispatch
    based on `scenario["protocol"]["name"]`.

Update (if needed for new source types):

- `photonstrust/photonstrust/config.py` (source defaults)
- `photonstrust/photonstrust/validation.py` (protocol-specific validation)

Acceptance:

- Existing tests continue to pass for BBM92 scenarios.
- New unit tests cover protocol dispatch selection.
- New unit tests cover basic PM-QKD and MDI-QKD invariants (finite/non-negative key rate, monotonic vs distance under symmetric settings).

### 3) Update PLOB sanity gate scoping

Update:

- `photonstrust/tests/test_qkd_plob_bound.py`
  - explicitly set `protocol.name: BBM92` in the scenario used by the test.
  - gate only applies to direct-link protocol families.

Add:

- `photonstrust/tests/test_qkd_relay_protocol_sanity.py`
  - monotonicity vs. distance/loss
  - non-negative key rate
  - basic boundedness vs. trivial upper limits (e.g., <= rep_rate_hz)

Acceptance:

- `py -m pytest` passes.

### 4) Reliability card provenance + notes updates

Update:

- `photonstrust/photonstrust/report.py`
  - ensure protocol family and any relay-related assumptions appear in v1.0 and
    v1.1 cards.
  - add a scope note for relay-based analytical models (assumptions + required stabilization fields).

Acceptance:

- Cards for new protocol families validate against `schemas/photonstrust.reliability_card.v1.schema.json` (v1.0)
  and `schemas/photonstrust.reliability_card.v1_1.schema.json` (v1.1) when opted-in.

Recommendation:

- Default relay-based protocols to Reliability Card v1.1 when no explicit `scenario.reliability_card_version` is set,
  since v1.0 schema constrains `inputs.source.type`.

## Validation

- `py -m pytest`

Optional spot checks:

- `photonstrust run <new_config>.yml --output results/protocol_surface_<name>`
