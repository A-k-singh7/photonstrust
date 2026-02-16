# Milestone Acceptance Templates

This document provides reusable templates for milestone acceptance reviews.

## How to use
- Copy one template per milestone.
- Fill all sections before acceptance meeting.
- Archive completed templates under `reports/specs/milestones/`.

---

## Template A: Milestone Readiness Sheet

### Milestone metadata
- Milestone ID:
- Date:
- Owner:
- Related docs:
- Scope summary:

### In-scope deliverables
- [ ] Deliverable 1
- [ ] Deliverable 2
- [ ] Deliverable 3

### Out-of-scope confirmations
- [ ] Items intentionally deferred are listed

### Technical acceptance criteria
- [ ] Functional criteria met
- [ ] Schema compatibility verified
- [ ] Regression tests pass
- [ ] Reproducibility checks pass

### Scientific acceptance criteria
- [ ] Physics outputs validated against expected trends
- [ ] Uncertainty metrics included where required
- [ ] Error budget interpretation reviewed

### UX and reporting acceptance
- [ ] Reliability Card generated (HTML)
- [ ] Reliability Card generated (PDF or documented fallback)
- [ ] UI displays scenario outputs correctly

### Risks and limitations
- Known limitation 1:
- Known limitation 2:

### Approval
- TL sign-off:
- QA sign-off:
- Date:

---

## Template B: Regression and Baseline Gate

### Gate context
- Scenario set:
- Baseline file version:
- Test run ID:

### Checks
- [ ] Unit tests passed
- [ ] Integration tests passed
- [ ] Baseline regression test passed
- [ ] Golden report hash test passed
- [ ] Schema validation test passed

### Drift analysis
- Metrics with notable drift:
- Drift rationale:
- Approved by:

### Decision
- [ ] Gate passed
- [ ] Gate failed
- Notes:

---

## Template C: Reliability Card Quality Review

### Card metadata
- Scenario ID:
- Band/topology:
- Card version:

### Mandatory field review
- [ ] Inputs complete
- [ ] Derived metrics complete
- [ ] Outputs include uncertainty where applicable
- [ ] Error budget present and consistent
- [ ] Safe-use label and rationale present
- [ ] Reproducibility bundle complete

### Semantic quality review
- [ ] Dominant error aligns with scenario behavior
- [ ] Recommendations are actionable
- [ ] Confidence level or uncertainty bounds are interpretable

### Reviewer comments
- Reviewer 1:
- Reviewer 2:

### Approval
- [ ] Approved
- [ ] Needs revision

---

## Template D: External Reviewer Dry-Run

### Reviewer profile
- Org/team:
- Role:
- Familiarity level:

### Task script
- [ ] Install and run one flagship scenario
- [ ] Generate and inspect Reliability Card
- [ ] Compare two runs in UI
- [ ] Interpret recommendation and uncertainty

### Findings
- Time to first successful run:
- Clarity issues:
- Trust concerns:
- Feature requests:

### Severity triage
- Critical:
- Major:
- Minor:

### Go/No-go suggestion
- [ ] Go
- [ ] Conditional go
- [ ] No-go

---

## Template E: Release Gate v1.0

### Gate prerequisites
- [ ] All milestone acceptance sheets completed
- [ ] CI fully green on release candidate
- [ ] Benchmark bundle regenerated
- [ ] Changelog and release notes finalized
- [ ] Documentation index updated

### Final checks
- [ ] Security and redaction checks done
- [ ] Reproducibility bundle verified from clean environment
- [ ] UI and CLI smoke checks done

### Release decision
- Decision date:
- Approvers:
- Final notes:

## Definition of done
- Templates are used for each milestone and archived with release artifacts.


## Inline citations (web, verified 2026-02-12)
Applied to: milestone evidence criteria, regression gate discipline, and release approval documentation.
- ACM Artifact Review and Badging policy: https://www.acm.org/publications/policies/artifact-review-and-badging-current
- Semantic Versioning 2.0.0: https://semver.org/spec/v2.0.0.html
- Keep a Changelog 1.1.0: https://keepachangelog.com/en/1.1.0/
- SLSA v1.0 notes: https://slsa.dev/spec/v1.0/whats-new
- Sigstore cosign signature verification: https://docs.sigstore.dev/cosign/verifying/verify/
- NIST CSF 2.0: https://doi.org/10.6028/NIST.CSWP.29

