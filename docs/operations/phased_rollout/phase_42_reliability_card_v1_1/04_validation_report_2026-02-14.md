# Phase 42: Reliability Card v1.1 (Validation Report)

Date: 2026-02-14

## Status

- PASS

## Checks

- `py -m pytest`

## Evidence

- Test run:

```text
py -m pytest
======================= 150 passed, 2 skipped in 17.76s =======================
```

- Notes:
  - `tests/test_reliability_card_v1_1_schema.py` validates v1.1 card output against `schemas/photonstrust.reliability_card.v1_1.schema.json`.
