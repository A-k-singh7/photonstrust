# Research Brief

## Metadata
- Work item ID: PT-PHASE-18
- Title: OrbitVerify evidence hardening v0.2 (availability envelope + standards anchors)
- Authors: PhotonTrust core team
- Date: 2026-02-13
- Related modules (planned/expected):
  - `photonstrust/orbit/pass_envelope.py` (extend summaries + report)
  - `photonstrust/orbit/diagnostics.py` (extend config diagnostics)
  - `photonstrust/channels/free_space.py` (already returns contributor decomposition)

## 1) Problem and motivation

OrbitVerify pass envelopes currently compute performance assuming a single
physics configuration and a sampled time-series envelope. This is useful, but
real free-space/satellite operations are dominated by:
- **availability constraints** (cloud blockage / operational windows),
- and the need to communicate loss contributors in **standards-aligned terms**.

PhotonTrust already decomposes free-space efficiency into contributors
(`eta_geometric`, `eta_atmospheric`, `eta_pointing`, `eta_turbulence`,
`eta_connector`). What’s missing is a first-class way to express and report:
- “how often is the link available?” (as an explicit scenario assumption),
- and “what standards anchors map to these contributor categories?” (as
  provenance, not as a claim of compliance).

## 2) Key research questions

- RQ1: What is the smallest availability model that is honest (clearly labeled
  as an assumption) and still operationally useful?
- RQ2: How do we embed standards anchors without implying formal compliance?
- RQ3: What should be surfaced in outputs so engineering teams can do
  go/no-go tradeoffs (keys-per-pass under availability assumptions)?

## 3) Decision and approach

Decision (v0.2): implement an explicit **availability envelope scalar** and
surface **standards anchors** in OrbitVerify artifacts.

Approach:
- Add optional `orbit_pass.availability.clear_fraction` in config:
  - interpreted as the fraction of the pass assumed to be “clear/usable”.
- Add to each case summary:
  - `expected_total_keys_bits = total_keys_bits * clear_fraction`
  - (purely an expectation under the declared assumption)
- Extend diagnostics to validate:
  - clear_fraction is a number within `[0, 1]` when present.
- Extend the HTML report to show:
  - the clear_fraction assumption and expected_total_keys_bits per case.
- Include standards anchor metadata as explicit “references” text in the report
  and results assumptions notes (no compliance claim).

## 4) Acceptance criteria

- Orbit pass config can optionally include `orbit_pass.availability.clear_fraction`.
- Results include expected keys under availability assumption:
  - per-case `summary.expected_total_keys_bits`.
- Diagnostics warn/error appropriately for invalid availability values.
- HTML report includes availability assumption and expected keys column(s).
- Automated gates pass:
  - `py -m pytest -q`
  - `py scripts/release/release_gate_check.py`
  - `cd web && npm run lint`
  - `cd web && npm run build`

## 5) Non-goals

- No weather API integration.
- No site-specific cloud climatology modeling.
- No claim of standards compliance (anchors only).
- No orbit propagator.

