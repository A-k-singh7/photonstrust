# Research Brief

## Metadata
- Work item ID: PT-PHASE-11
- Title: OrbitVerify mission templates v1 (pass envelopes + metadata)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/orbit/` (new)
  - `photonstrust/channels/free_space.py` (existing; contributor decomposition)
  - `photonstrust/qkd.py` (existing; point computation)
  - `photonstrust/report.py` / report exports (existing; add pass metadata hooks)
  - `schemas/photonstrust.orbit_pass_results.v0.schema.json` (new)

## 1) Problem and motivation
OrbitVerify needs a mission-oriented layer above the existing free-space channel
model. Real satellite/free-space links are time-varying: elevation, slant range,
and background regimes change during a pass, and "go/no-go" decisions are made
from an envelope (best/median/worst) rather than a single distance sweep.

PhotonTrust already has a decomposed free-space efficiency model and a QKD point
model, but it lacks:
- a mission pass profile contract (how a pass is represented),
- pass execution (run the engine across a time-segmented envelope),
- exported pass metadata and assumptions in artifacts, and
- validation gates that enforce "known-sense" physical behavior.

## 2) Research questions
- RQ1: What minimal mission pass profile schema is enough for mission rehearsal
  and design review workflows without implementing full orbital mechanics?
- RQ2: How do we represent and execute "best/median/worst" envelopes in a way
  that is auditable and compatible with multi-fidelity execution?
- RQ3: What are the minimum exported artifacts for trust (metadata table,
  contributor decomposition, and reproducibility fields)?
- RQ4: What invariants must be tested to prevent obviously wrong physics (e.g.,
  higher elevation producing worse performance under identical settings)?

## 3) Method design (v0.1)

### 3.1 Pass representation: explicit samples + fixed step
Represent a pass as a list of samples at a fixed `dt_s`, each with:
- time `t_s`,
- slant range `distance_km`,
- elevation angle `elevation_deg`,
- background regime proxy `background_counts_cps`.

This is intentionally a "pass envelope" contract, not an orbit propagator.

### 3.2 Envelope cases: best/median/worst
Define a list of named `cases`, each applying a deterministic override set to
the base free-space channel parameters, for example:
- atmospheric extinction coefficient,
- pointing jitter,
- turbulence proxy,
- background scaling factor.

Each case reuses the same pass samples unless explicitly changed, making the
source of differences transparent.

### 3.3 Outputs: time-series + integrated pass totals
For each case:
- compute QKD point outputs per sample,
- include channel decomposition per sample (geometric/atmospheric/pointing/etc),
- compute pass-level summary metrics:
  - total key bits over the pass (`sum(key_rate_bps * dt_s)`),
  - average/min/max key rate,
  - min/max loss in dB.

### 3.4 Trust artifacts
Export:
- mission metadata (pass id, dt, number of samples, case list),
- an assumptions table (explicit parameters and units),
- reproducibility metadata (config hash, engine version, python/platform),
- explicit limitations (v0.1 pass envelope, not orbit propagation).

## 4) Primary standards/program anchors (for assumptions alignment)
These references anchor terminology and model decomposition (not copied code):
- ITU-R P.1814 (terrestrial FSO attenuation): https://www.itu.int/rec/R-REC-P.1814/en
- ITU-R P.1817 (FSO availability): https://www.itu.int/rec/R-REC-P.1817/en
- CCSDS Optical High Data Rate Communication 1064 nm (CCSDS 141.11-O-1):
  https://public.ccsds.org/Pubs/141x11o1.pdf
- NASA Laser Communications Relay Demonstration (LCRD) overview:
  https://www.nasa.gov/mission/laser-communications-relay-demonstration-lcrd/

## 5) Acceptance criteria
- A mission pass runner exists and produces a versioned, deterministic JSON
  results artifact with pass metadata and assumptions.
- Scenario templates exist for:
  - a multi-sample pass envelope,
  - at least two background regimes (day/night proxy).
- Validation includes "known-sense" checks:
  - higher elevation improves channel metrics and increases key rate (all else equal),
  - higher background worsens QBER and reduces key rate (all else equal).
- `py -m pytest -q` and release gate pass.

## 6) Decision
- Decision: Proceed.

