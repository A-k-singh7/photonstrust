"""Platform-specific quantum memory models.

Provides physics-based decoherence models for specific memory platforms
with published experimental parameters.

Key references:
    - Bradley et al., PRX 9, 031045 (2019) -- NV diamond (T2 > 1s)
    - Stephenson et al., PRL 124, 110501 (2020) -- trapped ion networking
    - Afzelius et al., PRA 79, 052329 (2009) -- AFC rare-earth memories
    - Heshami et al., J. Mod. Opt. 63, 2005 (2016) -- memory review

Platform models:
    - NV diamond: stretched exponential decoherence
    - Trapped ion: exponential T2 decay with high gate fidelity
    - Rare-earth AFC: atomic frequency comb with bandwidth-dependent efficiency
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from photonstrust.physics.memory import MemoryStats


@dataclass(frozen=True)
class PlatformMemoryProfile:
    """Platform-specific quantum memory profile."""
    platform: str
    T1_s: float                # relaxation time (seconds)
    T2_s: float                # coherence time (seconds)
    gate_fidelity: float       # single-qubit gate fidelity
    read_efficiency: float     # memory read-out efficiency
    write_efficiency: float    # memory write (storage) efficiency
    operating_temp_K: float    # operating temperature (Kelvin)


# ---------------------------------------------------------------------------
# Platform presets from published experiments
# ---------------------------------------------------------------------------

PLATFORM_PRESETS: dict[str, PlatformMemoryProfile] = {
    "nv_diamond": PlatformMemoryProfile(
        platform="nv_diamond",
        T1_s=3600.0,           # T1 >> T2 for NV at low temp
        T2_s=1.58,             # Bradley et al. PRX 9, 031045 (2019)
        gate_fidelity=0.999,   # single-qubit gate
        read_efficiency=0.95,
        write_efficiency=0.80,
        operating_temp_K=4.0,  # cryogenic
    ),
    "trapped_ion_171yb": PlatformMemoryProfile(
        platform="trapped_ion_171yb",
        T1_s=float("inf"),     # hyperfine qubit, no T1 decay
        T2_s=600.0,            # ~10 min coherence (Wang et al. 2021)
        gate_fidelity=0.9999,  # high-fidelity gates
        read_efficiency=0.998,
        write_efficiency=0.99,
        operating_temp_K=300.0,  # room temp (ion trap)
    ),
    "trapped_ion_40ca": PlatformMemoryProfile(
        platform="trapped_ion_40ca",
        T1_s=1.168,            # optical qubit lifetime
        T2_s=0.05,             # limited by magnetic field noise
        gate_fidelity=0.999,
        read_efficiency=0.99,
        write_efficiency=0.95,
        operating_temp_K=300.0,
    ),
    "rare_earth_151eu_yso": PlatformMemoryProfile(
        platform="rare_earth_151eu_yso",
        T1_s=10800.0,          # 3 hours (Ma et al. 2021)
        T2_s=1.0,              # spin echo T2
        gate_fidelity=0.95,
        read_efficiency=0.10,  # AFC limited
        write_efficiency=0.30,
        operating_temp_K=3.0,  # cryogenic
    ),
    "rare_earth_167er_yso": PlatformMemoryProfile(
        platform="rare_earth_167er_yso",
        T1_s=100.0,
        T2_s=0.001,            # 1 ms at zero field
        gate_fidelity=0.90,
        read_efficiency=0.05,
        write_efficiency=0.20,
        operating_temp_K=1.5,
    ),
}


# ---------------------------------------------------------------------------
# NV diamond memory
# ---------------------------------------------------------------------------

def nv_diamond_memory(
    wait_time_s: float,
    *,
    T2_s: float = 1.58,
    stretch_exponent: float = 1.5,
    T1_s: float = 3600.0,
    read_efficiency: float = 0.95,
    write_efficiency: float = 0.80,
) -> MemoryStats:
    """NV diamond quantum memory with stretched exponential decoherence.

    The NV center electron spin in diamond exhibits a stretched
    exponential decay of coherence:

        F(t) = 0.5 + 0.5 * exp(-(t/T2)^n)

    where n is the stretch exponent (typically 1-3 depending on the
    dynamical decoupling sequence used).

    Args:
        wait_time_s: Storage time in seconds
        T2_s: Coherence time (default: 1.58s from Bradley et al.)
        stretch_exponent: Stretch parameter n (default: 1.5)
        T1_s: Relaxation time
        read_efficiency: Read-out efficiency
        write_efficiency: Write (storage) efficiency

    Returns:
        MemoryStats with fidelity and efficiency

    Ref: Bradley et al., PRX 9, 031045 (2019), Fig. 4
    """
    t = max(0.0, float(wait_time_s))
    T2 = max(1e-12, float(T2_s))
    n = max(0.1, float(stretch_exponent))

    # Stretched exponential decoherence
    coherence = math.exp(-((t / T2) ** n))

    # T1 relaxation (population decay)
    T1 = max(1e-12, float(T1_s))
    t1_decay = math.exp(-t / T1)

    fidelity = 0.5 + 0.5 * coherence * t1_decay
    p_retrieve = write_efficiency * read_efficiency * t1_decay

    return MemoryStats(
        p_store=write_efficiency,
        p_retrieve=max(0.0, min(1.0, p_retrieve)),
        fidelity=max(0.5, min(1.0, fidelity)),
        variance_fidelity=0.0,
        backend="nv_diamond_analytic",
        diagnostics={
            "wait_time_s": t,
            "T2_s": T2,
            "T1_s": T1,
            "stretch_exponent": n,
            "coherence_decay": coherence,
            "t1_decay": t1_decay,
        },
    )


# ---------------------------------------------------------------------------
# Trapped ion memory
# ---------------------------------------------------------------------------

def trapped_ion_memory(
    wait_time_s: float,
    *,
    T2_s: float = 600.0,
    T1_s: float | None = None,
    gate_fidelity: float = 0.9999,
    read_efficiency: float = 0.998,
    write_efficiency: float = 0.99,
) -> MemoryStats:
    """Trapped ion quantum memory.

    Hyperfine qubits in trapped ions offer extremely long coherence
    times (T2 ~ 10 min for 171Yb+). The decoherence is exponential:

        F(t) = 0.5 + 0.5 * exp(-t/T2)

    For hyperfine qubits, T1 is effectively infinite.

    Args:
        wait_time_s: Storage time in seconds
        T2_s: Coherence time (default: 600s for 171Yb+)
        T1_s: Relaxation time (None = infinite)
        gate_fidelity: Single-qubit gate fidelity
        read_efficiency: State readout efficiency
        write_efficiency: State preparation efficiency

    Returns:
        MemoryStats with fidelity and efficiency

    Ref: Stephenson et al., PRL 124, 110501 (2020)
    """
    t = max(0.0, float(wait_time_s))
    T2 = max(1e-12, float(T2_s))

    coherence = math.exp(-t / T2)

    if T1_s is not None:
        T1 = max(1e-12, float(T1_s))
        t1_decay = math.exp(-t / T1)
    else:
        t1_decay = 1.0  # infinite T1

    fidelity = 0.5 + 0.5 * coherence * t1_decay * gate_fidelity
    p_retrieve = write_efficiency * read_efficiency * t1_decay

    return MemoryStats(
        p_store=write_efficiency,
        p_retrieve=max(0.0, min(1.0, p_retrieve)),
        fidelity=max(0.5, min(1.0, fidelity)),
        variance_fidelity=0.0,
        backend="trapped_ion_analytic",
        diagnostics={
            "wait_time_s": t,
            "T2_s": T2,
            "T1_s": T1_s,
            "gate_fidelity": gate_fidelity,
            "coherence_decay": coherence,
            "t1_decay": t1_decay,
        },
    )


# ---------------------------------------------------------------------------
# Rare-earth AFC memory
# ---------------------------------------------------------------------------

def rare_earth_afc_memory(
    wait_time_s: float,
    *,
    T2_s: float = 1.0,
    T1_s: float = 10800.0,
    optical_depth: float = 3.0,
    finesse: float = 5.0,
    bandwidth_mhz: float = 10.0,
    read_efficiency: float = 0.10,
    write_efficiency: float = 0.30,
) -> MemoryStats:
    """Rare-earth atomic frequency comb (AFC) quantum memory.

    The AFC memory efficiency is determined by the comb parameters:

        eta_AFC = d_eff^2 * exp(-d_eff) * exp(-7/F^2)

    where d_eff is the effective optical depth of the comb teeth and
    F is the finesse of the AFC (ratio of tooth spacing to tooth width).

    For storage and retrieval:
        - Write: absorption into the AFC comb structure
        - Storage: spin-wave storage with coherence time T2
        - Read: re-emission after controlled rephasing

    Args:
        wait_time_s: Storage time in seconds
        T2_s: Spin coherence time
        T1_s: Population lifetime
        optical_depth: Total optical depth of the medium
        finesse: AFC finesse (tooth spacing / tooth width)
        bandwidth_mhz: AFC bandwidth in MHz
        read_efficiency: Retrieval efficiency
        write_efficiency: Absorption efficiency

    Returns:
        MemoryStats with AFC-specific efficiency and fidelity

    Ref: Afzelius et al., PRA 79, 052329 (2009), Eq. (3)
    """
    t = max(0.0, float(wait_time_s))
    T2 = max(1e-12, float(T2_s))
    T1 = max(1e-12, float(T1_s))
    F = max(1.0, float(finesse))
    d = max(0.0, float(optical_depth))

    # AFC absorption efficiency
    d_eff = d / F  # effective optical depth per tooth
    if d_eff > 0:
        eta_afc = d_eff ** 2 * math.exp(-d_eff) * math.exp(-7.0 / (F ** 2))
    else:
        eta_afc = 0.0
    eta_afc = max(0.0, min(1.0, eta_afc))

    # Coherence decay during storage
    coherence = math.exp(-t / T2)
    t1_decay = math.exp(-t / T1)

    fidelity = 0.5 + 0.5 * coherence * t1_decay

    # Total retrieval efficiency
    p_retrieve = write_efficiency * eta_afc * read_efficiency * t1_decay

    return MemoryStats(
        p_store=write_efficiency * eta_afc,
        p_retrieve=max(0.0, min(1.0, p_retrieve)),
        fidelity=max(0.5, min(1.0, fidelity)),
        variance_fidelity=0.0,
        backend="rare_earth_afc_analytic",
        diagnostics={
            "wait_time_s": t,
            "T2_s": T2,
            "T1_s": T1,
            "optical_depth": d,
            "finesse": F,
            "d_eff": d_eff,
            "eta_afc": eta_afc,
            "coherence_decay": coherence,
            "t1_decay": t1_decay,
            "bandwidth_mhz": bandwidth_mhz,
        },
    )
