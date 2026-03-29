"""PIC component library (v1 minimal set).

This module defines small, explicit, unit-tested component models used by
ChipVerify workflows. The v1 philosophy:
- support a small set of common building blocks
- be explicit about assumptions (e.g., unidirectional propagation)
- keep parameters simple and physical (loss in dB, phase in rad)
"""

from __future__ import annotations

import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import jax.numpy as jnp
import numpy as np

from photonstrust.components.pic.touchstone import (
    infer_touchstone_n_ports,
    interpolate_s_matrix,
    load_touchstone,
    load_touchstone_2port,
    load_touchstone_nport,
)

# Phase C component imports are deferred to _register_phase_c_components()
# to avoid circular imports (the component modules import ComponentPorts from
# this module).


@dataclass(frozen=True)
class ComponentPorts:
    in_ports: tuple[str, ...]
    out_ports: tuple[str, ...]


def supported_component_kinds() -> set[str]:
    _register_phase_c_components()
    return set(_LIB.keys())


def component_ports(kind: str, params: dict | None = None) -> ComponentPorts:
    _register_phase_c_components()
    kind = _normalize_kind(kind)
    if kind not in _LIB:
        raise KeyError(f"Unsupported PIC component kind: {kind}")

    if kind == "pic.touchstone_nport":
        if params is None:
            params = {}
        return _touchstone_nport_ports(params)

    if kind == "pic.mmi":
        if params is None:
            params = {}
        from photonstrust.components.pic.mmi import mmi_ports
        return mmi_ports(params)

    if kind == "pic.awg":
        if params is None:
            params = {}
        n_ch = int(params.get("n_channels", 8))
        return ComponentPorts(
            in_ports=("in",),
            out_ports=tuple(f"out{i+1}" for i in range(n_ch)),
        )

    return _LIB[kind]["ports"]  # type: ignore[return-value]


