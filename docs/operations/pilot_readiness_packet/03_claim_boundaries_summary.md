# Claim Boundaries Summary (Aligned to Current Model Validity)

**Purpose:** Prevent over-claiming during pilot sales/delivery.

## 1) What we can claim now (supported)

- PhotonTrust produces **reliability card outputs** for configured scenarios, including uncertainty-oriented fields and safe-use labeling.
- Current build includes validated support for:
  - QKD realism upgrades (fidelity/dead-time/noise foundations, Raman effective-length, BBM92 coincidence handling).
  - Satellite realism upgrades (bounded atmosphere path, radiance-proxy background estimator, outage-aware diagnostics).
  - Orbit-pass finite-key budgeting semantics with explicit epsilon/budget metadata.
  - Canonical satellite benchmark fixtures with drift-governance checks.
  - Reliability card v1.1 schema with evidence tier + operating envelope metadata.
  - PIC scattering realism features (edge propagation, N-port Touchstone ingestion, isolator model) per current tests.
- Recent phased validation reports show passing test runs in the prepared dev environment through Phase 54.

## 2) Validity envelope for customer statements

Only claim results are valid when all of the following are true:

- Scenario is within the configured model envelope (protocol/channel/device assumptions explicitly documented in card/report).
- Satellite day/night and optics assumptions are explicit when radiance-proxy background is used.
- Orbit key statements include finite-pass constraints (duration/budget/epsilon) rather than asymptotic framing.
- Claimed operating points are covered by canonical benchmark + drift-governance evidence.
- Output includes reliability metadata (evidence tier, operating envelope, reproducibility/provenance fields).
- Validation artifacts are attached (test/validation harness outputs for the delivered run path).
- Any QBER/security thresholds are interpreted per card guidance (e.g., high-QBER cases remain qualitative).

## 3) What we must NOT claim

- **No claim of formal certification** (ETSI/ISO/NIST alignment references are informative unless separately certified).
- **No universal real-world guarantee** outside modeled assumptions, parameter bounds, or unvalidated deployment conditions.
- **No hardware performance guarantee** for customer devices unless calibrated/validated against customer measurement data.
- **No asymptotic-only orbit key claim** that ignores finite-pass budgeting constraints.
- **No claim that one local run equals production readiness** without hard-gate replay (full tests + validation harness) in target environment.

## 4) Customer-safe wording (use verbatim)

- “PhotonTrust provides simulation-and-evidence-based reliability assessments for the scoped scenarios in this pilot.”
- “Results are valid within the documented operating envelope and evidence tier on each reliability card.”
- “This pilot output supports engineering decisions; it is not a substitute for formal certification or full field qualification.”

## 5) Pre-external-communication check

Before proposal decks, statements, or emails:

- [ ] Claim text reviewed against this document.
- [ ] Evidence tier and envelope included.
- [ ] Any uncertified standards language softened to “aligned with” / “informed by”.
- [ ] Technical owner approved final wording.

## 6) Current operational caveat (as of 2026-02-16)

Satellite S3/S4 and pilot hardening features are validated in the prepared dev environment. Until target customer environment replay is completed with the same hard gates, position outputs as **engineering evidence within documented applicability bounds, pending target-environment replay confirmation**.
