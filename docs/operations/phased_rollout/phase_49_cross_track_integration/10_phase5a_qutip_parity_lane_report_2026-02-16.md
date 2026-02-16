# Phase 5A — Optional QuTiP Parity Lane (2026-02-16)

## What was implemented

1. **Optional parity runner script**
   - Added `scripts/run_qutip_parity_lane.py`.
   - Default mode is **non-breaking** (always exits 0, reports findings).
   - `--strict` mode fails when QuTiP is missing or parity thresholds are breached.
   - Writes artifacts to `results/qutip_parity/`:
     - `qutip_parity_report.json`
     - `qutip_parity_report.md`

2. **Install + usage docs**
   - Updated `README.md` with an "Optional QuTiP parity lane (non-blocking)" section:
     - `pip install -e .[dev,qutip]`
     - `python scripts/run_qutip_parity_lane.py`

3. **Optional CI lane (manual trigger, non-blocking)**
   - Added `.github/workflows/qutip-parity-optional.yml`.
   - Trigger: `workflow_dispatch`.
   - Job is `continue-on-error: true` and runs parity in `--strict` mode.
   - Uploads `results/qutip_parity/` as an artifact.

---

## Focused parity comparison executed

**Environment used:**
- Python 3.12.3
- QuTiP 5.2.3

**Run command:**
```bash
./.venv/bin/python scripts/run_qutip_parity_lane.py
```

**Coverage set:**
- Emitter: `steady_state`, `transient`
- Memory: wait times `1e3`, `1e6`, `1e9` ns
- End-to-end BBM92 point checks at distances `10`, `25`, `50` km

**Observed max deltas (analytic vs qutip):**
- **Emitter**
  - `g2_0`: abs delta **0.983**
  - `p_multi`: abs delta **0.484**
  - `emission_prob`: rel delta **15.4%**
- **Memory**
  - `fidelity`: abs delta **0.500** (largest at `1e9 ns`)
  - `p_retrieve`: abs delta **0.0**
- **QKD (BBM92)**
  - `qber_total`: abs delta **0.186**
  - `key_rate_bps`: rel delta **1.0** (qutip path produced 0 bps in this focused set)

**Fallback status:**
- No runtime fallback to analytic was observed in this run (QuTiP backend was active).

---

## Recommendation (go/no-go)

**Decision: NO-GO for requiring QuTiP in mandatory CI right now.**

Rationale:
- Focused parity lane shows material backend deltas in emitter (`g2_0`), long-wait memory fidelity, and downstream BBM92 KPI impact (QBER/key-rate).
- Making QuTiP required in core CI today would likely create noisy/failing gates without backend-alignment closure.

**Keep QuTiP lane optional and non-blocking** until parity criteria are tightened and model alignment work is completed.
