"""PDK (Process Design Kit) abstractions.

This is a lightweight contract layer so PhotonTrust can be:
- PDK-aware (design rules, layer conventions, constraints), and
- extensible (private PDK plugins without forking the core).

The v0 implementation is intentionally minimal and file-format agnostic.
"""

from photonstrust.pdk.adapters import (
    PDK_ADAPTER_CONTRACT_SCHEMA_VERSION,
    PDKAdapterContract,
    PDKCapabilityMatrix,
    PDKPayloadResolver,
    default_pdk_capability_matrix,
    validate_pdk_adapter_contract,
)
from photonstrust.pdk.registry import (
    PDK,
    RegistryPDKAdapter,
    get_pdk,
    load_pdk_manifest,
    pdk_capability_matrix,
    resolve_pdk_contract,
)

__all__ = [
    "PDK",
    "PDK_ADAPTER_CONTRACT_SCHEMA_VERSION",
    "PDKAdapterContract",
    "PDKCapabilityMatrix",
    "PDKPayloadResolver",
    "RegistryPDKAdapter",
    "default_pdk_capability_matrix",
    "get_pdk",
    "load_pdk_manifest",
    "pdk_capability_matrix",
    "resolve_pdk_contract",
    "validate_pdk_adapter_contract",
]
