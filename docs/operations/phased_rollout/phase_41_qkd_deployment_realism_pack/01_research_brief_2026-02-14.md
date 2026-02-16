# Phase 41: QKD Deployment Realism Pack (Fiber) (Research Brief)

Date: 2026-02-14

## Goal

Make PhotonTrust fiber QKD outputs defensible under deployed-fiber constraints by
standardizing and gating the highest-leverage realism terms:

- coexistence Raman noise (classical + QKD on the same fiber)
- explicit misalignment / optical visibility QBER floor
- finite-key (non-asymptotic) penalty mode
- source indistinguishability proxy (HOM visibility)
- explicit background count accounting (channel + detector)

This phase is about trust closure for *fiber deployments*, not protocol expansion.
Decoy-state BB84 / MDI / TF are out of scope here.

Repo anchors (what exists today):
- physics core: `photonstrust/qkd.py`
- Raman model: `photonstrust/channels/coexistence.py`
- card/report: `photonstrust/report.py`
- existing behavioral gates:
  - `tests/test_qkd_coexistence_noise.py`
  - `tests/test_qkd_misalignment_floor.py`
  - `tests/test_qkd_finite_key_monotonicity.py`
  - `tests/test_qkd_plob_bound.py`

Companion spec (already written, aligns with current implementation):
- `docs/research/deep_dive/16_qkd_deployment_realism_pack.md`

---

## Deployment reality: why these terms are non-optional

1) Raman coexistence noise
- In metro/regional deployments, QKD often shares fiber with classical traffic.
- Spontaneous Raman scattering produces broadband in-band noise that scales with:
  launch power, number of classical channels, distance, and filter bandwidth.

2) Misalignment / visibility floor
- Field links have a non-zero minimum QBER from residual polarization/phase
  drift, finite extinction, and alignment error.
- Without an explicit floor, models look “lab-only” (unrealistically low QBER at
  short distance).

3) Finite-key effects
- Practical operation uses finite blocks over finite time; asymptotic key
  fractions can overstate achievable secure key, especially at long distance.

4) Source indistinguishability (HOM visibility)
- Entanglement-based links are sensitive to photon indistinguishability.
- A pure loss model cannot represent “good loss, bad interference” regimes.

5) Background counts
- Background photons (filter leakage, stray light, reflections) combine with
  detector dark counts and must be explicit, not hidden.

---

## What is implemented (and what it means)

Raman coexistence:
- `photonstrust/channels/coexistence.py` implements a calibration-friendly linear
  Raman counts model with a single coefficient.
- `photonstrust/qkd.py` adds `raman_counts_cps` into the total noise counts.

Misalignment / visibility:
- `protocol.optical_visibility` maps to a QBER floor `q_misalignment=(1-V)/2`.
- Otherwise `protocol.misalignment_prob` is used.

Finite-key:
- `finite_key.enabled` activates a monotonic penalty subtracted from the
  asymptotic privacy term.
- This is a *v1 surrogate* penalty: it is monotonic in block size and epsilon but
  is not a protocol-complete composable finite-key proof.

Source indistinguishability:
- `source.hom_visibility` (or `source.indistinguishability`) maps to
  `q_source=(1-V)/2` and contributes to QBER/fidelity.

Noise accounting:
- total noise counts are additive in counts/sec and integrated over the
  coincidence window.
- the Reliability Card reports noise/QBER decomposition fields.

---

## Applicability bounds (anti-overclaim rules)

Any Phase 41 “deployment-realistic” claim must:

1) Declare coexistence parameters when `channel.coexistence.enabled=true`,
   including coefficient provenance (measured vs assumed).
2) Use a non-zero misalignment/visibility floor for field-deployment claims
   unless explicitly presenting an idealized lab baseline.
3) If finite-key is enabled, report `signals_per_block`, `security_epsilon`, and
   `parameter_estimation_fraction`, and state this is a v1 monotonic penalty.
4) Avoid visibility double-counting: do not set both `protocol.optical_visibility`
   and `source.hom_visibility` from the same measurement without stating the
   split of responsibility.
5) Always surface noise breakdown (`dark`, `background`, `raman`) and
   `coincidence_window_ps` since they dominate long-distance behavior.

---

## Phase 41 deliverables

1) Canonical presets
- Add `configs/canonical/` with a small set of deterministic fiber presets:
  metro, regional, coexistence, finite-key, abort boundary.

2) Drift governance
- Add a baseline fixture for canonical presets and a CI test that detects drift.
- Define baseline update workflow (regenerate only when change is intentional).

3) Artifact labeling
- Ensure Reliability Cards include human-readable applicability notes derived
  from config flags (coexistence, finite-key, misalignment, source visibility).

---

## Primary anchors (external)

Coexistence / Raman:
- Patel et al. (2012) coexistence, Phys. Rev. X: https://doi.org/10.1103/PhysRevX.2.041010
- da Silva et al. (2014) Raman noise multi-channel (preprint): https://arxiv.org/abs/1410.0656
- Eraerds et al. (2009) QKD + data on one fiber (preprint): https://arxiv.org/abs/0912.1798

Finite-key:
- Tomamichel et al. (2012) tight finite-key analysis: https://doi.org/10.1038/ncomms1631

Capacity sanity (repeaterless bound; anti-overclaim):
- Pirandola et al. (2017) PLOB bound: https://doi.org/10.1038/ncomms15043
