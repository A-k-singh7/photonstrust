# Upgrade Ideas (Single Front Door)

Date: 2026-02-14

You are right: there are a lot of docs. This folder is the "front door" for
future work. It consolidates upgrade ideas into 3 short, actionable maps so you
do not need to hunt through 200+ files.

Rules for using this folder:
- Add new upgrades here first (as an idea with acceptance criteria).
- When you decide to build, convert the idea into a strict phase folder under:
  - `docs/operations/phased_rollout/phase_XX_.../`
  following: research -> plan -> build -> validate -> doc updates.
- Mark the upgrade idea as DONE once the phase validation report exists.

## Maps (Read These Only)

1. `01_upgrade_ideas_qkd_and_satellite.md`
   - Protocol roadmap, fiber realism pack, satellite realism pack, QuTiP/Qiskit multi-fidelity trust gates.
2. `02_upgrade_ideas_pic_and_verification.md`
   - Drag-drop authoring improvements, DRC/PDRC/LVS, KLayout/GDS/SPICE, gdsfactory interop, inverse design evidence gates.
3. `03_upgrade_ideas_platform_quality_security.md`
   - Tests, CI, performance, dependency/security posture, packaging/community readiness.

## Source Indices (If You Need Depth)

- Audit index: `../audit/00_audit_index.md`
- Deep-dive index: `../research/deep_dive/00_deep_dive_index.md`
- Phased rollout truth: `../operations/phased_rollout/README.md`

Investor-grade demo plan (the "undeniable" wedge):
- `../research/deep_dive/31_fundable_wedge_and_denial_resistant_demos.md`
