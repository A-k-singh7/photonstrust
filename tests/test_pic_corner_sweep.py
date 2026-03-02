from __future__ import annotations

import copy
import dataclasses
import inspect
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

from photonstrust.benchmarks.schema import validate_instance
from photonstrust.pdk.registry import load_pdk_manifest

corner_sweep_mod: Any | None = None
perturbation_mod: Any | None = None
_RUNTIME_SKIP_REASONS: list[str] = []

try:
    import photonstrust.pic.corner_sweep as corner_sweep_mod
except Exception as exc:  # pragma: no cover - optional cross-lane module
    _RUNTIME_SKIP_REASONS.append(f"corner sweep runtime API unavailable: {exc}")

try:
    import photonstrust.pic.perturbation as perturbation_mod
except Exception as exc:  # pragma: no cover - optional cross-lane module
    _RUNTIME_SKIP_REASONS.append(f"perturbation runtime API unavailable: {exc}")

run_corner_sweep = getattr(corner_sweep_mod, "run_corner_sweep", None)
compute_sensitivity_rank = getattr(corner_sweep_mod, "compute_sensitivity_rank", None)
classify_risk_level = getattr(corner_sweep_mod, "classify_risk_level", None)
perturb_netlist = getattr(perturbation_mod, "perturb_netlist", None)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_GRAPH_PATH = REPO_ROOT / "graphs" / "demo_qkd_transmitter.json"


@pytest.fixture(autouse=True)
def _require_m4_runtime_apis() -> None:
    if _RUNTIME_SKIP_REASONS:
        pytest.skip("; ".join(_RUNTIME_SKIP_REASONS))
    if run_corner_sweep is None or compute_sensitivity_rank is None or classify_risk_level is None:
        pytest.skip("corner sweep runtime API surface is incomplete")
    if perturb_netlist is None:
        pytest.skip("perturbation runtime API surface is incomplete")


