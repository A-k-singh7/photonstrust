# Work Items

This folder is the audit trail for PhotonTrust's research-to-build workflow.

## Required pattern
For each non-trivial change (new model, protocol change, benchmark update,
schema change, performance optimization), create a work-item folder:

`docs/work_items/YYYY-MM-DD_<short_name>/`

Inside, include:
1) `research_brief.md` (PhD-level)
2) `implementation_plan.md`
3) `validation_report.md`

Templates:
- `docs/templates/research_brief_template.md`
- `docs/templates/implementation_plan_template.md`
- `docs/templates/validation_report_template.md`

## Definition of done
- The work-item folder exists and is linked from the relevant research doc.
- The code change is validated by tests and regression checks.
- Public-facing docs updated where behavior or assumptions changed.
