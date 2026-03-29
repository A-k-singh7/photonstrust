## Summary
- Linked issue(s):
- Scope:
- What changed:
- Why:

## Change Type
- [ ] Docs or repo hygiene only
- [ ] Behavior change
- [ ] Schema, config, or contract change
- [ ] Release or automation workflow change

## Contract impact
- [ ] No public contract changes
- [ ] Public contract/config/schema docs were updated
- Impacted contracts, configs, or schemas:

## Validation
- [ ] Ran the smallest relevant local checks
- [ ] Added/updated tests for changed behavior
- [ ] Schema validation unaffected or updated (`tests/test_schema_validation.py`)
- [ ] Regression/golden checks reviewed when outputs changed
- [ ] Ran `npm run build` for web changes
- [ ] Ran `npm run lint` for web changes

## Documentation
- [ ] No doc changes required
- [ ] Updated docs and listed files:
- [ ] Updated `CHANGELOG.md` for external behavior or workflow changes
- [ ] Updated contributor/release docs when repo workflow changed

## Repository Hygiene
- [ ] Branch is scoped to one logical change
- [ ] `git diff --check` is clean
- [ ] No generated local artifacts included by accident (`__pycache__`, `.egg-info`, `web/test-results`, scratch logs, etc.)
- [ ] No secrets, tokens, or local environment files included by accident

## Reproducibility
- [ ] Seeds/configs retained or documented
- [ ] Output/fixture updates are explained in this PR
- [ ] Ran `python scripts/refresh_repo_baselines.py --all` or explained why tracked fixture/release artifacts did not need it