def _to_dict(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    if dataclasses.is_dataclass(payload):
        raw = dataclasses.asdict(payload)
        assert isinstance(raw, dict)
        return raw
    to_dict = getattr(payload, "to_dict", None)
    if callable(to_dict):
        raw = to_dict()
        if isinstance(raw, dict):
            return dict(raw)
    if hasattr(payload, "__dict__"):
        return dict(getattr(payload, "__dict__"))
    raise TypeError(f"Expected dict-like payload, got: {type(payload)!r}")


def _discover_corner_pdk_manifest() -> Path | None:
    pdk_dir = REPO_ROOT / "configs" / "pdks"
    candidates = sorted(pdk_dir.glob("*.json"), key=lambda p: p.name.lower())
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if isinstance(payload.get("process_corners"), dict):
            return path
        if isinstance(payload.get("corner_sets"), dict):
            return path
    for path in candidates:
        name_lc = path.name.lower()
        if "corner" in name_lc:
            return path
    return None


def _manifest_name(manifest_path: Path) -> str | None:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    name = str(payload.get("name") or "").strip()
    return name or None


def _make_process_params(**overrides: float) -> dict[str, float]:
    params: dict[str, float] = {
        "waveguide_width_nm": 0.0,
        "coupling_gap_nm": 0.0,
        "propagation_loss_db_per_cm": 1.0,
    }
    params.update({str(k): float(v) for k, v in overrides.items()})

    width = float(params.get("waveguide_width_nm", 0.0))
    gap = float(params.get("coupling_gap_nm", 0.0))
    loss = float(params.get("propagation_loss_db_per_cm", 1.0))
    params.setdefault("delta_waveguide_width_nm", width)
    params.setdefault("width_delta_nm", width)
    params.setdefault("delta_coupling_gap_nm", gap)
    params.setdefault("gap_delta_nm", gap)
    params.setdefault("loss_db_per_cm", loss)
    params.setdefault("waveguide_loss_db_per_cm", loss)
    return params


def _invoke_perturb_netlist(*, netlist: dict[str, Any], process_params: dict[str, Any], pdk: Any) -> dict[str, Any]:
    fn = perturb_netlist
    sig = inspect.signature(fn)
    params = sig.parameters

    kwargs: dict[str, Any] = {}
    if "netlist" in params:
        kwargs["netlist"] = copy.deepcopy(netlist)
    elif "compiled_netlist" in params:
        kwargs["compiled_netlist"] = copy.deepcopy(netlist)
    elif "graph" in params:
        kwargs["graph"] = copy.deepcopy(netlist)

    if "process_params" in params:
        kwargs["process_params"] = dict(process_params)
    elif "corner_params" in params:
        kwargs["corner_params"] = dict(process_params)
    elif "params" in params:
        kwargs["params"] = dict(process_params)

    if "pdk" in params:
        kwargs["pdk"] = pdk
    elif "pdk_name" in params and hasattr(pdk, "name"):
        kwargs["pdk_name"] = str(getattr(pdk, "name"))
    elif "manifest_path" in params and hasattr(pdk, "name"):
        kwargs["manifest_path"] = None

    if kwargs:
        try:
            raw = fn(**kwargs)
            return _to_dict(raw)
        except TypeError:
            pass

    last_exc: Exception | None = None
    for args in (
        (copy.deepcopy(netlist), dict(process_params), pdk),
        (copy.deepcopy(netlist), dict(process_params)),
        (copy.deepcopy(netlist),),
    ):
        try:
            raw = fn(*args)
            return _to_dict(raw)
        except TypeError as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unable to call perturb_netlist")


def _invoke_run_corner_sweep(
    *,
    graph_path: Path,
    pdk_manifest_path: Path,
    output_dir: Path,
    n_monte_carlo: int,
    mc_seed: int,
) -> dict[str, Any]:
    fn = run_corner_sweep
    sig = inspect.signature(fn)
    params = sig.parameters
    pdk_name = _manifest_name(pdk_manifest_path)

    kwargs: dict[str, Any] = {}

    if "graph_path" in params:
        kwargs["graph_path"] = graph_path
    elif "graph" in params:
        kwargs["graph"] = graph_path
    elif "graph_file" in params:
        kwargs["graph_file"] = graph_path

    if "pdk_manifest_path" in params:
        kwargs["pdk_manifest_path"] = pdk_manifest_path
    elif "manifest_path" in params:
        kwargs["manifest_path"] = pdk_manifest_path
    elif "pdk_manifest" in params:
        kwargs["pdk_manifest"] = pdk_manifest_path
    elif "pdk_name" in params and pdk_name is not None:
        kwargs["pdk_name"] = pdk_name
    elif "pdk" in params and pdk_name is not None:
        kwargs["pdk"] = pdk_name

    if "protocol" in params:
        kwargs["protocol"] = "BB84_DECOY"
    elif "protocol_name" in params:
        kwargs["protocol_name"] = "BB84_DECOY"

    if "target_distance_km" in params:
        kwargs["target_distance_km"] = 50.0
    elif "target_distance" in params:
        kwargs["target_distance"] = 50.0

    if "wavelength_nm" in params:
        kwargs["wavelength_nm"] = 1550.0
    elif "wavelength" in params:
        kwargs["wavelength"] = 1550.0

    if "corner_set" in params:
        kwargs["corner_set"] = None
    elif "corners" in params:
        kwargs["corners"] = "all"

    if "n_monte_carlo" in params:
        kwargs["n_monte_carlo"] = int(n_monte_carlo)
    elif "monte_carlo_samples" in params:
        kwargs["monte_carlo_samples"] = int(n_monte_carlo)
    elif "mc_samples" in params:
        kwargs["mc_samples"] = int(n_monte_carlo)

    if "mc_seed" in params:
        kwargs["mc_seed"] = int(mc_seed)
    elif "seed" in params:
        kwargs["seed"] = int(mc_seed)

    if "key_rate_threshold_bps" in params:
        kwargs["key_rate_threshold_bps"] = 1000.0
    elif "threshold_bps" in params:
        kwargs["threshold_bps"] = 1000.0
    elif "threshold" in params:
        kwargs["threshold"] = 1000.0

    if "output_dir" in params:
        kwargs["output_dir"] = output_dir
    elif "output" in params:
        kwargs["output"] = output_dir

    if kwargs:
        try:
            raw = fn(**kwargs)
            return _to_dict(raw)
        except TypeError:
            pass

    last_exc: Exception | None = None
    for args in (
        (graph_path,),
        (graph_path, pdk_name or "aim_photonics"),
    ):
        try:
            raw = fn(*args)
            return _to_dict(raw)
        except TypeError as exc:
            last_exc = exc
            continue
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Unable to call run_corner_sweep")


def _invoke_compute_sensitivity_rank(corner_results: Any, sigma_dict: dict[str, float]) -> list[dict[str, Any]]:
    fn = compute_sensitivity_rank
    sig = inspect.signature(fn)
    params = sig.parameters
    kwargs: dict[str, Any] = {}

    if "corner_results" in params:
        kwargs["corner_results"] = corner_results
    elif "corners" in params:
        kwargs["corners"] = corner_results
    elif "results" in params:
        kwargs["results"] = corner_results

    if "sigma_dict" in params:
        kwargs["sigma_dict"] = dict(sigma_dict)
    elif "sigmas" in params:
        kwargs["sigmas"] = dict(sigma_dict)
    elif "sigma" in params:
        kwargs["sigma"] = dict(sigma_dict)

    if kwargs:
        try:
            raw = fn(**kwargs)
            if isinstance(raw, list):
                return [dict(row) for row in raw if isinstance(row, dict)]
            if isinstance(raw, dict):
                out: list[dict[str, Any]] = []
                for key, value in raw.items():
                    if isinstance(value, dict):
                        row = dict(value)
                        row.setdefault("parameter", str(key))
                        out.append(row)
                return out
        except TypeError:
            pass

    for args in ((corner_results, sigma_dict), (corner_results,), (sigma_dict, corner_results)):
        try:
            raw = fn(*args)
            if isinstance(raw, list):
                return [dict(row) for row in raw if isinstance(row, dict)]
            if isinstance(raw, dict):
                out = []
                for key, value in raw.items():
                    if isinstance(value, dict):
                        row = dict(value)
                        row.setdefault("parameter", str(key))
                        out.append(row)
                return out
        except TypeError:
            continue
    raise RuntimeError("Unable to call compute_sensitivity_rank")


def _invoke_classify_risk_level(corner_results: Any, threshold_bps: float) -> str:
    fn = classify_risk_level
    sig = inspect.signature(fn)
    params = sig.parameters
    kwargs: dict[str, Any] = {}

    if "corner_results" in params:
        kwargs["corner_results"] = corner_results
    elif "corners" in params:
        kwargs["corners"] = corner_results
    elif "results" in params:
        kwargs["results"] = corner_results
    elif "sweep_result" in params:
        kwargs["sweep_result"] = corner_results

    if "threshold_bps" in params:
        kwargs["threshold_bps"] = float(threshold_bps)
    elif "key_rate_threshold_bps" in params:
        kwargs["key_rate_threshold_bps"] = float(threshold_bps)
    elif "threshold" in params:
        kwargs["threshold"] = float(threshold_bps)

    if kwargs:
        try:
            raw = fn(**kwargs)
            return _risk_level_text(raw)
        except TypeError:
            pass

    for args in ((corner_results, threshold_bps), (corner_results,), (threshold_bps, corner_results)):
        try:
            raw = fn(*args)
            return _risk_level_text(raw)
        except TypeError:
            continue
    raise RuntimeError("Unable to call classify_risk_level")


def _risk_level_text(raw: Any) -> str:
    if isinstance(raw, str):
        return raw.strip().upper()
    if isinstance(raw, dict):
        for key in ("risk_level", "level", "classification"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip().upper()
    return str(raw).strip().upper()


def _component_rows(netlist: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("instances", "nodes"):
        maybe = netlist.get(key)
        if isinstance(maybe, list):
            for row in maybe:
                if isinstance(row, dict):
                    rows.append(row)
    return rows


def _find_component(netlist: dict[str, Any], *, component_id: str) -> dict[str, Any]:
    for row in _component_rows(netlist):
        if str(row.get("id") or "").strip() == component_id:
            return row
    raise AssertionError(f"Component not found: {component_id}")


def _numeric_from_mapping(mapping: dict[str, Any], keys: tuple[str, ...]) -> float:
    for key in keys:
        value = mapping.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    raise AssertionError(f"Missing numeric key; expected one of: {keys}")


def _waveguide_total_insertion_loss_db(netlist: dict[str, Any]) -> float:
    total = 0.0
    for row in _component_rows(netlist):
        kind_lc = str(row.get("kind") or "").strip().lower()
        if "waveguide" not in kind_lc and "delay" not in kind_lc:
            continue
        params = row.get("params")
        if not isinstance(params, dict):
            continue
        if "insertion_loss_db" in params:
            total += float(params.get("insertion_loss_db") or 0.0)
        elif "loss_db" in params:
            total += float(params.get("loss_db") or 0.0)
        elif "propagation_loss_db" in params:
            total += float(params.get("propagation_loss_db") or 0.0)
    return total


def _extract_corner_rows(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = result.get("corners")
    if isinstance(raw, dict):
        out: dict[str, dict[str, Any]] = {}
        for key, row in raw.items():
            if isinstance(row, dict):
                out[str(key)] = dict(row)
        if out:
            return out
    if isinstance(raw, list):
        out = {}
        for row in raw:
            if not isinstance(row, dict):
                continue
            name = str(row.get("corner") or row.get("name") or row.get("corner_name") or "").strip()
            if name:
                out[name] = dict(row)
        if out:
            return out
    alt = result.get("corner_results")
    if isinstance(alt, dict):
        out = {}
        for key, row in alt.items():
            if isinstance(row, dict):
                out[str(key)] = dict(row)
        if out:
            return out
    raise AssertionError("Corner rows not found in corner sweep result")


def _extract_key_rate_bps(row: dict[str, Any]) -> float:
    for key in ("key_rate_bps", "secret_key_rate_bps", "keyrate_bps", "r_bps"):
        value = row.get(key)
        if value is None:
            continue
        return float(value)
    maybe_summary = row.get("summary")
    if isinstance(maybe_summary, dict):
        for key in ("key_rate_bps", "secret_key_rate_bps", "keyrate_bps"):
            value = maybe_summary.get(key)
            if value is None:
                continue
            return float(value)
    raise AssertionError("key rate field missing from corner row")


def _extract_yield_fraction(result: dict[str, Any]) -> float:
    monte = result.get("monte_carlo")
    if isinstance(monte, dict):
        for key in ("yield_fraction", "yield", "yield_above_threshold"):
            if key in monte:
                return float(monte.get(key))
    risk = result.get("risk_assessment")
    if isinstance(risk, dict):
        for key in ("yield_above_threshold", "yield_fraction", "yield"):
            if key in risk:
                return float(risk.get(key))
    raise AssertionError("Yield fraction not found in sweep result")


def _extract_monte_summary(result: dict[str, Any]) -> dict[str, Any]:
    monte = result.get("monte_carlo")
    if not isinstance(monte, dict):
        raise AssertionError("monte_carlo section missing from sweep result")
    selected: dict[str, Any] = {}
    for key in (
        "n_samples",
        "sample_count",
        "key_rate_mean_bps",
        "key_rate_std_bps",
        "key_rate_p5_bps",
        "key_rate_p95_bps",
        "yield_fraction",
    ):
        if key in monte:
            selected[key] = monte.get(key)
    if not selected:
        raise AssertionError("No deterministic Monte Carlo summary fields found")
    return selected


def _run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "photonstrust.cli", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope="module")
def perturbation_netlist() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "graph_id": "corner_perturbation_unit_netlist",
        "profile": "pic_circuit",
        "instances": [
            {
                "id": "wg_main",
                "kind": "waveguide",
                "params": {
                    "length_um": 1000.0,
                    "width_um": 0.5,
                    "insertion_loss_db": 0.1,
                },
            },
            {
                "id": "dc_main",
                "kind": "directional_coupler",
                "params": {
                    "gap_um": 0.20,
                    "coupling_ratio": 0.50,
                },
            },
            {
                "id": "ring_main",
                "kind": "ring_resonator",
                "params": {
                    "resonance_nm": 1550.0,
                    "group_index": 1.75,
                },
            },
        ],
        "nodes": [
            {
                "id": "wg_main",
                "kind": "pic.waveguide",
                "params": {
                    "length_um": 1000.0,
                    "width_um": 0.5,
                    "insertion_loss_db": 0.1,
                },
            },
            {
                "id": "dc_main",
                "kind": "pic.coupler",
                "params": {
                    "gap_um": 0.20,
                    "coupling_ratio": 0.50,
                },
            },
            {
                "id": "ring_main",
                "kind": "pic.ring_resonator",
                "params": {
                    "resonance_nm": 1550.0,
                    "group_index": 1.75,
                },
            },
        ],
    }


@pytest.fixture(scope="module")
def perturbation_pdk() -> Any:
    corner_manifest = _discover_corner_pdk_manifest()
    if corner_manifest is not None:
        return load_pdk_manifest(corner_manifest)
    return load_pdk_manifest(REPO_ROOT / "configs" / "pdks" / "aim_photonics.pdk.json")


@pytest.fixture(scope="module")
def corner_pdk_manifest_path() -> Path:
    manifest = _discover_corner_pdk_manifest()
    if manifest is None:
        pytest.skip("No corner PDK manifest detected under configs/pdks")
    return manifest


@pytest.fixture(scope="module")
def corner_sweep_result(
    tmp_path_factory: pytest.TempPathFactory,
    corner_pdk_manifest_path: Path,
) -> dict[str, Any]:
    output_dir = tmp_path_factory.mktemp("corner_sweep_nominal")
    return _invoke_run_corner_sweep(
        graph_path=DEMO_GRAPH_PATH,
        pdk_manifest_path=corner_pdk_manifest_path,
        output_dir=output_dir,
        n_monte_carlo=0,
        mc_seed=7,
    )


@pytest.fixture(scope="module")
def corner_sweep_mc_result(
    tmp_path_factory: pytest.TempPathFactory,
    corner_pdk_manifest_path: Path,
) -> dict[str, Any]:
    output_dir = tmp_path_factory.mktemp("corner_sweep_mc")
    return _invoke_run_corner_sweep(
        graph_path=DEMO_GRAPH_PATH,
        pdk_manifest_path=corner_pdk_manifest_path,
        output_dir=output_dir,
        n_monte_carlo=12,
        mc_seed=123,
    )


def test_perturbation_monotonicity_waveguide_loss(
    perturbation_netlist: dict[str, Any],
    perturbation_pdk: Any,
) -> None:
    low_loss = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(propagation_loss_db_per_cm=0.5),
        pdk=perturbation_pdk,
    )
    high_loss = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(propagation_loss_db_per_cm=2.5),
        pdk=perturbation_pdk,
    )
    assert _waveguide_total_insertion_loss_db(high_loss) >= _waveguide_total_insertion_loss_db(low_loss)


