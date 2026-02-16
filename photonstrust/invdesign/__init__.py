"""Inverse design (v0).

This package provides "design synthesis" primitives that take objectives and
produce component/circuit parameters plus evidence artifacts.

v0 deliberately uses lightweight deterministic search (grid / coordinate) so it
works without heavy dependencies. Backends like adjoint solvers can be added as
optional plugins later.
"""

from photonstrust.invdesign.coupler_ratio import inverse_design_coupler_ratio
from photonstrust.invdesign.mzi_phase import inverse_design_mzi_phase
from photonstrust.invdesign.plugin_boundary import resolve_invdesign_solver_metadata

__all__ = ["inverse_design_coupler_ratio", "inverse_design_mzi_phase", "resolve_invdesign_solver_metadata"]
