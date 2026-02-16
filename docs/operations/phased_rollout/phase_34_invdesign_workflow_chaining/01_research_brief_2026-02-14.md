# Phase 34 - Invdesign Workflow Chaining - Research Brief

## Metadata
- Work item ID: PT-PHASE-34
- Date: 2026-02-14
- Scope: Add a first-class "workflow run" that chains PIC inverse design into layout + verification + EDA interop, while preserving PhotonTrust's tool-seam safety posture.

## Problem Statement
PhotonTrust currently exposes the PIC design loop as *separate* actions/runs:
- inverse design (`/v0/pic/invdesign/*`)
- layout build (`/v0/pic/layout/build`)
- LVS-lite (`/v0/pic/layout/lvs_lite`)
- optional KLayout artifact pack (`/v0/pic/layout/klayout/run`)
- SPICE export (`/v0/pic/spice/export`)

This is functional but not yet "control-plane grade" because it lacks a single, chained evidence object that proves:
1. which inverse-designed parameters produced the final graph,
2. which layout artifacts were generated from that graph,
3. which verification checks were run on that exact layout,
4. and which interop artifacts (KLayout pack, SPICE netlist) were exported for downstream tools.

Without an explicit chain run:
- reviewers must manually correlate run IDs and artifacts (error-prone),
- demos are easier to dispute ("did that layout match that optimized netlist?"),
- and the UI cannot offer a one-click "generate the full review pack" workflow.

## Research Findings (What Real EDA Flows Do)
Classical chip/EDA workflows are chained, not isolated:
- schematic/netlist -> layout -> DRC -> LVS -> extraction -> simulation

Even when early-stage flows are approximate (as PhotonTrust is by design in v0.x), the *process* is still expected:
- bounded, repeatable steps
- explicit tool provenance
- and a review artifact that ties the steps together

PhotonTrust already has the primitives needed for this, including two important interop seams:
- KLayout batch macro automation (with captured stdout/stderr + input/output hashes)
  - KLayout docs: https://www.klayout.de/doc.html
- SPICE-like netlist export for EDA interop (with stable mapping/provenance files)
  - ngspice is treated as optional external tool; SPICE export is deterministic and internal by default
  - ngspice docs: https://ngspice.sourceforge.io/docs.html

Implication:
- A "workflow run" is the missing glue layer that turns the set of actions into a decision-grade pipeline.

## Trust + Safety Constraints (Non-Negotiables)
- No arbitrary filesystem access through workflow chaining:
  - Only use artifact resolution inside run directories (`run_store.resolve_artifact_path`).
- No arbitrary macro execution:
  - KLayout runs must remain constrained to the trusted macro template(s) in `tools/klayout/macros/`.
- External tools are optional seams:
  - Workflow must succeed even if KLayout/ngspice are not available.
- Deterministic evidence:
  - The workflow report must explicitly include child run IDs, key settings hashes, and step statuses.

## Outcome (Phase 34)
PhotonTrust gains a first-class chained workflow surface:
- A new API endpoint to execute an end-to-end chain and produce a single "workflow run" manifest.
- A UI button to run the workflow and immediately surface the reviewable evidence links.
- A minimal, deterministic workflow report artifact that records the provenance chain.

