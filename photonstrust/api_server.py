"""PhotonTrust FastAPI REST server.

Wraps the entire `photonstrust.sdk` behind HTTP endpoints so that any
EDA tool, MATLAB script, or web client can call the engine over JSON.

Endpoints
---------
GET  /health                    – liveness probe
POST /simulate                  – single-wavelength netlist simulation
POST /simulate/sweep            – wavelength sweep
POST /drc/crosstalk             – crosstalk DRC check
POST /drc/layout                – layout DRC + LVS
POST /yield                     – Monte Carlo process yield
POST /spice/export              – export SPICE netlist + .lib
POST /spice/ac_sweep            – generate AC sweep netlist text
POST /spice/monte_carlo         – generate MC netlist text
POST /spice/transient           – generate transient netlist text
POST /layout/gds                – export GDS layout JSON (GDL)
POST /layout/pcell              – get PCell instance dict
POST /wdm/analyze               – WDM channel analysis
POST /thermo/phase_shift        – thermo-optic V→ΔΦ calculation
POST /report/reliability_card   – generate HTML reliability card

Usage
-----
    uvicorn photonstrust.api_server:app --reload --port 8080

    # Or via SDK:
    import photonstrust.sdk as pt
    pt.start_server()
"""

from __future__ import annotations

import html
import json
import tempfile
from pathlib import Path
from typing import Any, Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel, Field
    _FASTAPI = True
except ImportError:
    _FASTAPI = False


def _require_fastapi() -> None:
    if not _FASTAPI:
        raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn")


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

