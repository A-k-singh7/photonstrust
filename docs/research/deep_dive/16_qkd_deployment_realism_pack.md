# QKD Deployment Realism Pack (Fiber)

This document is an implementation-grade spec for making PhotonTrust's
fiber-based QKD outputs credible under real deployment constraints.

It focuses on the highest-leverage realism gaps for decision-grade demos:

1. QKD + classical data coexistence noise (spontaneous Raman + background)
2. Explicit misalignment / visibility QBER floor
3. Finite-key effects (non-asymptotic security penalty)
4. Source spectral/indistinguishability proxies that propagate to fidelity
5. Detector statefulness hooks (gating/saturation/afterpulsing) in the QKD path

PhotonTrust currently produces consistent and reproducible metrics, but the
absence of these terms makes it too easy for a skeptical reviewer to dismiss
results as "lab-only" or "asymptotic-only".

---

## 1) Scope

In scope (v1):
- Protocol family: entanglement-based QKD model used by `photonstrust/qkd.py`
  (current configs use `protocol.name: BBM92`).
- Channel: fiber (existing `photonstrust/channels/fiber.py`).
- Outputs:
  - key rate and QBER remain the primary decision outputs,
  - Reliability Card includes a decomposed error budget and uncertainty fields.

Out of scope (v1):
- Full end-to-end composable security proofs for every protocol variant.
- Full WCP BB84 + decoy-state machinery (can be Phase 2 once a prepare-and-measure
  protocol is added).

---

## 2) Reality Gaps in the Current Model

Current `photonstrust/qkd.py` QBER contributors are dominated by:
- multiphoton contribution proxy (`q_multi`),
- detector noise (`q_dark` via dark-counts + afterpulsing),
- timing-window effects (`q_timing`).

Missing terms that matter in deployed fiber:
- Raman-scattered noise induced by co-propagating classical traffic,
- a non-zero QBER floor from imperfect alignment/visibility even at short ranges,
- finite-key penalties that can dominate when blocks are not enormous,
- source spectral quality proxies that map to practical interference/visibility.

---

## 3) Proposed Config Extensions (Backward Compatible)

All fields below are optional. If omitted, behavior should match current output.

### 3.1 Channel coexistence noise (Raman + classical traffic)

Add under `channel`:

```yaml
channel:
  coexistence:
    enabled: false
    classical_launch_power_dbm: 0.0
    classical_channel_count: 1
    direction: co  # co|counter
    filter_bandwidth_nm: 0.2
    raman_coeff_cps_per_km_per_mw_per_nm: 0.0
    raman_spectral_factor: 1.0
```

Notes:
- `raman_coeff_cps_per_km_per_mw_per_nm` is intentionally a calibration-friendly
  scalar (can be inferred from a single lab measurement sweep).
- If you want a simpler surface first, collapse this entire block into a single
  `channel.background_counts_cps` and move detailed coexistence to v2.

### 3.2 Background counts (ambient + leakage)

Add under `detector`:

```yaml
detector:
  background_counts_cps: 0.0
```

### 3.3 Misalignment / visibility floor

Add under `protocol`:

```yaml
protocol:
  misalignment_prob: 0.0  # [0, 0.5]
  optical_visibility: null  # optional alternative to misalignment_prob
```

Interpretation:
- If `optical_visibility` is provided, use `q_mis = (1 - visibility) / 2`.
- Else use `q_mis = misalignment_prob`.

### 3.4 Finite-key

Add new top-level block:

```yaml
finite_key:
  enabled: false
  signals_per_block: 1.0e10
  security_epsilon: 1.0e-10
  parameter_estimation_fraction: 0.1
```

Interpretation:
- When enabled, the secret fraction must be reduced relative to the asymptotic
  expression in a way that is monotonic in:
  - smaller `signals_per_block` -> lower key rate,
  - smaller `security_epsilon` (stricter) -> lower key rate,
  - higher QBER -> lower key rate.

### 3.5 Source spectral/indistinguishability proxies

Add under `source`:

```yaml
source:
  hom_visibility: null  # [0, 1], optional
  indistinguishability: null  # [0, 1], optional alias (pick one)
```

Interpretation:
- Use this to degrade fidelity or add an explicit `q_source` term that rolls into
  total QBER.

---

## 4) Model Formulation (Pragmatic, Calibration-Friendly)

### 4.1 Noise counts: dark + background + Raman

Define a total noise count rate (counts per second):

`noise_counts_cps = dark_counts_cps + background_counts_cps + raman_counts_cps`

Compute:
- `dark_counts_cps` from detector presets (existing),
- `background_counts_cps` from config (new),
- `raman_counts_cps` from coexistence model (new).

Convert to coincidence-window false-click probability using Poisson arrivals:

`p_noise = 1 - exp(-noise_counts_cps * window_s)`

Then use `p_noise` in place of `p_dark` in the current code path.

Raman model (current):

