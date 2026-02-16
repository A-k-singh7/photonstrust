# Phase 28 - SPICE + KLayout Interop (EDA Tool Seams) - Research Brief

## Metadata
- Work item ID: PT-PHASE-28
- Date: 2026-02-14
- Scope: Provide deterministic EDA interoperability seams for PIC verification workflows:
  - export graph connectivity as a SPICE-like netlist + mapping artifacts
  - optional batch execution runners for external tools (ngspice, KLayout)

## Problem Statement
PhotonTrust needs to be adoptable inside existing engineering flows.

In practice, most PIC teams already have:
- layout tooling (KLayout-centric flows are common), and
- analog simulation tooling (SPICE-family simulators) for electrical/control blocks and for some photonic compact-model environments.

Even if PhotonTrust remains the physics source of truth for the "trust artifacts" (evidence packs, drift governance, performance DRC), it must be able to:
- export deterministic, reviewable representations that external tools can ingest, and
- optionally run those tools in batch mode to produce machine-readable artifacts.

This phase focuses on seams and provenance, not on claiming SPICE can directly solve optical physics by default.

## Research Notes

### 1) Why SPICE export is valuable (even before full co-simulation)
A deterministic SPICE-like netlist enables:
- partner workflows that already rely on simulator-specific subckt libraries,
- schematic-to-layout correlation checks (connectivity is a first-class artifact),
- reproducible reviews: a netlist diff is often easier to audit than a binary layout diff.

### 2) Tool runners must be optional
PhotonTrust open-core should not require external tools.

Instead:
- discover tools on PATH
- run them in batch mode when present
- capture commands, return codes, and logs into artifacts

### 3) KLayout fits as a batch macro runner
KLayout is the practical runtime for:
- PDK technology file semantics,
- DRC macros,
- and layout scripts.

PhotonTrust should:
- treat KLayout as an external runner,
- avoid embedding foundry decks in open-core,
- capture tool provenance and outputs.

## Phase 28 Exit Criteria (high-level)
- A deterministic SPICE export exists for PIC graphs:
  - `netlist.sp` + `spice_map.json` + `spice_provenance.json`
- An optional ngspice runner seam exists:
  - batch run wrapper producing logs/raw outputs (when ngspice is installed)
- The KLayout runner seam exists (from Phase 27) and is documented as part of the EDA runner posture.
