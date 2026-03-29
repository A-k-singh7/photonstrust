"""FastAPI server for PhotonTrust MVP web workflows.

This is a local-development surface intended to keep the web UI thin:
- UI sends graph JSON.
- Backend validates/compiles and executes using the Python engine.
"""

from __future__ import annotations

from photonstrust.api.application import create_app
from photonstrust.api.routers.evidence import router as evidence_router
from photonstrust.api.routers.foundry import router as foundry_router
from photonstrust.api.routers.graph import router as graph_router
from photonstrust.api.routers.jobs import router as jobs_router
from photonstrust.api.routers.layout import router as layout_router
from photonstrust.api.routers.metrics import router as metrics_router
from photonstrust.api.routers.orbit import router as orbit_router
from photonstrust.api.routers.pic import router as pic_router
from photonstrust.api.routers.projects import router as projects_router
from photonstrust.api.routers.qkd import router as qkd_router
from photonstrust.api.routers.runs import router as runs_router
from photonstrust.api.routers.signoff import router as signoff_router
from photonstrust.api.routers.system import router as system_router
from photonstrust.api.routers.telemetry import router as telemetry_router
from photonstrust.api.routers.catalog import router as catalog_router
from photonstrust.api.routers.kms import router as kms_router
from photonstrust.api.routers.cost import router as cost_router
from photonstrust.api.routers.network import router as network_router
from photonstrust.api.routers.workflow import router as workflow_router
from photonstrust.api.routers.monitor import router as monitor_router
from photonstrust.api.routers.security import router as security_router
from photonstrust.api.routers.audit import router as audit_router
from photonstrust.api.routers.planner import router as planner_router
from photonstrust.api.routers.surrogate import router as surrogate_router
from photonstrust.api.routers.maintenance import router as maintenance_router
from photonstrust.api.routers.analytics import router as analytics_router
from photonstrust.api.routers.qrng import router as qrng_router
from photonstrust.api.routers.integrations import router as integrations_router
from photonstrust.api.routers.satellite import router as satellite_router
from photonstrust.api.routers.backends import router as backends_router
from photonstrust.api.routers.chipverify import router as chipverify_router


app = create_app()
app.include_router(system_router)
app.include_router(catalog_router)
app.include_router(kms_router)
app.include_router(network_router)
app.include_router(cost_router)
app.include_router(foundry_router)
app.include_router(graph_router)
app.include_router(orbit_router)
app.include_router(pic_router)
app.include_router(qkd_router)
app.include_router(layout_router)
app.include_router(signoff_router)
app.include_router(runs_router)
app.include_router(jobs_router)
app.include_router(projects_router)
app.include_router(metrics_router)
app.include_router(evidence_router)
app.include_router(telemetry_router)
app.include_router(workflow_router)
app.include_router(monitor_router)
app.include_router(security_router)
app.include_router(audit_router)
app.include_router(planner_router)
app.include_router(surrogate_router)
app.include_router(maintenance_router)
app.include_router(analytics_router)
app.include_router(qrng_router)
app.include_router(integrations_router)
app.include_router(satellite_router)
app.include_router(backends_router)
app.include_router(chipverify_router)