def test_perturbation_monotonicity_coupler_gap_effect(
    perturbation_netlist: dict[str, Any],
    perturbation_pdk: Any,
) -> None:
    fast_gap = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(coupling_gap_nm=-5.0),
        pdk=perturbation_pdk,
    )
    slow_gap = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(coupling_gap_nm=5.0),
        pdk=perturbation_pdk,
    )
    nominal = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(coupling_gap_nm=0.0),
        pdk=perturbation_pdk,
    )

    fast_params = dict(_find_component(fast_gap, component_id="dc_main").get("params") or {})
    nominal_params = dict(_find_component(nominal, component_id="dc_main").get("params") or {})
    slow_params = dict(_find_component(slow_gap, component_id="dc_main").get("params") or {})
    fast_ratio = _numeric_from_mapping(fast_params, ("coupling_ratio", "split_ratio", "power_ratio"))
    nominal_ratio = _numeric_from_mapping(nominal_params, ("coupling_ratio", "split_ratio", "power_ratio"))
    slow_ratio = _numeric_from_mapping(slow_params, ("coupling_ratio", "split_ratio", "power_ratio"))

    assert fast_ratio >= nominal_ratio
    assert nominal_ratio >= slow_ratio


def test_perturbation_ring_resonance_shift_behavior(
    perturbation_netlist: dict[str, Any],
    perturbation_pdk: Any,
) -> None:
    down = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(waveguide_width_nm=-10.0),
        pdk=perturbation_pdk,
    )
    up = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(waveguide_width_nm=10.0),
        pdk=perturbation_pdk,
    )
    nominal = _invoke_perturb_netlist(
        netlist=perturbation_netlist,
        process_params=_make_process_params(waveguide_width_nm=0.0),
        pdk=perturbation_pdk,
    )

    down_params = dict(_find_component(down, component_id="ring_main").get("params") or {})
    nominal_params = dict(_find_component(nominal, component_id="ring_main").get("params") or {})
    up_params = dict(_find_component(up, component_id="ring_main").get("params") or {})
    down_res = _numeric_from_mapping(down_params, ("resonance_nm", "resonance_wavelength_nm", "lambda_res_nm"))
    nominal_res = _numeric_from_mapping(nominal_params, ("resonance_nm", "resonance_wavelength_nm", "lambda_res_nm"))
    up_res = _numeric_from_mapping(up_params, ("resonance_nm", "resonance_wavelength_nm", "lambda_res_nm"))

    assert down_res <= nominal_res
    assert nominal_res <= up_res


