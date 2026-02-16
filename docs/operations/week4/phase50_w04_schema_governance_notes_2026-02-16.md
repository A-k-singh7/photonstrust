# Phase 50 W04 Operations Notes (Config Schema Governance)

Date: 2026-02-16

## Week focus

Finalize the quality/security foundation by adding explicit scenario config
schema governance with migration hooks and fail-fast unsupported-version
handling.

## Migration policy notes

- Current supported scenario config schema: `0.1`.
- Legacy configs with missing/`0` schema version are migrated through the
  explicit `0.0 -> 0.1` migration hook.
- Unsupported schema versions fail fast with actionable migration guidance.
- Pilot validation config (`configs/pilot_day0_kickoff.yml`) now carries
  explicit `schema_version: "0.1"`.

## Refreshed risk table

| Risk ID | Risk | Owner | Likelihood | Impact | Mitigation | Gate trigger | Status |
|---|---|---|---|---|---|---|---|
| P50-R3 | Config schema migration work introduces backward-compatibility break | SIM | Medium | High | Added explicit migration hook (`0.0 -> 0.1`) and tests for legacy config behavior | Legacy config fails migration tests | Mitigated |
| P50-R11 | Unsupported schema versions pass silently and cause undefined behavior | TL | Medium | High | Added fail-fast `ConfigSchemaVersionError` with migration guidance in loader + CLI | Unsupported schema version returns non-error code | Mitigated |
| P50-R12 | Strict schema checks block existing pilot flows | QA | Low | High | Added pilot validate-only gate and full regression suite run | `pilot_day0_kickoff.yml --validate-only` fails | Mitigated |
| P50-R13 | Future schema updates occur without codified migration path | DOC | Medium | Medium | Codified migration hook registry and schema policy notes in W04 docs | New schema introduced without migration hook | Open |

## Owner map confirmation

Config governance and migration streams remain explicitly owned with no
accountable/responsible gaps.
