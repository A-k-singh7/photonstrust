# Upgrade Ideas: Platform Quality + Security + Performance + Packaging

Date: 2026-02-14

This file consolidates platform upgrades that make PhotonTrust:
- more stable
- more secure
- faster
- easier to adopt in academia and industry

---

## P0 (Next)

### UPG-PLAT-001: CI overhaul (matrix + lint + coverage + optional deps)

Why:
- prevents silent regressions
- makes optional tool seams trustworthy (QuTiP/Qiskit/gdstk/API/UI)

Deliver:
- Python matrix 3.9-3.12
- `ruff` lint + format check
- `pytest-cov` with a coverage floor (start at 70%)
- optional deps test row (qutip/qiskit/layout/api)
- nightly schedule for slow regressions

Source:
- `../audit/04_ci_cd_improvements.md`

### UPG-PLAT-002: Supply chain + dependency scanning (pip-audit + Dependabot)

Why:
- basic security hygiene required for enterprise trust

Deliver:
- `.github/dependabot.yml`
- CI job: `pip-audit`
- Node: `npm ci` + optional `npm audit` for web

Source:
- `../audit/06_dependency_security.md`

### UPG-PLAT-003: SECURITY.md + disclosure process

Why:
- required for responsible vulnerability reporting

Deliver:
- `SECURITY.md` at repo root

Source:
- `../audit/06_dependency_security.md`

---

## P1 (Planned)

### UPG-TEST-001: Test coverage expansion + shared fixtures

Why:
- you cannot dominate trust with gaps in unit/integration testing

Deliver:
- `tests/conftest.py` shared fixtures
- utils/presets/events tests
- quick integration pipeline smoke test
- band/detector matrix param tests

Source:
- `../audit/02_test_coverage_gaps.md`

### UPG-CONFIG-001: Config schema versioning + migrations

Why:
- prevents silent config breakage across releases

Deliver:
- `schema_version` on scenario configs
- migration functions for breaking changes

Source:
- `../audit/03_configuration_validation.md`

### UPG-CONFIG-002: TypedDict -> Pydantic models (runtime validation)

Why:
- makes configs robust and self-documenting

Deliver:
- TypedDict definitions first
- Pydantic models for runtime validation next (v0.2)

Source:
- `../audit/03_configuration_validation.md`

### UPG-CODE-001: Error hierarchy + API exception hygiene

Why:
- API must not swallow bugs; error surfaces must be stable and safe

Deliver:
- `photonstrust/errors.py` base exception types
- API endpoints only catch PhotonTrustError for 400s; unexpected -> 500 with logging

Source:
- `../audit/07_code_quality.md`

---

## Performance (Scaling Without Breaking Determinism)

### UPG-PERF-001: Parallel uncertainty sampling (serial -> multi-core)

Why:
- certification mode runtime will otherwise block adoption

Deliver:
- parallel sample execution with per-sample deterministic seeds
- stable outputs independent of worker count

Source:
- `../audit/05_performance_bottlenecks.md`

### UPG-PERF-002: Vectorized detector fast path

Why:
- stochastic detector simulation is currently heavier than necessary

Deliver:
- numpy vectorized path for common (no afterpulse) scenarios
- keep heap-based event logic only where needed

Source:
- `../audit/05_performance_bottlenecks.md`

### UPG-PERF-003: API async/background jobs + caching

Why:
- long runs should not block the server
- repeat compile/sim should be cached by hash

Deliver:
- background job model for compute endpoints
- compile cache keyed by canonical config hash

Source:
- `../audit/05_performance_bottlenecks.md`

---

## Packaging + Adoption (Academic + Industry)

### UPG-PKG-001: CITATION.cff + LICENSE + issue templates

Why:
- academics need citation tooling; industry needs license clarity

Deliver:
- `CITATION.cff`
- `LICENSE`
- `.github/ISSUE_TEMPLATE/*`

Source:
- `../audit/09_packaging_improvements.md`

### UPG-PKG-002: Docs build system (mkdocs/sphinx) (optional)

Why:
- long-term adoption benefits from a structured docs site

Deliver:
- choose mkdocs or sphinx
- host on GitHub Pages or ReadTheDocs

Source:
- `../audit/09_packaging_improvements.md`

---

## Expanded Backlog (Trust Closure + Security)

This section turns "platform quality" into concrete, phase-buildable items.
If you build only one thing next: build Phase 40 signing/verification.