def test_corner_expectation_ss_less_or_equal_tt_key_rate(corner_sweep_result: dict[str, Any]) -> None:
    corners = _extract_corner_rows(corner_sweep_result)
    assert "SS" in corners and "TT" in corners
    assert _extract_key_rate_bps(corners["SS"]) <= _extract_key_rate_bps(corners["TT"])


def test_corner_expectation_ff_greater_or_equal_tt_key_rate(corner_sweep_result: dict[str, Any]) -> None:
    corners = _extract_corner_rows(corner_sweep_result)
    assert "FF" in corners and "TT" in corners
    assert _extract_key_rate_bps(corners["FF"]) >= _extract_key_rate_bps(corners["TT"])


def test_corner_sweep_yield_fraction_bounded(corner_sweep_mc_result: dict[str, Any]) -> None:
    yield_fraction = _extract_yield_fraction(corner_sweep_mc_result)
    assert 0.0 <= yield_fraction <= 1.0


def test_compute_sensitivity_rank_variance_fractions_sum_to_one(corner_sweep_result: dict[str, Any]) -> None:
    corners = _extract_corner_rows(corner_sweep_result)
    rank = _invoke_compute_sensitivity_rank(
        corner_results=corners,
        sigma_dict={
            "waveguide_width_nm": 10.0,
            "coupling_gap_nm": 5.0,
            "propagation_loss_db_per_cm": 0.5,
        },
    )
    assert rank, "expected non-empty sensitivity ranking"

    fractions: list[float] = []
    for row in rank:
        if "variance_fraction" in row:
            fractions.append(float(row.get("variance_fraction") or 0.0))
        elif "fraction" in row:
            fractions.append(float(row.get("fraction") or 0.0))
        elif "weight" in row:
            fractions.append(float(row.get("weight") or 0.0))
    assert fractions, "expected variance fractions in sensitivity ranking output"
    assert sum(fractions) == pytest.approx(1.0, abs=1.0e-6)


