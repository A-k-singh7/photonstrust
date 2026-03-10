# Developer Guides

This section is the best entry point for contributors and maintainers.

## Start Here

- `../../CONTRIBUTING.md`
- `../../SECURITY.md`
- `../../scripts/README.md`
- `../../docs/README.md`

## Main Topics

- contributor workflow and validation expectations
- research-to-build process for model changes
- release, benchmark, and readiness automation
- UI and API developer workflows

## Common Commands

```bash
python scripts/ci_checks.py
python scripts/run_validation_harness.py --output-root results/validation
python scripts/validate_recent_research_examples.py
python scripts/clean_local_workspace.py --dry-run
```