def component_forward_matrix(kind: str, params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Forward propagation matrix mapping input-port amplitudes to output amplitudes.

    Shape: (n_out, n_in), complex dtype.
    """

    _register_phase_c_components()
    kind = _normalize_kind(kind)
    if kind not in _LIB:
        raise KeyError(f"Unsupported PIC component kind: {kind}")
    fn: Callable[[dict, float | None], np.ndarray] = _LIB[kind]["matrix_fn"]  # type: ignore[assignment]
    return fn(params, wavelength_nm)


def component_all_ports(kind: str, params: dict | None = None) -> tuple[str, ...]:
    ports = component_ports(kind, params=params)
    return tuple([*ports.in_ports, *ports.out_ports])


_TOUCHSTONE_SUFFIX_RE = re.compile(r"\.s\d+p$")


def _is_within_root(path_text: str, root_text: str) -> bool:
    try:
        return os.path.commonpath([path_text, root_text]) == root_text
    except ValueError:
        return False


def _workspace_root() -> str:
    return os.path.realpath(os.getcwd())


def _allowed_roots() -> tuple[str, ...]:
    roots = (
        _workspace_root(),
        os.path.realpath(tempfile.gettempdir()),
        os.path.realpath(str(Path.home())),
    )
    return tuple(dict.fromkeys(roots))


def _is_within_allowed_roots(path_text: str) -> bool:
    return any(_is_within_root(path_text, root_text) for root_text in _allowed_roots())


def _resolve_touchstone_root(params: dict, *, kind: str) -> str:
    base_value = params.get("touchstone_root")
    if base_value is None or str(base_value).strip() == "":
        return _workspace_root()

    base_dir = os.path.realpath(os.path.join(_workspace_root(), os.path.expanduser(str(base_value).strip())))
    if not _is_within_allowed_roots(base_dir):
        raise ValueError(f"{kind} touchstone_root must stay within the workspace, home, or temp directories")
    return base_dir


def _resolve_touchstone_path(params: dict, *, kind: str) -> str:
    path_value = params.get("touchstone_path") or params.get("path")
    if not path_value:
        raise ValueError(f"{kind} requires params.touchstone_path (or params.path)")

    base_dir = _resolve_touchstone_root(params, kind=kind)
    resolved = os.path.realpath(os.path.join(base_dir, os.path.expanduser(str(path_value).strip())))
    if not _is_within_root(resolved, base_dir):
        raise ValueError(f"{kind} touchstone_path must resolve within touchstone_root or the current working directory")

    resolved_path = Path(resolved)
    if not resolved_path.is_file():
        raise ValueError(f"{kind} touchstone_path does not exist: {resolved}")
    if not _TOUCHSTONE_SUFFIX_RE.fullmatch(resolved_path.suffix.lower()):
        raise ValueError(f"{kind} touchstone_path must point to a .sNp file")
    return resolved


def component_scattering_matrix(kind: str, params: dict, wavelength_nm: float | None = None) -> np.ndarray:
    """Bidirectional scattering matrix for a component.

    Convention:
    - Let `a[i]` be the complex incident wave into port i (from the connected network).
    - Let `b[i]` be the complex outgoing wave from port i (into the connected network).
    - Then b = S @ a.

    Port ordering is `component_all_ports(kind)`.

    Notes:
    - For v1 native components we assume reciprocity and (by default) no reflections.
    - For Touchstone-imported components we use the full 2x2 S matrix at the evaluated wavelength.
    """

    _register_phase_c_components()
    kind = _normalize_kind(kind)
    ports = component_ports(kind, params=params)
    all_ports = component_all_ports(kind, params=params)

    def _rl_mag(db: float | None) -> float:
        if db is None:
            return 0.0
        db = float(db)
        if not math.isfinite(db):
            return 0.0
        # Return loss definition: RL(dB) = -20 log10 |Gamma|.
        return float(10 ** (-db / 20.0))

    def _port_reflection(
        *,
        rl_key: str,
        phase_key: str,
    ) -> complex:
        rl_db = params.get(rl_key)
        if rl_db is None:
            rl_db = params.get("return_loss_db")
        if rl_db is None:
            return 0.0 + 0.0j

        mag = _rl_mag(rl_db)
        phase = params.get(phase_key)
        if phase is None:
            phase = params.get("reflection_phase_rad")
        phase = float(phase or 0.0)
        return complex(mag * math.cos(phase), mag * math.sin(phase))

    def _assert_passive(smat: np.ndarray) -> None:
        # Passivity: largest eigenvalue of S^H S <= 1.
        h = smat.conj().T @ smat
        vals = np.linalg.eigvalsh(h)
        max_v = float(np.max(np.real(vals)))
        if not math.isfinite(max_v) or max_v > 1.0 + 1e-12:
            raise ValueError(f"Non-passive scattering matrix for kind={kind!r} (max_eig={max_v}).")

    # 2-port elements: allow optional reflections; some kinds may be non-reciprocal.
    if len(ports.in_ports) == 1 and len(ports.out_ports) == 1 and kind not in {"pic.touchstone_2port", "pic.touchstone_nport"}:
        fwd = component_forward_matrix(kind, params, wavelength_nm=wavelength_nm)
        if fwd.shape != (1, 1):
            raise ValueError(f"Expected 1x1 forward matrix for 2-port component (kind={kind})")
        t_fwd = fwd[0, 0]
        t_rev = t_fwd

        if kind == "pic.isolator_2port":
            # Model as a passive, non-reciprocal 2-port with specified isolation.
            il_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
            iso_db = float(params.get("isolation_db", 30.0) or 0.0)
            il_db = max(0.0, il_db)
            iso_db = max(0.0, iso_db)
            mag_rev = float(10 ** (-(il_db + iso_db) / 20.0))
            phi_fwd = math.atan2(t_fwd.imag, t_fwd.real)
            phi_rev = params.get("reverse_phase_rad")
            phi_rev = float(phi_rev) if phi_rev is not None else float(phi_fwd)
            t_rev = complex(mag_rev * math.cos(phi_rev), mag_rev * math.sin(phi_rev))

        r_in = _port_reflection(rl_key="return_loss_in_db", phase_key="reflection_in_phase_rad")
        r_out = _port_reflection(rl_key="return_loss_out_db", phase_key="reflection_out_phase_rad")

        # Port order: [in, out]
        s = jnp.zeros((2, 2), dtype=jnp.complex128)
        s = s.at[0, 0].set(r_in)
        s = s.at[1, 1].set(r_out)
        s = s.at[0, 1].set(t_rev)  # S12
        s = s.at[1, 0].set(t_fwd)  # S21

        if abs(r_in) > 0.0 or abs(r_out) > 0.0 or kind == "pic.isolator_2port":
            try:
                _assert_passive(s)
            except Exception as e:
                if "Abstract tracer value" not in str(e) and "ConcretizationTypeError" not in type(e).__name__:
                    raise
        return s

    if kind == "pic.coupler":
        # Build a 4-port reflectionless reciprocal model from the existing forward matrix.
        # Port order: [in1, in2, out1, out2]
        fwd = component_forward_matrix(kind, params, wavelength_nm=wavelength_nm)
        if fwd.shape != (2, 2):
            raise ValueError("pic.coupler forward matrix must be 2x2")
        s = np.zeros((4, 4), dtype=np.complex128)
        # b_out = M @ a_in
        s[2:4, 0:2] = fwd
        # b_in = M^T @ a_out (reciprocal reverse coupling)
        s[0:2, 2:4] = fwd.T
        return s

    # Phase C multiport components with dedicated scattering models.
    if kind in {"pic.mmi", "pic.y_branch", "pic.crossing", "pic.awg"}:
        scat_fn = _LIB[kind].get("scattering_fn")
        if scat_fn is not None:
            return scat_fn(params, wavelength_nm)
        raise ValueError(f"No scattering function registered for {kind!r}")

    if kind == "pic.touchstone_2port":
        # Use the full S-parameter matrix at the requested wavelength.
        if wavelength_nm is None:
            raise ValueError("pic.touchstone_2port requires wavelength_nm to evaluate S-parameters")
        allow_extrapolation = bool(params.get("allow_extrapolation", False))

        ts_path = _resolve_touchstone_path(params, kind="pic.touchstone_2port")
        data = load_touchstone_2port(ts_path)

        c_m_s = 299_792_458.0
        lam_m = float(wavelength_nm) * 1e-9
        if lam_m <= 0.0:
            raise ValueError("wavelength_nm must be > 0 for touchstone evaluation")
        freq_hz = c_m_s / lam_m
        s = interpolate_s_matrix(data, freq_hz=float(freq_hz), allow_extrapolation=allow_extrapolation)
        if s.shape != (2, 2):
            raise ValueError("Touchstone interpolation returned non-2x2 S matrix")
        return np.array(s, dtype=np.complex128)

    if kind == "pic.touchstone_nport":
        # Use the full S-parameter matrix at the requested wavelength.
        if wavelength_nm is None:
            raise ValueError("pic.touchstone_nport requires wavelength_nm to evaluate S-parameters")

        allow_extrapolation = bool(params.get("allow_extrapolation", False))

        ts_path = _resolve_touchstone_path(params, kind="pic.touchstone_nport")
        n_ports = params.get("n_ports")
        if n_ports is None:
            n_ports = infer_touchstone_n_ports(ts_path)
        if n_ports is None:
            raise ValueError("pic.touchstone_nport requires n_ports or a .sNp filename")
        n_ports = int(n_ports)
        if n_ports <= 0:
            raise ValueError("pic.touchstone_nport n_ports must be > 0")

        data = load_touchstone_nport(ts_path, n_ports=n_ports)
        if int(data.n_ports) != int(n_ports):
            raise ValueError(f"Touchstone n_ports mismatch: expected {n_ports}, got {data.n_ports}")

        c_m_s = 299_792_458.0
        lam_m = float(wavelength_nm) * 1e-9
        if lam_m <= 0.0:
            raise ValueError("wavelength_nm must be > 0 for touchstone evaluation")
        freq_hz = c_m_s / lam_m
        s_full = interpolate_s_matrix(data, freq_hz=float(freq_hz), allow_extrapolation=allow_extrapolation)
        if s_full.shape != (n_ports, n_ports):
            raise ValueError("Touchstone interpolation returned wrong S matrix shape")

        ports = component_ports(kind, params=params)
        port_list = list([*ports.in_ports, *ports.out_ports])
        idx = []
        for p in port_list:
            if not str(p).lower().startswith("p"):
                raise ValueError("pic.touchstone_nport ports must be named like 'p1', 'p2', ...")
            try:
                k = int(str(p)[1:])
            except Exception as exc:
                raise ValueError(f"Invalid touchstone port name: {p!r}") from exc
            if k < 1 or k > n_ports:
                raise ValueError(f"Touchstone port out of range: {p!r}")
            idx.append(k - 1)
        s_perm = np.array(s_full, dtype=np.complex128)[np.ix_(idx, idx)]
        return s_perm

    raise ValueError(
        f"No scattering model available for kind={kind!r} with ports={all_ports}. "
        "(Only 2-port elements, pic.coupler, and pic.touchstone_2port are supported in v1 scattering mode.)"
    )


def component_power_transmission(kind: str, params: dict, wavelength_nm: float | None = None) -> float:
    """Return scalar power transmission for 2-port components.

    This is used by the fast chain solver. For multiport components (e.g.,
    couplers) this raises.
    """

    ports = component_ports(kind, params=params)
    if len(ports.in_ports) != 1 or len(ports.out_ports) != 1:
        raise ValueError(f"power_transmission is defined for 2-port components only (kind={kind})")
    mat = component_forward_matrix(kind, params, wavelength_nm=wavelength_nm)
    if mat.shape != (1, 1):
        raise ValueError(f"Expected 1x1 forward matrix for 2-port component (kind={kind})")
    t = complex(mat[0, 0])
    return float(abs(t) ** 2)


def _normalize_kind(kind: str) -> str:
    return str(kind).strip().lower()


def _eta_from_loss_db(loss_db: float) -> float:
    return 10 ** (-max(0.0, float(loss_db)) / 10.0)


def _phase_from_params(params: dict, wavelength_nm: float | None) -> float:
    if "phase_rad" in params and params["phase_rad"] is not None:
        return float(params["phase_rad"])
    if wavelength_nm is None:
        return 0.0
    if "n_eff" in params and params["n_eff"] is not None and "length_um" in params and params["length_um"] is not None:
        n_eff = float(params["n_eff"])
        length_um = float(params["length_um"])
        lam_m = float(wavelength_nm) * 1e-9
        length_m = length_um * 1e-6
        if lam_m <= 0:
            return 0.0
        return float(2.0 * math.pi * n_eff * length_m / lam_m)
    return 0.0


def _two_port_scalar_matrix(t: complex) -> jnp.ndarray:
    return jnp.array([[t]], dtype=jnp.complex128)


def _matrix_waveguide(params: dict, wavelength_nm: float | None) -> np.ndarray:
    length_um = float(params.get("length_um", 0.0) or 0.0)
    loss_db_per_cm = float(params.get("loss_db_per_cm", 0.0) or 0.0)
    length_cm = max(0.0, length_um) / 1e4
    loss_db = max(0.0, loss_db_per_cm) * length_cm
    eta = _eta_from_loss_db(loss_db)
    phi = _phase_from_params(params, wavelength_nm)
    t = math.sqrt(eta) * complex(math.cos(phi), math.sin(phi))
    return _two_port_scalar_matrix(t)


def _matrix_insertion_loss_2port(params: dict, wavelength_nm: float | None) -> np.ndarray:
    loss_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    eta = _eta_from_loss_db(loss_db)
    phi = _phase_from_params(params, wavelength_nm)
    t = math.sqrt(eta) * complex(math.cos(phi), math.sin(phi))
    return _two_port_scalar_matrix(t)


def _matrix_phase_shifter(params: dict, wavelength_nm: float | None) -> jnp.ndarray:
    # Explicit phase control is the core; loss is optional.
    # Uses jnp functions to enable Autodiff through phase_rad.
    phi = params.get("phase_rad", 0.0)
    phi = phi if phi is not None else 0.0

    loss_db = params.get("insertion_loss_db", 0.0)
    loss_db = float(loss_db) if loss_db is not None else 0.0

    eta = _eta_from_loss_db(loss_db)
    t = jnp.sqrt(eta) * (jnp.cos(phi) + 1j * jnp.sin(phi))
    return jnp.array([[t]], dtype=jnp.complex128)


def _matrix_ring(params: dict, wavelength_nm: float | None) -> np.ndarray:
    """All-pass ring resonator (2-port) with a backwards-compatible fallback.

    Backwards compatibility: if the caller provides only `insertion_loss_db`, we
    keep the v0.1 placeholder behavior (lumped 2-port loss).

    Resonator mode: enable by providing any of:
      - coupling_ratio
      - radius_um
      - round_trip_length_um
      - n_eff
      - loss_db_per_cm

    Model (all-pass through transfer):
      H = (r - a*exp(-j*phi)) / (1 - r*a*exp(-j*phi))
    """

    has_resonator_params = any(
        k in params and params.get(k) is not None
        for k in ("coupling_ratio", "radius_um", "round_trip_length_um", "n_eff", "loss_db_per_cm")
    )
    if not has_resonator_params:
        return _matrix_insertion_loss_2port(params, wavelength_nm)

    if wavelength_nm is None:
        raise ValueError("pic.ring requires wavelength_nm in resonator mode")

    kappa = float(params.get("coupling_ratio", 0.002) or 0.0)
    kappa = min(1.0, max(0.0, kappa))
    r = math.sqrt(max(0.0, 1.0 - kappa))

    if params.get("round_trip_length_um") is not None:
        L_rt_um = float(params.get("round_trip_length_um") or 0.0)
    elif params.get("radius_um") is not None:
        radius_um = float(params.get("radius_um") or 0.0)
        L_rt_um = 2.0 * math.pi * max(0.0, radius_um)
    else:
        raise ValueError("pic.ring resonator mode requires radius_um or round_trip_length_um")
    if L_rt_um <= 0.0:
        raise ValueError("pic.ring round-trip length must be > 0")

    n_eff = params.get("n_eff")
    if n_eff is None:
        raise ValueError("pic.ring resonator mode requires n_eff")
    n_eff = float(n_eff)
    if not math.isfinite(n_eff) or n_eff <= 0.0:
        raise ValueError("pic.ring n_eff must be finite and > 0")

    loss_db_per_cm = float(params.get("loss_db_per_cm", 0.0) or 0.0)
    length_cm = L_rt_um / 1e4
    loss_db_rt = max(0.0, loss_db_per_cm) * length_cm

    # Round-trip amplitude transmission.
    a_rt = math.sqrt(_eta_from_loss_db(loss_db_rt))

    lam_m = float(wavelength_nm) * 1e-9
    if lam_m <= 0.0:
        raise ValueError("wavelength_nm must be > 0 for pic.ring")
    L_m = L_rt_um * 1e-6
    phi = float(2.0 * math.pi * n_eff * L_m / lam_m)
    e = complex(math.cos(phi), -math.sin(phi))  # exp(-j*phi)

    num = complex(r) - complex(a_rt) * e
    den = 1.0 - complex(r) * complex(a_rt) * e
    if abs(den) < 1e-18:
        # Avoid numeric blow-ups in pathological critical points.
        t = 0.0 + 0.0j
    else:
        t = num / den

    # Optional extra insertion loss on the bus.
    il_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    eta_bus = _eta_from_loss_db(il_db)
    t = math.sqrt(eta_bus) * t

    return _two_port_scalar_matrix(t)


def _matrix_coupler(params: dict, wavelength_nm: float | None) -> jnp.ndarray:
    # Unidirectional 2x2 coupler model (no reflections, symmetric).
    # out = M @ in, where in=[in1,in2], out=[out1,out2]
    kappa = params.get("coupling_ratio", 0.5)
    kappa = kappa if kappa is not None else 0.5
    kappa = jnp.clip(kappa, 0.0, 1.0)

    il_db = float(params.get("insertion_loss_db", 0.0) or 0.0)
    eta = _eta_from_loss_db(il_db)

    t = jnp.sqrt(1.0 - kappa)
    k = jnp.sqrt(kappa)
    m = jnp.array([[t, 1j * k], [1j * k, t]], dtype=jnp.complex128)
    return jnp.sqrt(eta) * m


def _matrix_touchstone_2port(params: dict, wavelength_nm: float | None) -> np.ndarray:
    # Touchstone S-parameter import (2-port), mapped to a forward scalar transfer.
    # Default mapping: S21 (port1 -> port2) == out due to in.
    if wavelength_nm is None:
        raise ValueError("pic.touchstone_2port requires wavelength_nm to evaluate S-parameters")

    forward = str(params.get("forward", "s21") or "s21").strip().lower()
    allow_extrapolation = bool(params.get("allow_extrapolation", False))

    # Resolve to an absolute path for stable caching and provenance behavior.
    ts_path = _resolve_touchstone_path(params, kind="pic.touchstone_2port")
    data = load_touchstone_2port(ts_path)

    c_m_s = 299_792_458.0
    lam_m = float(wavelength_nm) * 1e-9
    if lam_m <= 0.0:
        raise ValueError("wavelength_nm must be > 0 for touchstone evaluation")
    freq_hz = c_m_s / lam_m

    s = interpolate_s_matrix(data, freq_hz=float(freq_hz), allow_extrapolation=allow_extrapolation)
    if forward == "s21":
        t = complex(s[1, 0])
    elif forward == "s12":
        t = complex(s[0, 1])
    else:
        raise ValueError("pic.touchstone_2port param 'forward' must be 's21' or 's12'")

    return _two_port_scalar_matrix(t)


def _touchstone_nport_ports(params: dict) -> ComponentPorts:
    ts_path = _resolve_touchstone_path(params, kind="pic.touchstone_nport")

    n_ports = params.get("n_ports")
    if n_ports is None:
        n_ports = infer_touchstone_n_ports(ts_path)
    if n_ports is None:
        raise ValueError("pic.touchstone_nport requires n_ports or a .sNp filename")
    n_ports = int(n_ports)
    if n_ports <= 0:
        raise ValueError("pic.touchstone_nport n_ports must be > 0")

    in_ports = params.get("in_ports")
    out_ports = params.get("out_ports")
    if in_ports is None and out_ports is None:
        if n_ports % 2 != 0:
            raise ValueError("pic.touchstone_nport requires in_ports/out_ports for odd n_ports")
        half = n_ports // 2
        in_ports = [f"p{i}" for i in range(1, half + 1)]
        out_ports = [f"p{i}" for i in range(half + 1, n_ports + 1)]
    else:
        if in_ports is None or out_ports is None:
            raise ValueError("pic.touchstone_nport requires both in_ports and out_ports when provided")
        if not isinstance(in_ports, list) or not isinstance(out_ports, list):
            raise ValueError("pic.touchstone_nport in_ports/out_ports must be arrays")
        in_ports = [str(p) for p in in_ports]
        out_ports = [str(p) for p in out_ports]

    if not in_ports or not out_ports:
        raise ValueError("pic.touchstone_nport in_ports and out_ports must be non-empty")

    allowed = {f"p{i}" for i in range(1, n_ports + 1)}
    all_ports = [*in_ports, *out_ports]
    if any(p not in allowed for p in all_ports):
        raise ValueError(f"pic.touchstone_nport ports must be named p1..p{n_ports}")
    if len(set(in_ports)) != len(in_ports) or len(set(out_ports)) != len(out_ports):
        raise ValueError("pic.touchstone_nport port lists must not contain duplicates")
    if set(in_ports) & set(out_ports):
        raise ValueError("pic.touchstone_nport in_ports and out_ports must be disjoint")
    if set(all_ports) != allowed:
        raise ValueError("pic.touchstone_nport in_ports+out_ports must cover all Touchstone ports")

    return ComponentPorts(in_ports=tuple(in_ports), out_ports=tuple(out_ports))


def _matrix_touchstone_nport(params: dict, wavelength_nm: float | None) -> np.ndarray:
    if wavelength_nm is None:
        raise ValueError("pic.touchstone_nport requires wavelength_nm to evaluate S-parameters")

    allow_extrapolation = bool(params.get("allow_extrapolation", False))

    ts_path = _resolve_touchstone_path(params, kind="pic.touchstone_nport")
    n_ports = params.get("n_ports")
    if n_ports is None:
        n_ports = infer_touchstone_n_ports(ts_path)
    if n_ports is None:
        raise ValueError("pic.touchstone_nport requires n_ports or a .sNp filename")
    n_ports = int(n_ports)
    if n_ports <= 0:
        raise ValueError("pic.touchstone_nport n_ports must be > 0")

    data = load_touchstone_nport(ts_path, n_ports=n_ports)

    c_m_s = 299_792_458.0
    lam_m = float(wavelength_nm) * 1e-9
    if lam_m <= 0.0:
        raise ValueError("wavelength_nm must be > 0 for touchstone evaluation")
    freq_hz = c_m_s / lam_m
    s_full = interpolate_s_matrix(data, freq_hz=float(freq_hz), allow_extrapolation=allow_extrapolation)
    if s_full.shape != (n_ports, n_ports):
        raise ValueError("Touchstone interpolation returned wrong S matrix shape")

    ports = _touchstone_nport_ports(params)
    port_list = list([*ports.in_ports, *ports.out_ports])
    idx = [int(str(p)[1:]) - 1 for p in port_list]
    s_perm = np.array(s_full, dtype=np.complex128)[np.ix_(idx, idx)]

    n_in = len(ports.in_ports)
    # Forward-only approximation: map incident waves on in_ports to outgoing waves on out_ports.
    return np.array(s_perm[n_in:, :n_in], dtype=np.complex128)


_LIB: dict[str, dict] = {
    "pic.waveguide": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_waveguide,
    },
    "pic.grating_coupler": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_insertion_loss_2port,
    },
    "pic.edge_coupler": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_insertion_loss_2port,
    },
    "pic.phase_shifter": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_phase_shifter,
    },
    "pic.isolator_2port": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_insertion_loss_2port,
    },
    # v1 ring: treated as a 2-port lumped element (filter physics planned later).
    "pic.ring": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_ring,
    },
    "pic.coupler": {
        "ports": ComponentPorts(in_ports=("in1", "in2"), out_ports=("out1", "out2")),
        "matrix_fn": _matrix_coupler,
    },
    "pic.touchstone_2port": {
        "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
        "matrix_fn": _matrix_touchstone_2port,
    },
    "pic.touchstone_nport": {
        # Ports are derived from params (see _touchstone_nport_ports).
        "ports": ComponentPorts(in_ports=(), out_ports=()),
        "matrix_fn": _matrix_touchstone_nport,
    },
}


_PHASE_C_REGISTERED = False


def _register_phase_c_components() -> None:
    """Lazily register Phase C components to avoid circular imports."""
    global _PHASE_C_REGISTERED  # noqa: PLW0603
    if _PHASE_C_REGISTERED:
        return
    _PHASE_C_REGISTERED = True

    from photonstrust.components.pic.mmi import (
        mmi_forward_matrix,
        mmi_scattering_matrix,
    )
    from photonstrust.components.pic.y_branch import (
        y_branch_forward_matrix,
        y_branch_scattering_matrix,
    )
    from photonstrust.components.pic.crossing import (
        crossing_forward_matrix,
        crossing_scattering_matrix,
    )
    from photonstrust.components.pic.mzm import (
        mzm_forward_matrix,
        mzm_scattering_matrix,
    )
    from photonstrust.components.pic.photodetector import (
        photodetector_forward_matrix,
        photodetector_scattering_matrix,
    )
    from photonstrust.components.pic.awg import (
        awg_forward_matrix,
        awg_scattering_matrix,
    )
    from photonstrust.components.pic.heater import (
        heater_forward_matrix,
        heater_scattering_matrix,
    )
    from photonstrust.components.pic.ssc import (
        ssc_forward_matrix,
        ssc_scattering_matrix,
    )

    _LIB.update({
        "pic.mmi": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out1", "out2")),
            "matrix_fn": mmi_forward_matrix,
            "scattering_fn": mmi_scattering_matrix,
        },
        "pic.y_branch": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out1", "out2")),
            "matrix_fn": y_branch_forward_matrix,
            "scattering_fn": y_branch_scattering_matrix,
        },
        "pic.crossing": {
            "ports": ComponentPorts(in_ports=("in1", "in2"), out_ports=("out1", "out2")),
            "matrix_fn": crossing_forward_matrix,
            "scattering_fn": crossing_scattering_matrix,
        },
        "pic.mzm": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
            "matrix_fn": mzm_forward_matrix,
            "scattering_fn": mzm_scattering_matrix,
        },
        "pic.photodetector": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
            "matrix_fn": photodetector_forward_matrix,
            "scattering_fn": photodetector_scattering_matrix,
        },
        "pic.awg": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out1", "out2", "out3", "out4", "out5", "out6", "out7", "out8")),
            "matrix_fn": awg_forward_matrix,
            "scattering_fn": awg_scattering_matrix,
        },
        "pic.heater": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
            "matrix_fn": heater_forward_matrix,
            "scattering_fn": heater_scattering_matrix,
        },
        "pic.ssc": {
            "ports": ComponentPorts(in_ports=("in",), out_ports=("out",)),
            "matrix_fn": ssc_forward_matrix,
            "scattering_fn": ssc_scattering_matrix,
        },
    })


# ---------------------------------------------------------------------------
# Class-based component registry (auto-discovered from PICComponentBase)
# ---------------------------------------------------------------------------

_COMPONENT_CLASSES: dict[str, type] = {}
_CLASSES_DISCOVERED = False


def _discover_component_classes() -> None:
    """Auto-discover all PICComponentBase subclasses from component modules."""
    global _CLASSES_DISCOVERED  # noqa: PLW0603
    if _CLASSES_DISCOVERED:
        return
    _CLASSES_DISCOVERED = True

    _register_phase_c_components()

    from photonstrust.components.pic.base import PICComponentBase  # noqa: E402

    # Force import of inline wrappers so their subclasses are visible.
    import photonstrust.components.pic.inline_components  # noqa: F401

    for cls in PICComponentBase.__subclasses__():
        meta = cls.meta()
        _COMPONENT_CLASSES[meta.kind] = cls


def component_class(kind: str) -> type | None:
    """Return the PICComponentBase subclass for *kind*, or ``None``."""
    if not _CLASSES_DISCOVERED:
        _discover_component_classes()
    return _COMPONENT_CLASSES.get(_normalize_kind(kind))


def all_component_classes() -> dict[str, type]:
    """Return a dict mapping kind strings to PICComponentBase subclasses."""
    if not _CLASSES_DISCOVERED:
        _discover_component_classes()
    return dict(_COMPONENT_CLASSES)