if _FASTAPI:
    class SimulateRequest(BaseModel):
        netlist: dict[str, Any]
        wavelength_nm: Optional[float] = 1550.0

    class SweepRequest(BaseModel):
        netlist: dict[str, Any]
        wavelengths_nm: list[float] = Field(
            default_factory=lambda: list(range(1480, 1581, 10))
        )

    class CrosstalkDRCRequest(BaseModel):
        gap_um: float = 1.0
        length_um: float = 100.0
        wavelength_nm: float = 1550.0
        target_xt_db: float = -30.0
        process_metrics: Optional[list[dict[str, Any]]] = None
        mc_samples: int = 5000

    class LayoutDRCRequest(BaseModel):
        netlist: dict[str, Any]
        rules: Optional[dict[str, Any]] = None

    class YieldRequest(BaseModel):
        metrics: list[dict[str, Any]]
        mc_samples: int = 10000
        min_required_yield: float = 0.90

    class SpiceExportRequest(BaseModel):
        graph: dict[str, Any]
        top_name: str = "PT_TOP"
        include_compact_models: bool = True

    class SpiceACRequest(BaseModel):
        graph: dict[str, Any]
        start_wl_nm: float = 1480.0
        stop_wl_nm: float = 1580.0
        points: int = 100

    class SpiceMCRequest(BaseModel):
        graph: dict[str, Any]
        n_runs: int = 200
        sigma_scale: float = 1.0

    class SpiceTransientRequest(BaseModel):
        graph: dict[str, Any]
        bit_rate_gbps: float = 25.0
        n_bits: int = 8
        v_pi: float = 5.0

    class GDSRequest(BaseModel):
        netlist: dict[str, Any]
        format: str = "gdl"

    class PCellRequest(BaseModel):
        kind: str
        params: Optional[dict[str, Any]] = None
        x: float = 0.0
        y: float = 0.0
        rotation_deg: float = 0.0

    class WDMRequest(BaseModel):
        netlist: dict[str, Any]
        channel_spacing_ghz: float = 100.0
        n_channels: int = 8
        center_wl_nm: float = 1550.0

    class ThermoOpticRequest(BaseModel):
        voltage_v: float
        heater_resistance_ohm: float = 500.0
        thermal_resistance_k_per_w: float = 5e4
        thermo_optic_coeff: float = 1.86e-4
        waveguide_length_um: float = 50.0
        wavelength_nm: float = 1550.0

    class ReliabilityCardRequest(BaseModel):
        netlist: Optional[dict[str, Any]] = None
        drc_params: Optional[dict[str, Any]] = None
        yield_metrics: Optional[list[dict[str, Any]]] = None
        title: str = "PhotonTrust Reliability Card"


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Any:
    _require_fastapi()
    import photonstrust.sdk as pt

    app = FastAPI(
        title="PhotonTrust REST API",
        description=(
            "HTTP interface to the PhotonTrust photonic simulation engine. "
            "All SDK capabilities are exposed as JSON endpoints."
        ),
        version="1.0.0",
        contact={"name": "PhotonTrust", "url": "https://photonstrust.ai"},
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "engine": "photonstrust"}

    @app.post("/simulate")
    def simulate(req: SimulateRequest) -> dict:
        try:
            return pt.simulate_netlist(req.netlist, wavelength_nm=req.wavelength_nm)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/simulate/sweep")
    def simulate_sweep(req: SweepRequest) -> list:
        try:
            return pt.simulate_netlist_sweep(req.netlist, wavelengths_nm=req.wavelengths_nm)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/drc/crosstalk")
    def drc_crosstalk(req: CrosstalkDRCRequest) -> dict:
        try:
            return pt.run_drc_report(
                gap_um=req.gap_um, length_um=req.length_um,
                wavelength_nm=req.wavelength_nm, target_xt_db=req.target_xt_db,
                process_metrics=req.process_metrics, mc_samples=req.mc_samples,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/drc/layout")
    def drc_layout(req: LayoutDRCRequest) -> dict:
        try:
            return pt.run_layout_drc_lvs(req.netlist, req.rules)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/yield")
    def estimate_yield(req: YieldRequest) -> dict:
        try:
            return pt.estimate_yield(
                req.metrics, mc_samples=req.mc_samples,
                min_required_yield=req.min_required_yield,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/spice/export")
    def spice_export(req: SpiceExportRequest) -> dict:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                result = pt.export_spice(
                    req.graph, tmp,
                    top_name=req.top_name,
                    include_compact_models=req.include_compact_models,
                )
                # Read generated files and embed in response
                out = Path(tmp)
                netlist_rel = Path(str(result["artifacts"]["netlist_path"]).strip())
                if netlist_rel.is_absolute() or any(part in ("", "..") for part in netlist_rel.parts):
                    raise ValueError("netlist artifact path must be a safe relative path")
                netlist_path = (out / netlist_rel).resolve()
                netlist_path.relative_to(out.resolve())
                netlist_text = netlist_path.read_text(encoding="utf-8")
                lib_text = None
                if "compact_models_lib" in result["artifacts"]:
                    lib_rel = Path(str(result["artifacts"]["compact_models_lib"]).strip())
                    if lib_rel.is_absolute() or any(part in ("", "..") for part in lib_rel.parts):
                        raise ValueError("compact model artifact path must be a safe relative path")
                    lib_path = (out / lib_rel).resolve()
                    lib_path.relative_to(out.resolve())
                    if lib_path.exists():
                        lib_text = lib_path.read_text(encoding="utf-8")
                return {
                    **result,
                    "netlist_text": netlist_text,
                    "compact_models_text": lib_text,
                }
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/spice/ac_sweep", response_class=JSONResponse)
    def spice_ac_sweep(req: SpiceACRequest) -> dict:
        try:
            text = pt.ac_sweep_netlist(
                req.graph, start_wl_nm=req.start_wl_nm,
                stop_wl_nm=req.stop_wl_nm, points=req.points,
            )
            return {"netlist": text}
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/spice/monte_carlo")
    def spice_mc(req: SpiceMCRequest) -> dict:
        try:
            return {"netlist": pt.monte_carlo_netlist(
                req.graph, n_runs=req.n_runs, sigma_scale=req.sigma_scale,
            )}
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/spice/transient")
    def spice_transient(req: SpiceTransientRequest) -> dict:
        try:
            return {"netlist": pt.transient_netlist(
                req.graph, bit_rate_gbps=req.bit_rate_gbps,
                n_bits=req.n_bits, v_pi=req.v_pi,
            )}
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/layout/gds")
    def layout_gds(req: GDSRequest) -> dict:
        try:
            return pt.netlist_to_gdl(req.netlist)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/layout/pcell")
    def layout_pcell(req: PCellRequest) -> dict:
        try:
            return pt.pcell_instance(
                req.kind, req.params, x=req.x, y=req.y,
                rotation_deg=req.rotation_deg,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/wdm/analyze")
    def wdm_analyze(req: WDMRequest) -> dict:
        try:
            from photonstrust.wdm.analysis import analyze_wdm_channels
            return analyze_wdm_channels(
                req.netlist,
                channel_spacing_ghz=req.channel_spacing_ghz,
                n_channels=req.n_channels,
                center_wl_nm=req.center_wl_nm,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/thermo/phase_shift")
    def thermo_phase_shift(req: ThermoOpticRequest) -> dict:
        try:
            from photonstrust.physics.thermo_optic import compute_thermo_optic_phase
            return compute_thermo_optic_phase(
                voltage_v=req.voltage_v,
                heater_resistance_ohm=req.heater_resistance_ohm,
                thermal_resistance_k_per_w=req.thermal_resistance_k_per_w,
                thermo_optic_coeff=req.thermo_optic_coeff,
                waveguide_length_um=req.waveguide_length_um,
                wavelength_nm=req.wavelength_nm,
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    @app.post("/report/reliability_card", response_class=HTMLResponse)
    def reliability_card(req: ReliabilityCardRequest) -> str:
        try:
            from photonstrust.reports.reliability_card import generate_reliability_card_html
            return generate_reliability_card_html(
                netlist=req.netlist,
                drc_params=req.drc_params,
                yield_metrics=req.yield_metrics,
                title=html.escape(req.title, quote=True),
            )
        except Exception as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    return app


# Singleton app instance
try:
    app = create_app()
except ImportError:
    app = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Programmatic server launch
# ---------------------------------------------------------------------------

def start_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
    log_level: str = "info",
) -> None:
    """Start the PhotonTrust REST API server.

    Parameters
    ----------
    host:
        Bind address.
    port:
        Port to listen on.
    reload:
        Enable live reload (dev mode).

    Example
    -------
    >>> import photonstrust.sdk as pt
    >>> pt.start_server(port=8080)
    """
    try:
        import uvicorn  # type: ignore[import-untyped]
    except ImportError as exc:
        raise ImportError("uvicorn required: pip install uvicorn") from exc

    uvicorn.run(
        "photonstrust.api_server:app",
        host=host,
        port=port,
        reload=reload,
        log_level=log_level,
    )
