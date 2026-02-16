"""PIC layout hooks (v0.1).

This package defines a deterministic "graph -> layout artifacts" seam.

Design goals:
- Keep the open-core install lightweight (no hard dependency on gdsfactory/KLayout).
- Always emit route/port sidecars for downstream checks (e.g., Performance DRC).
- Optionally emit GDS and run external layout checks when tools are available.
"""

