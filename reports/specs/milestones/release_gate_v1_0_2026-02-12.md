# Release Gate v1.0

## Gate prerequisites
- [x] All milestone acceptance sheets completed
- [x] CI fully green on release candidate
- [x] Benchmark bundle regenerated
- [x] Changelog and release notes finalized
- [x] Documentation index updated

## Final checks
- [x] Security and redaction checks done
- [x] Reproducibility bundle verified from clean environment
- [x] UI and CLI smoke checks done

## Release decision
- Decision date: 2026-02-12
- Approvers: TL, QA
- Final notes:
  - `rg -n --hidden -S "BEGIN PRIVATE KEY|API_KEY|SECRET_KEY|password\\s*=|token\\s*=" .` returned no matches.
  - `py -3 scripts/bundle_release.py` completed successfully.
  - Quick smoke scenario succeeded in `1.27s`:
    `py -3 -m photonstrust.cli run configs/demo1_quick_smoke.yml --output results/smoke_quick`.
  - Streamlit headless smoke start succeeded: `py -3 -m streamlit run ui/app.py --server.headless true --server.port 8511`.
  - `py -3 scripts/release/release_gate_check.py` reports `PASS` with tests + benchmark drift checks.
  - Milestone acceptance artifacts are archived under `reports/specs/milestones/`.
  - External reviewer dry-run outcome is `Conditional go`; v1.0 release remains approved with follow-up onboarding improvements tracked.

## Definition of done
- Templates are used for each milestone and archived with release artifacts.
