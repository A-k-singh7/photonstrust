# Developer Guides

This section is the best entry point for contributors and maintainers.

## Start Here

- `../../CONTRIBUTING.md`
- `../../docs/README.md`
- `../../docs/reference/README.md`
- `../../scripts/README.md`
- `git_and_docs_workflow.md`
- `testing.md`
- `release_process.md`

## Main Topics

- contributor workflow and validation expectations
- git hygiene, branch discipline, and docs sync rules
- release, benchmark, and readiness automation
- UI and API developer workflows
- repository cleanup and maintainability planning

## Current Reference Docs

- `git_and_docs_workflow.md`
- `testing.md`
- `release_process.md`
- `repo_inventory_matrix_2026-03-13.md`
- `docs_cleanup_matrix_2026-03-13.md`
- `scripts_and_configs_cleanup_matrix_2026-03-13.md`
- `test_naming_cleanup_matrix_2026-03-13.md`
- `public_launch_hygiene_review_2026-03-13.md`
- `flagship_workflow_definition_2026-03-15.md`
- `pdk_component_coverage_matrix_2026-03-13.md`
- `pdk_internal_to_manifest_mapping_2026-03-13.md`
- `dependabot_pr_resolution_log_2026-03-15.md`

## Common Commands

```bash
pytest -q tests/test_docs_experience.py
python scripts/validation/ci_checks.py
python scripts/validation/run_validation_harness.py --output-root results/validation
python scripts/validation/validate_recent_research_examples.py
python scripts/dev/clean_local_workspace.py --dry-run
git diff --check
```
