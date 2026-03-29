# Research-to-Build Protocol (Default Operating Pattern)

This protocol defines the mandatory execution order for all substantial work.

## Protocol stages

## Stage A: Research (required first)
Produce a PhD-level research brief before implementation starts.

Minimum requirements:
- clear research questions and falsifiable hypotheses
- explicit mathematical assumptions
- baseline and comparison strategy
- uncertainty and reproducibility plan

Template:
- `docs/templates/research_brief_template.md`

## Stage B: Planning and code-fit
Map the research design into concrete repository changes.

Minimum requirements:
- file-level impact map
- interface compatibility analysis
- incremental build steps with test gates

Template:
- `docs/templates/implementation_plan_template.md`

## Stage C: Build and test
Implement incrementally and validate at each checkpoint.

Required checks:
- relevant unit/integration tests
- schema validation
- regression and golden checks when output formats change

## Stage D: Final documentation update
Document results and update user-facing guidance.

Required updates:
- relevant research and deep-dive docs
- README/docs where behavior changed
- changelog/release notes for externally visible updates

Template:
- `docs/templates/validation_report_template.md`

## Quality gates
Work is complete only if all stages pass.

Gate 1 (research quality):
- hypotheses and methods are review-ready

Gate 2 (engineering quality):
- tests and reproducibility checks pass

Gate 3 (documentation quality):
- docs reflect actual behavior and limitations

## Audit trail expectations
For each completed work item, maintain:
- research brief
- implementation plan
- validation report

Store these under a work-item folder in docs when possible.


## Inline citations (web, verified 2026-02-12)
Applied to: staged research-to-build workflow, architecture checks, and audit-trail requirements.
- RFC 9340 architecture principles: https://www.rfc-editor.org/info/rfc9340
- IETF QIRG quantum-native draft (November 2025): https://www.ietf.org/archive/id/draft-cacciapuoti-qirg-quantum-native-architecture-00.html
- OpenQASM 3 paper: https://arxiv.org/abs/2104.14722
- QIR specification (LLVM-based quantum IR): https://github.com/qir-alliance/qir-spec
- QuTiP release and compatibility context: https://qutip.org/download.html
- Qiskit release notes and runtime-facing changes: https://quantum.cloud.ibm.com/docs/en/api/qiskit/release-notes/2.2
- JCGM 100 uncertainty baseline: https://www.bipm.org/en/doi/10.59161/JCGM100-2008E
- NIST CSF 2.0 governance baseline: https://doi.org/10.6028/NIST.CSWP.29
