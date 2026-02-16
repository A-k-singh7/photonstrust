# Phase 51 W06 Fallback Policy Notes (QuTiP Lane)

Date: 2026-02-16

## Policy intent

The QuTiP lane is a trust-amplifier lane, not a mandatory default-runtime gate.
When QuTiP is unavailable or backend execution fails, runtime behavior remains
non-breaking by falling back to analytic paths while preserving explicit
fallback metadata.

## Implemented policy

- `QutipBackend.applicability("emitter", ...)` returns:
  - `pass` when QuTiP is available,
  - `fail` with install guidance when QuTiP is unavailable.
- `QutipBackend.simulate("emitter", ...)` routes through `get_emitter_stats`
  with `physics_backend="qutip"`; emitter-level fallback remains explicit via:
  - `backend_requested="qutip"`
  - `backend="analytic"` (on fallback)
  - `fallback_reason` populated
- QuTiP lane recommendation remains policy-authoritative from parity artifacts:
  - current decision: `no-go`
  - `require_qutip_in_ci=false`

## Operational implications

- Mandatory CI remains anchored on core regression gates.
- QuTiP parity lane continues as optional/non-blocking evidence lane until
  analytic-vs-QuTiP parity thresholds are met.
- Escalation to blocking CI requires an explicit policy change in phase docs and
  gate criteria update.
