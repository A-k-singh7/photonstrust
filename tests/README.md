# Test Suite Layout

PhotonTrust uses a mixed test stack covering domain logic, API contracts,
automation scripts, UI helpers, and validation baselines.

## Current Main Groups

- `api/`
  - FastAPI contract and server-lane tests.
- `scripts/`
  - Tests for maintainer automation scripts.
- `ui/`
  - Python-side UI helper and parity tests.
- `fixtures/`
  - Shared baseline and reference fixtures.
- top-level `test_*.py`
  - Domain, integration, schema, contract, and validation tests still pending
    further grouping.

## Naming Rules

- `test_<subject>_<behavior>.py` for domain tests.
- `test_<script_name>_script.py` for script tests.
- `test_<surface>_contract.py` for contract tests.
- `test_<artifact>_schema.py` for schema tests.

## Cleanup Direction

This structure is in transition. The next grouping waves should move more tests
into dedicated folders such as:

- `contracts/`
- `validation/`
- `integration/`
- `unit/`

without breaking CI or documented test references.