def test_corner_sweep_monte_carlo_deterministic_with_fixed_seed(
    tmp_path: Path,
    corner_pdk_manifest_path: Path,
) -> None:
    out_a = tmp_path / "mc_a"
    out_b = tmp_path / "mc_b"
    report_a = _invoke_run_corner_sweep(
        graph_path=DEMO_GRAPH_PATH,
        pdk_manifest_path=corner_pdk_manifest_path,
        output_dir=out_a,
        n_monte_carlo=10,
        mc_seed=20260302,
    )
    report_b = _invoke_run_corner_sweep(
        graph_path=DEMO_GRAPH_PATH,
        pdk_manifest_path=corner_pdk_manifest_path,
        output_dir=out_b,
        n_monte_carlo=10,
        mc_seed=20260302,
    )
    assert _extract_monte_summary(report_a) == _extract_monte_summary(report_b)


def test_classify_risk_level_is_critical_when_worst_key_rate_zero() -> None:
    corner_results = {
        "SS": {"key_rate_bps": 0.0},
        "TT": {"key_rate_bps": 1200.0},
        "FF": {"key_rate_bps": 2400.0},
    }
    risk = _invoke_classify_risk_level(corner_results=corner_results, threshold_bps=1000.0)
    assert risk == "CRITICAL"


