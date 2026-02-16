# Phase 58 (W33-W36): Inverse Design Wave 3

Source anchors:
- `docs/research/deep_dive/19_inverse_design_engine_architecture.md`
- `docs/research/deep_dive/29_inverse_design_adjoint_strategy_licensing_and_evidence.md`

### W33 (2026-09-28 to 2026-10-04) - Mandatory inverse-design evidence gates
- Work: Certification mode requires complete inverse-design evidence artifacts.
- Artifacts: schema and gating updates.
- Validation: certification failure tests for incomplete evidence.
- Exit: Inverse-design claims are evidence-first.

### W34 (2026-10-05 to 2026-10-11) - Robust optimization knobs
- Work: Add fabrication corner robustness and worst-case reporting.
- Artifacts: robustness sweep outputs and thresholds.
- Validation: corner regression tests.
- Exit: Robustness becomes required, not optional.

### W35 (2026-10-12 to 2026-10-18) - External solver plugin boundary
- Work: Add plugin boundary for optional external/GPL solver paths.
- Artifacts: plugin runner seam and policy docs.
- Validation: plugin/no-plugin artifact parity checks.
- Exit: License-safe architecture with optional solver extensibility.

### W36 (2026-10-19 to 2026-10-25) - Flagship inverse-designed component
- Work: Deliver one flagship component end-to-end with robustness and signoff evidence.
- Artifacts: component package + evidence bundle.
- Validation: replay and signoff checks.
- Exit: Denial-resistant inverse-design demo fixture complete.
