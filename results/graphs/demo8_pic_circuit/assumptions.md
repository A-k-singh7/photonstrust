# Graph Compile Assumptions

- profile: pic_circuit
- graph_schema_version: 0.1
- Compilation output is a normalized netlist only (no PIC physics executed in Phase 08).
- The compiler enforces:
  - unique node IDs
  - valid edge endpoints
  - deterministic topological ordering (tie-break by node id)
- Phase 09 will define component models and execute this netlist.