### [DONE] UPG-PLAT-010: Evidence bundle signing + verification (Phase 40)

Why:
- Phases 35-36 already export bundles + schema-validate them; signing closes the trust loop outside the repo

Risk if ignored:
- exported evidence is mutable; approvals cannot be cryptographically bound to the evidence they bless

Minimal viable slice:
- sign `bundle_manifest.json` (detached signature)
- `photonstrust evidence bundle verify` recomputes hashes and verifies signature

Validation gates:
- any post-export mutation fails verification
- `--require-signature` fails when signature missing

Anchors:
- SLSA v1.2: https://slsa.dev/spec/v1.2/
- in-toto: https://in-toto.io/
- Sigstore: https://www.sigstore.dev/

Implementation:
- `../operations/phased_rollout/phase_40_evidence_bundle_signing/`

### UPG-PLAT-011: Approvals reference signed bundle digest

Why:
- makes the project approvals log an audit-grade governance object

Minimal viable slice:
- approvals store `bundle_manifest_sha256` + signature metadata
- approval requires verification in certification mode

Validation gates:
- cannot approve without a verifiable signed digest
- approval log remains append-only

### UPG-PLAT-012: Publish evidence bundles by content digest (immutable URIs)

Why:
- prevents "evidence drift" by forcing content-addressed publishing

Minimal viable slice:
- publish `evidence/sha256/<digest>.zip` + `<digest>.manifest.json`

Validation gates:
- re-publishing identical bundle yields same digest/URI
- fetch+verify from storage passes

### UPG-PLAT-020: Scenario config `schema_version` + migration framework

Why:
- Phase 38 validation is strong, but long-lived configs need version governance and forward migration

Minimal viable slice:
- require `schema_version` in scenario configs
- add deterministic migrators for breaking changes

Validation gates:
- unsupported versions fail fast with actionable error
- migration output passes validation and is deterministic

### UPG-PLAT-021: Schema registry discipline for all public artifacts

Why:
- schema contracts are the backbone of diffing, approvals, evidence bundles, and external review

Minimal viable slice:
- single authoritative schema index + versioning policy
- CI validates: reliability cards, workflow reports, evidence manifests, approvals, API payloads

Validation gates:
- release gate fails if any produced artifact is schema-invalid

### UPG-PLAT-030: Dependency scanning policy is blocking for high/critical CVEs

Why:
- `pip-audit` is only useful if it can block known high-risk vulnerabilities

Minimal viable slice:
- fail CI on high/critical CVEs in runtime deps; warn-only for dev deps

Validation gates:
- an injected known-vulnerable dependency causes CI to fail with a clear report

### UPG-PLAT-031: SBOM generation for core + extras (bundle + release)

Why:
- evidence bundles are audit artifacts; SBOMs make dependency posture reviewable

Minimal viable slice:
- generate CycloneDX/SPDX SBOMs for core, api, ui, and "all extras"
- include SBOM digest pointers in evidence bundle manifests

### UPG-PLAT-040: API hardening: strict validation, input limits, no stack trace leaks

Why:
- the API is a trust boundary (run registry, artifacts, approvals)

Minimal viable slice:
- require jsonschema in API deployments; fail startup if missing
- request size limits; strict content-type and JSON parsing
- structured error taxonomy (no tracebacks in responses)

Validation gates:
- malformed/oversized requests yield stable 400/413 without stack traces

### UPG-PLAT-041: AuthN/AuthZ for runs, artifacts, approvals

Minimal viable slice:
- role-based auth: reader/contributor/approver/admin

Validation gates:
- unauthenticated gets 401; unauthorized gets 403
- approvals require approver role

### UPG-PLAT-050: Evidence bundle redaction + classification

Why:
- bundles can contain sensitive configs or measurement data; redaction must be explicit and testable

Minimal viable slice:
- classification: public/internal/restricted
- redaction rules + redaction summary in manifest

Validation gates:
- seeded fake secrets do not appear in exported bundles
- restricted bundles cannot be published to public destinations

### UPG-PLAT-060: Performance regression suite (PR-fast + nightly-slow)

Why:
- trust requires not just correctness but stable runtime envelopes

Minimal viable slice:
- define a small canonical set; record runtime percentiles + key output tolerances

Validation gates:
- PR fails (or requires explicit override) on large regressions
