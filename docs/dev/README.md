# Developer Guides

This section is the best entry point for contributors and maintainers.

## Start Here

- `../../CONTRIBUTING.md`
- `../../SECURITY.md`
- `../../scripts/README.md`
- `../../docs/README.md`
- `testing.md`
- `release_process.md`

## Main Topics

- contributor workflow and validation expectations
- research-to-build process for model changes
- release, benchmark, and readiness automation
- UI and API developer workflows
- repository structure, naming, and documentation cleanup planning

## Planning and Cleanup References

- `repo_professionalization_master_plan_2026-03-13.md`
- `repo_inventory_matrix_2026-03-13.md`
- `docs_cleanup_matrix_2026-03-13.md`
- `test_naming_cleanup_matrix_2026-03-13.md`
- `scripts_and_configs_cleanup_matrix_2026-03-13.md`
- `public_launch_hygiene_review_2026-03-13.md`
- `pdk_component_coverage_matrix_2026-03-13.md`
- `pdk_expansion_plan_2026-03-13.md`
- `pdk_internal_to_manifest_mapping_2026-03-13.md`

## Common Commands

```bash
python scripts/validation/ci_checks.py
python scripts/validation/run_validation_harness.py --output-root results/validation
python scripts/validation/validate_recent_research_examples.py
python scripts/dev/clean_local_workspace.py --dry-run
```
