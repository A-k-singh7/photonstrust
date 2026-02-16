# Phase 55: GraphSpec TOML + Round-Trip Guarantees (Validation Report)

Date: 2026-02-16

## Status

- PASS

## Targeted GraphSpec regression

- Command:

```text
py -3 -m pytest tests/test_graph_spec.py tests/test_graph_compiler.py tests/test_graph_diagnostics.py
```

- Result:

```text
16 passed in 0.97s
```

## GraphSpec formatter idempotence

- Commands:

```text
py -3 -m photonstrust.cli fmt graphspec graphs/demo8_qkd_link_graph.ptg.toml --write --print-hash
py -3 -m photonstrust.cli fmt graphspec graphs/demo8_qkd_link_graph.ptg.toml --check --print-hash
```

- Result:

```text
{
  "ok": true,
  "changed": false,
  "path": "graphs\\demo8_qkd_link_graph.ptg.toml",
  "graph_hash": "46cbbd85469ca091614057dad3da81f5a4ac262991fd575112646618068d2155"
}
```

## Full regression gate

- Command:

```text
py -3 -m pytest
```

- Result:

```text
274 passed, 2 skipped, 1 warning in 21.41s
```

## Benchmark drift governance

- Command:

```text
py -3 scripts/check_benchmark_drift.py
```

- Result:

```text
Benchmark drift check: PASS
```

## Release gate

- Command:

```text
py -3 scripts/release_gate_check.py
```

- Result:

```text
Release gate report written: results\release_gate\release_gate_report.json
Release gate: PASS
```

## CI checks

- Command:

```text
py -3 scripts/ci_checks.py
```

- Result:

```text
[ci-checks] all checks passed
```

## Validation harness

- Command:

```text
py -3 scripts/run_validation_harness.py --output-root results/validation
```

- Result:

```text
Validation harness: PASS
case_count: 10
failed_cases: 0
run_dir: results\validation\20260216T123041Z
```

## Decision

Approve Phase 55 W21-W24:

- TOML authoring is accepted end-to-end for graph compile flows,
- GraphSpec formatting and hashing are deterministic,
- typed port-domain constraints are enforced before simulation,
- JSON/TOML round-trip semantics are covered by explicit equivalence tests.
