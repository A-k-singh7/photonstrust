"""Backward-compatible imports for generic CLI sealed backend helpers.

Keep this module as a thin compatibility shim; canonical implementations live in
`photonstrust.layout.pic.generic_cli_sealed_runner`.
"""

from photonstrust.layout.pic.generic_cli_sealed_runner import GenericCLIBackendResult
from photonstrust.layout.pic.generic_cli_sealed_runner import run_generic_cli_backend

__all__ = ["GenericCLIBackendResult", "run_generic_cli_backend"]
