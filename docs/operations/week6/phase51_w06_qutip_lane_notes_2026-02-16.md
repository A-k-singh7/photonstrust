# Phase 51 W06 Operations Notes (QuTiP Narrow Target Lane)

Date: 2026-02-16

## Week focus

Add a single high-value QuTiP backend target (emitter) with explicit
applicability/provenance reporting while preserving optional/non-blocking
fallback posture.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P51-R6 | QuTiP lane introduces hard dependency in default runtime path | TL | Medium | High | Kept QuTiP lane isolated in `qutip_backend.py` and optional resolver routing | Core tests fail when QuTiP absent | Mitigated |
| P51-R7 | Missing QuTiP dependency path becomes opaque to operators | QA | Medium | Medium | Added applicability status/reasons and provenance fields (`qutip_available`, `qutip_version`) | Applicability test fails for missing dependency case | Mitigated |
| P51-R8 | Fallback behavior drifts without tests | SIM | Medium | High | Added explicit fallback tests in `tests/test_qutip_backend_interface.py` | Forced QuTiP failure test does not report fallback metadata | Mitigated |
| P51-R9 | Team over-interprets parity lane as release gate despite instability | DOC | Medium | High | Validation report records `recommendation.decision=no-go` and keeps lane non-blocking | Any attempt to require QuTiP in mandatory CI | Mitigated |
| P51-R10 | Solver warnings in parity lane mask hard failures | QA | Low | Medium | Keep command-output evidence in validation report and retain full regression gate (`pytest -q`) | Parity run ends without artifact output files | Mitigated |

## Owner map confirmation

QuTiP lane implementation, fallback policy, parity evidence, and regression-gate
streams remain explicitly owned with no accountable/responsible gaps.
