# Roadmap and Milestones

This roadmap turns PhotonTrust into a commercial verification platform across
chip and satellite workflows.

## Roadmap horizon
- Total: 18 months
- Operating cadence: 2-week sprint, monthly release train, quarterly gate

## Phase A (Month 0-3): Expansion foundation

## Outcomes
- free-space channel MVP integrated with existing fiber path.
- detector gating/saturation model in physics engine.
- fiber QKD deployment realism pack (coexistence noise, misalignment floor, finite-key mode).
- graph schema v0.1 and compiler service (graph JSON -> ScenarioConfig).
- initial ChipVerify alpha reports.

## Acceptance gate A
- 3 benchmark scenarios pass deterministic replay and diagnostics checks.
- at least 1 QKD coexistence/finite-key scenario passes monotonicity + reporting gates.
- preview mode p95 runtime under 5 seconds for target scenarios.

## Phase B (Month 4-8): ChipVerify beta

## Outcomes
- drag-drop editor alpha with reusable component templates.
- component library v1 (ring, MZI, coupler, detector, channel blocks).
- scenario diff workflow and provenance panel.
- external pilot package for design teams.

## Acceptance gate B
- at least 2 external partners reproduce card outputs in independent
  environments.
- calibration diagnostics included in all pilot reports.

## Phase C (Month 9-14): OrbitVerify pilot

## Outcomes
- satellite mission profile templates (ground station, pass geometry, weather
  envelope assumptions).
- compliance evidence bundle v1 (EAR/ITAR/FCC fields in report metadata).
- mission rehearsal report templates for review boards.

## Acceptance gate C
- one satellite/space pilot partner confirms usefulness in actual review flow.
- scenario cards contain complete provenance and compliance metadata.

## Phase D (Month 15-18): Commercial scale

## Outcomes
- reliability card v2 schema with chip + orbit extensions.
- signed artifact and provenance attestation pipeline.
- enterprise deployment package (on-prem/isolated environment).
- onboarding and support playbooks.

## Acceptance gate D
- 3 paid customers.
- pilot-to-production setup time under 2 weeks.
- release quality gates pass for two consecutive release cycles.

## Cross-phase quality gates (always on)
- schema validation for all card outputs.
- benchmark drift checks with explicit override process.
- CI checks for calibration diagnostics thresholds.
- signed release bundle integrity verification.

## KPI dashboard
- model trust: diagnostics pass rate.
- product speed: edit-to-result latency.
- business traction: pilot conversion rate and recurring revenue mix.

## Related docs
- `12_web_research_update_2026-02-12.md`
- `13_business_expansion_and_build_plan_2026-02-12.md`
- `deep_dive/16_qkd_deployment_realism_pack.md`

