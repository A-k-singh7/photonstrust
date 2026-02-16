# Phase 36 - Evidence Bundle Attestation + Schema Contracts - Research Brief

## Metadata
- Work item ID: PT-PHASE-36
- Date: 2026-02-14
- Scope: Add schema contracts + validation gates for (1) workflow chain reports and (2) evidence bundle manifests.

## Problem Statement
PhotonTrust is evolving into a verification/control-plane platform. That means
the primary product output is not "a number", but a *reviewable artifact pack*
whose structure must remain stable over time.

Phase 34/35 introduced:
- a chained workflow report (`workflow_report.json`) and
- a portable evidence bundle zip containing `bundle_manifest.json` with sha256 per file.

Without explicit schemas and validation gates:
- these artifacts can silently drift as new fields are added or renamed,
- reviewers cannot reliably build tooling around them,
- and open-science users cannot depend on stable formats for papers/labs.

## Research Findings (Why Schemas Matter For Trust)
Trustable platforms have contracts:
- a versioned schema is the simplest enforceable contract for artifacts
- schema validation in CI prevents accidental breaking changes

PhotonTrust already uses this pattern successfully:
- invdesign reports are schema-validated (`schemas/photonstrust.pic_invdesign_report.v0.schema.json`)
- KLayout artifact packs are schema-validated (`schemas/photonstrust.pic_klayout_run_artifact_pack.v0.schema.json`)

Extending the same discipline to workflow and bundle artifacts:
- makes "workflow evidence" first-class and toolable,
- reduces ambiguity in enterprise/academic review,
- and creates a stable foundation for future signing/attestation work.

## Trust + Safety Constraints
- Schemas should be strict (reject unexpected fields) to prevent silent drift.
- Where extensibility is required (e.g., `artifact_relpaths` objects), schemas should allow additional properties with bounded types (string relpaths).
- Schema versioning must be explicit (`schema_version: "0.1"`) so future breaking changes can ship as new schema IDs.

## Outcome (Phase 36)
- Introduce schema contracts for:
  - `pic.workflow.invdesign_chain` reports
  - `photonstrust.evidence_bundle` manifests
- Add automated tests to validate real outputs against schemas.
- This becomes the base layer for future cryptographic signing/attestation.