def test_corner_sweep_output_validates_against_schema_helper(corner_sweep_mc_result: dict[str, Any]) -> None:
    try:
        import photonstrust.workflow.schema as schema_mod
    except Exception as exc:  # pragma: no cover - defensive import
        pytest.skip(f"workflow schema module unavailable: {exc}")

    if not hasattr(schema_mod, "pic_corner_sweep_schema_path"):
        pytest.skip("pic_corner_sweep_schema_path helper is not available yet")

    schema_path = schema_mod.pic_corner_sweep_schema_path()
    if not Path(schema_path).exists():
        pytest.skip("Corner sweep schema path helper exists but file is not present")

    validate_instance(corner_sweep_mc_result, Path(schema_path))


def test_cli_corner_sweep_smoke_optional(tmp_path: Path, corner_pdk_manifest_path: Path) -> None:
    top_help = _run_cli(["-h"])
    if top_help.returncode != 0 or "sweep" not in str(top_help.stdout):
        pytest.skip("CLI sweep command is not available in this checkout")

    sweep_help = _run_cli(["sweep", "-h"])
    if sweep_help.returncode != 0:
        pytest.skip("CLI sweep command is present but help failed")

    help_text = (sweep_help.stdout or "") + (sweep_help.stderr or "")
    args = ["sweep", str(DEMO_GRAPH_PATH)]

    if "--output-dir" in help_text:
        args += ["--output-dir", str(tmp_path / "cli_corner_sweep")]
    elif "--output" in help_text:
        args += ["--output", str(tmp_path / "cli_corner_sweep")]

    if "--pdk-manifest" in help_text:
        args += ["--pdk-manifest", str(corner_pdk_manifest_path)]
    elif "--pdk" in help_text:
        args += ["--pdk", str(corner_pdk_manifest_path)]

    if "--target-distance" in help_text:
        args += ["--target-distance", "50.0"]
    if "--wavelength" in help_text:
        args += ["--wavelength", "1550.0"]
    if "--monte-carlo" in help_text:
        args += ["--monte-carlo", "0"]
    elif "--n-monte-carlo" in help_text:
        args += ["--n-monte-carlo", "0"]
    if "--mc-seed" in help_text:
        args += ["--mc-seed", "17"]
    if "--corners" in help_text:
        args += ["--corners", "all"]

    completed = _run_cli(args)
    combined = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0 and "unrecognized arguments" in combined.lower():
        pytest.skip("CLI sweep signature differs from assumed smoke invocation")
    assert completed.returncode == 0, combined
