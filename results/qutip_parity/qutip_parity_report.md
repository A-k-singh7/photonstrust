# QuTiP parity lane report

- Generated: 2026-02-16T10:36:19.873513+00:00
- Python: 3.12.10
- QuTiP available: True
- QuTiP version: 5.2.2
- Strict mode: False

## Threshold breaches
- emitter.g2_0 (abs): observed=0.983229, limit=0.1 — Large g2 drift materially changes multi-photon probability.
- memory.fidelity (abs): observed=0.5, limit=0.05 — Memory fidelity parity should be within 5 percentage points.
- qkd.qber_total (abs): observed=0.185942, limit=0.05 — QBER drift beyond 5 points is protocol-significant.
- qkd.key_rate_bps (rel): observed=1, limit=0.5 — Key-rate parity should be within 50% for this focused smoke lane.

## Focused deltas (max by metric)
- emitter
  - emission_prob: abs=0.132938, rel=0.154078
  - g2_0: abs=0.983229, rel=58.6281
  - p_multi: abs=0.483506, rel=29.3141
- memory
  - p_retrieve: abs=0, rel=0
  - fidelity: abs=0.5, rel=1
  - variance_fidelity: abs=0.000258445, rel=n/a
- qkd
  - key_rate_bps: abs=29551.8, rel=1
  - qber_total: abs=0.185942, rel=10.0237
  - entanglement_rate_hz: abs=106897, rel=1.35279
  - p_pair: abs=0.000338211, rel=0.462926

## Recommendation
- Decision: **NO-GO**
- Rationale: Focused parity lane shows material analytic-vs-QuTiP deltas and/or fallback behavior. Keep QuTiP lane optional until model alignment improves.