Raman is modeled with an attenuation-aware effective interaction length (integral
closed form), so received Raman counts do not grow unbounded linearly with link
distance.

Where:
- `P_mW = 10 ** (P_dbm / 10)`
- `direction_factor` is a simple constant (e.g., 1.0 for co-prop, 1.5 for counter)
  until a more detailed model is justified.

This is intentionally not "physics-perfect"; the goal is a single parameter that
can be calibrated and that drives the correct directionality in outputs.

### 4.2 Misalignment / visibility term

Define:
- `q_mis = misalignment_prob` or `(1 - visibility)/2`
- clamp to `[0, 0.5]`.

Then:

`q_total = clamp(q_multi + q_dark + q_timing + q_mis + q_source, 0, 0.5)`

Where `q_source` is optional (from HOM/indistinguishability proxies).

### 4.3 Finite-key penalty (first implementation)

PhotonTrust currently uses an asymptotic secret fraction:

`privacy_term = max(0, 1 - f_ec*h2(q) - h2(q))`

Finite-key must reduce this term. For a v1 implementation, use a conservative
penalty that is:
- zero when finite-key is disabled,
- increases as `signals_per_block` decreases,
- increases as `security_epsilon` decreases.

Example shape (not a final security proof):

`privacy_term_finite = max(0, privacy_term - k(epsilon) / sqrt(n))`

Where:
- `n = signals_per_block * sifting_factor` (or an explicit n_sifted model),
- `k(epsilon)` is tuned from literature bounds and documented.

Phase 2 (when needed):
- Implement a protocol-specific finite-key secret key length formula using a
  composable security reference.

---

## 5) Implementation Plan (Files and Responsibilities)

### Step 1: Config + presets (no behavior change)
- Extend YAML config examples (add one new demo):
  - `configs/demo1_coexistence_example.yml` (new)
  - `configs/demo1_finite_key_example.yml` (new)

### Step 2: Channel noise calculation
- Add:
  - `photonstrust/channels/coexistence.py` (or `channels/noise.py`)
- Implement:
  - `compute_raman_counts_cps(distance_km, coexistence_cfg, band, wavelength_nm)`
  - Keep it deterministic and unit-tested.

### Step 3: QKD model integration
- Update:
  - `photonstrust/qkd.py`
- Add:
  - `background_counts_cps` and `raman_counts_cps` into the `p_dark` (noise)
    calculation.
  - `q_mis` contribution in QBER.
  - finite-key branch that maps asymptotic -> finite-key key rate.

### Step 4: Reporting and schema
- Update:
  - `photonstrust/report.py`
  - `schemas/photonstrust.reliability_card.v1.schema.json`
  - `reports/specs/reliability_card_v1.md`
- Add new optional breakdown fields:
  - `qber_components.raman`
  - `qber_components.misalignment`
  - `qber_components.source_visibility`
  - `finite_key.enabled`, `finite_key.signals_per_block`, `finite_key.penalty`

### Step 5: Tests and benchmarks
- Add tests:
  - `tests/test_qkd_coexistence_noise.py`
  - `tests/test_qkd_misalignment_floor.py`
  - `tests/test_qkd_finite_key_monotonicity.py`
- Add at least one reference benchmark fixture (parameterized) capturing the
  qualitative trend from coexistence literature:
  - increasing classical launch power should reduce secure key rate and increase
    outage probability at fixed distance.

---

## 6) Validation Gates (Definition of Done)

Functional:
- Backward compatibility: existing configs produce identical outputs when all new
  fields are absent.
- Determinism: fixed seed + config hash reproduces outputs within tolerance.

Scientific sanity:
- Key rate decreases monotonically with:
  - increased background_counts_cps,
  - increased classical_launch_power_dbm,
  - increased misalignment_prob,
  - enabled finite-key with smaller signals_per_block.
- QBER clamps remain enforced in `[0, 0.5]`.

Reporting:
- Reliability Card includes explicit visibility/misalignment and coexistence/noise
  assumptions when enabled.
- Error budget shows the new contributors, not hidden inside "dark".

---

## Source index (primary references)

Coexistence and Raman noise:
- Coexistence of high-bit-rate QKD and data on optical fiber (Patel et al., 2012):
  https://doi.org/10.1103/PhysRevX.2.041010
- Impact of Raman scattered noise from multiple telecom channels on QKD (da Silva et al., 2014 preprint):
  https://arxiv.org/abs/1410.0656
- Quantum key distribution and 1 Gbit/s data encryption over a single fibre (Eraerds et al., 2009 preprint):
  https://arxiv.org/abs/0912.1798

Finite-key:
- Tight finite-key analysis for quantum cryptography (Tomamichel et al., 2012):
  https://doi.org/10.1038/ncomms1631

Detector afterpulsing (for gating/stateful noise):
- Time-domain measurements of afterpulsing in InGaAs/InP SPADs (Restelli et al., 2012):
  https://doi.org/10.1080/09500340.2012.687463
