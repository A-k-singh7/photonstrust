"""PhotonTrust Streamlit dashboard."""

from __future__ import annotations

import json
import io
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import zipfile

import streamlit as st

from ui.components import render_card_delta, render_card_summary, render_decision_summary
from ui.data import (
    api_artifact_url,
    api_get_json,
    api_post_json,
    append_ui_metric_event,
    diagnose_api_runtime_error,
    get_ui_project_baseline,
    list_dataset_entries,
    list_runs,
    load_card,
    load_dataset_entry,
    load_ui_product_state,
    promote_ui_project_baseline,
    save_ui_product_state,
    save_ui_pic_run_bundle,
    save_ui_run_profile,
    stable_json_hash,
)


FALLBACK_PROTOCOLS = ["BBM92", "E91", "MDI_QKD", "AMDI_QKD", "PM_QKD", "TF_QKD"]

RUN_PRESETS: dict[str, dict[str, Any]] = {
    "BBM92 Quick": {
        "protocol_name": "BBM92",
        "distance_km": 50.0,
        "rep_rate_mhz": 100.0,
        "pde": 0.30,
        "dark_counts_cps": 100.0,
        "coincidence_window_ps": 200.0,
        "source_type": "emitter_cavity",
        "mu": 0.5,
    },
    "MDI Long-Link": {
        "protocol_name": "MDI_QKD",
        "distance_km": 150.0,
        "rep_rate_mhz": 100.0,
        "pde": 0.75,
        "dark_counts_cps": 1.0,
        "coincidence_window_ps": 200.0,
        "source_type": "emitter_cavity",
        "mu": 0.2,
        "nu": 0.05,
        "omega": 0.0,
        "relay_fraction": 0.5,
    },
    "AMDI Benchmark": {
        "protocol_name": "AMDI_QKD",
        "distance_km": 400.0,
        "rep_rate_mhz": 1000.0,
        "pde": 0.85,
        "dark_counts_cps": 0.02,
        "coincidence_window_ps": 100.0,
        "source_type": "emitter_cavity",
        "mu": 0.2,
        "nu": 0.05,
        "omega": 0.0,
        "relay_fraction": 0.5,
        "pairing_window_bins": 4096.0,
        "pairing_efficiency": 0.8,
        "pairing_error_prob": 0.0,
    },
    "TF High-Distance": {
        "protocol_name": "TF_QKD",
        "distance_km": 300.0,
        "rep_rate_mhz": 850.0,
        "pde": 0.80,
        "dark_counts_cps": 0.1,
        "coincidence_window_ps": 100.0,
        "source_type": "emitter_cavity",
        "mu": 0.2,
        "phase_slices": 32.0,
        "relay_fraction": 0.5,
    },
}

DEFAULT_BUILDER_STATE: dict[str, Any] = {
    "api_base_url": str(os.environ.get("PHOTONTRUST_API_BASE_URL", "http://127.0.0.1:8000")),
    "project_id": str(os.environ.get("PHOTONTRUST_DEFAULT_PROJECT_ID", "default")),
    "scenario_id": "ui_qkd_run",
    "graph_id": "ui_qkd_link",
    "protocol_name": "BBM92",
    "distance_km": 50.0,
    "band": "c_1550",
    "wavelength_nm": 1550.0,
    "execution_mode": "preview",
    "source_type": "emitter_cavity",
    "rep_rate_mhz": 100.0,
    "collection_efficiency": 0.35,
    "coupling_efficiency": 0.60,
    "g2_0": 0.02,
    "fiber_loss_db_per_km": 0.2,
    "connector_loss_db": 1.5,
    "channel_background_counts_cps": 0.0,
    "detector_class": "snspd",
    "pde": 0.30,
    "dark_counts_cps": 100.0,
    "detector_background_counts_cps": 0.0,
    "jitter_ps_fwhm": 30.0,
    "dead_time_ns": 100.0,
    "afterpulsing_prob": 0.001,
    "sync_drift_ps_rms": 10.0,
    "coincidence_window_ps": 200.0,
    "sifting_factor": 0.5,
    "ec_efficiency": 1.16,
    "misalignment_prob": 0.01,
    "relay_fraction": 0.5,
    "mu": 0.5,
    "nu": 0.1,
    "omega": 0.0,
    "phase_slices": 16.0,
    "pairing_window_bins": 2048.0,
    "pairing_efficiency": 0.6,
    "pairing_error_prob": 0.0,
    "include_qasm": True,
}

SESSION_FIRST_VISIT_TS_KEY = "ui_first_visit_ts"
SESSION_LAST_TTFV_SECONDS_KEY = "ui_last_ttfv_seconds"
SESSION_LAST_UI_EVENT_LOG_KEY = "ui_last_event_log_path"
SESSION_LAST_ERROR_DIAG_KEY = "ui_last_error_diag"
SESSION_LAST_PROFILE_PATH_KEY = "ui_last_profile_path"
SESSION_DECISION_PROJECT_ID_KEY = "ui_decision_project_id"
RUN_PROFILE_SCHEMA_VERSION = "0.1"
SESSION_PIC_GRAPH_JSON_KEY = "ui_pic_graph_json"
SESSION_LAST_PIC_PAYLOAD_KEY = "ui_last_pic_payload"
SESSION_LAST_PIC_REQUEST_KEY = "ui_last_pic_request"
SESSION_LAST_PIC_BUNDLE_DIR_KEY = "ui_last_pic_bundle_dir"
SESSION_CAPABILITY_LAST_RESULT_KEY = "ui_capability_last_result"
SESSION_CAPABILITY_HISTORY_KEY = "ui_capability_history"
SESSION_EXPERIENCE_MODE_KEY = "ui_experience_mode"
SESSION_GUIDED_CHECKLIST_KEY = "ui_guided_checklist"
SESSION_GUIDED_CHECKLIST_LOADED_KEY = "ui_guided_checklist_loaded"
SESSION_UI_SESSION_ID_KEY = "ui_session_id"
SESSION_FLOW_ENTERED_TS_KEY = "ui_newcomer_flow_entered_ts"
SESSION_FLOW_COMPLETED_EMITTED_KEY = "ui_newcomer_flow_completed_emitted"
SESSION_PREV_EXPERIENCE_MODE_KEY = "ui_prev_experience_mode"

NEWCOMER_FLOW_VERSION = "2026-03-guided-power-v1"

EXPERIENCE_MODES: tuple[str, ...] = ("Guided", "Power")

GUIDED_CHECKLIST_STEPS: tuple[tuple[str, str], ...] = (
    ("api_health_checked", "Check API health"),
    ("first_run_completed", "Run first simulation"),
    ("decision_reviewed", "Review decision summary"),
    ("compare_decision", "Compare candidate vs baseline"),
)

GLOSSARY_TERMS: tuple[tuple[str, str], ...] = (
    ("QBER", "Quantum bit error rate. Lower is generally better for secure key generation."),
    ("Key rate", "Estimated secret key bits per second produced by the run."),
    (
        "Safe-use label",
        "Trust posture label derived from thresholds and checks; use it to qualify deployment readiness.",
    ),
    (
        "Reliability card",
        "Primary report artifact summarizing assumptions, outputs, and trust-relevant diagnostics.",
    ),
    (
        "Baseline",
        "Reference run used for comparison and promotion decisions in the Run Registry.",
    ),
)

CAPABILITY_API_SURFACE: list[dict[str, str]] = [
    {"domain": "Core API", "capability": "Health probe", "method": "GET", "path": "/healthz", "ui_status": "Console", "startup_value": "Runtime liveness and version check."},
    {"domain": "Core API", "capability": "Kinds registry", "method": "GET", "path": "/v0/registry/kinds", "ui_status": "Builder+Console", "startup_value": "Machine-readable parameter and component taxonomy."},
    {"domain": "Graph", "capability": "Graph validation", "method": "POST", "path": "/v0/graph/validate", "ui_status": "Console", "startup_value": "Pre-flight schema and semantic diagnostics."},
    {"domain": "Graph", "capability": "Graph compilation", "method": "POST", "path": "/v0/graph/compile", "ui_status": "Console", "startup_value": "Deterministic compile step with cache metadata."},
    {"domain": "QKD", "capability": "Run QKD simulation", "method": "POST", "path": "/v0/qkd/run", "ui_status": "Run Builder+Console", "startup_value": "Reliability-card-grade simulation with provenance."},
    {"domain": "QKD", "capability": "Run QKD async", "method": "POST", "path": "/v0/qkd/run/async", "ui_status": "Console", "startup_value": "Queue-based execution for larger jobs."},
    {"domain": "QKD", "capability": "Import external result", "method": "POST", "path": "/v0/qkd/import_external", "ui_status": "Console", "startup_value": "Interop bridge from third-party simulators."},
    {"domain": "Jobs", "capability": "List jobs", "method": "GET", "path": "/v0/jobs", "ui_status": "Console", "startup_value": "Execution queue observability."},
    {"domain": "Jobs", "capability": "Get job", "method": "GET", "path": "/v0/jobs/{job_id}", "ui_status": "Console", "startup_value": "Full async job manifest retrieval."},
    {"domain": "Jobs", "capability": "Get job status", "method": "GET", "path": "/v0/jobs/{job_id}/status", "ui_status": "Console", "startup_value": "Lightweight async polling endpoint."},
    {"domain": "Runs", "capability": "List runs", "method": "GET", "path": "/v0/runs", "ui_status": "Run Registry+Console", "startup_value": "Unified run registry across workflows."},
    {"domain": "Runs", "capability": "Get run manifest", "method": "GET", "path": "/v0/runs/{run_id}", "ui_status": "Run Registry+Console", "startup_value": "Single-run provenance and artifact index."},
    {"domain": "Runs", "capability": "Fetch run artifact", "method": "GET", "path": "/v0/runs/{run_id}/artifact", "ui_status": "Run Builder+Registry+Console", "startup_value": "Safe artifact serving with path constraints."},
    {"domain": "Runs", "capability": "Build evidence bundle", "method": "GET", "path": "/v0/runs/{run_id}/bundle", "ui_status": "Console", "startup_value": "Portable evidence package for offline review."},
    {"domain": "Runs", "capability": "Publish evidence bundle", "method": "POST", "path": "/v0/runs/{run_id}/bundle/publish", "ui_status": "Console", "startup_value": "Digest-addressable bundle publication."},
    {"domain": "Evidence", "capability": "Fetch published bundle", "method": "GET", "path": "/v0/evidence/bundle/by-digest/{digest}", "ui_status": "Console", "startup_value": "Immutable, hash-addressed evidence retrieval."},
    {"domain": "Evidence", "capability": "Verify published bundle", "method": "GET", "path": "/v0/evidence/bundle/by-digest/{digest}/verify", "ui_status": "Console", "startup_value": "Server-side integrity verification report."},
    {"domain": "Runs", "capability": "Run diff", "method": "POST", "path": "/v0/runs/diff", "ui_status": "Run Registry+Console", "startup_value": "Input/output delta and violation-diff analysis."},
    {"domain": "Projects", "capability": "List projects", "method": "GET", "path": "/v0/projects", "ui_status": "Console", "startup_value": "Project-level aggregation over run history."},
    {"domain": "Projects", "capability": "List approvals", "method": "GET", "path": "/v0/projects/{project_id}/approvals", "ui_status": "Console", "startup_value": "Approval ledger for governance."},
    {"domain": "Projects", "capability": "Create approval", "method": "POST", "path": "/v0/projects/{project_id}/approvals", "ui_status": "Console", "startup_value": "Machine-checkable signoff trail."},
    {"domain": "Orbit", "capability": "Validate orbit pass", "method": "POST", "path": "/v0/orbit/pass/validate", "ui_status": "Console", "startup_value": "Mission-envelope diagnostics before execution."},
    {"domain": "Orbit", "capability": "Run orbit pass", "method": "POST", "path": "/v0/orbit/pass/run", "ui_status": "Console", "startup_value": "Time-resolved pass simulation with trust labels."},
    {"domain": "PIC", "capability": "Simulate PIC graph", "method": "POST", "path": "/v0/pic/simulate", "ui_status": "PIC+Console", "startup_value": "Single-point and sweep photonic simulation."},
    {"domain": "PIC", "capability": "Inverse design (MZI phase)", "method": "POST", "path": "/v0/pic/invdesign/mzi_phase", "ui_status": "Console", "startup_value": "Objective-driven phase tuning with evidence."},
    {"domain": "PIC", "capability": "Inverse design (coupler ratio)", "method": "POST", "path": "/v0/pic/invdesign/coupler_ratio", "ui_status": "Console", "startup_value": "Coupler optimization for target split ratios."},
    {"domain": "PIC", "capability": "Workflow chain", "method": "POST", "path": "/v0/pic/workflow/invdesign_chain", "ui_status": "Console", "startup_value": "Chained invdesign->layout->LVS->SPICE workflow."},
    {"domain": "PIC", "capability": "Workflow replay", "method": "POST", "path": "/v0/pic/workflow/invdesign_chain/replay", "ui_status": "Console", "startup_value": "Deterministic replay from stored request snapshot."},
    {"domain": "PIC", "capability": "Layout build", "method": "POST", "path": "/v0/pic/layout/build", "ui_status": "Console", "startup_value": "Deterministic PIC layout artifact generation."},
    {"domain": "PIC", "capability": "LVS-lite", "method": "POST", "path": "/v0/pic/layout/lvs_lite", "ui_status": "Console", "startup_value": "Topology and signoff-bundle consistency checks."},
    {"domain": "PIC", "capability": "KLayout artifact pack", "method": "POST", "path": "/v0/pic/layout/klayout/run", "ui_status": "Console", "startup_value": "Tool-seam output bundle for DRC/LVS integration."},
    {"domain": "PIC", "capability": "Foundry DRC sealed seam", "method": "POST", "path": "/v0/pic/layout/foundry_drc/run", "ui_status": "Console", "startup_value": "Fail-closed foundry DRC bridge with metadata-only exposure."},
    {"domain": "PIC", "capability": "SPICE export", "method": "POST", "path": "/v0/pic/spice/export", "ui_status": "Console", "startup_value": "Circuit export into SPICE-compatible artifacts."},
    {"domain": "PIC", "capability": "Performance DRC crosstalk", "method": "POST", "path": "/v0/performance_drc/crosstalk", "ui_status": "Console", "startup_value": "Physical performance checks against crosstalk budgets."},
]

CAPABILITY_CLI_SURFACE: list[dict[str, str]] = [
    {"domain": "CLI", "capability": "Scenario run", "command": "photonstrust run <config.yaml>", "startup_value": "One-command local execution for research and ops."},
    {"domain": "CLI", "capability": "Config validation only", "command": "photonstrust run <config.yaml> --validate-only", "startup_value": "Pre-flight config checks in CI and review loops."},
    {"domain": "CLI", "capability": "Graph compile artifacts", "command": "photonstrust graph compile <graph.json> --output results/graphs", "startup_value": "Deterministic graph-to-engine build artifact chain."},
    {"domain": "CLI", "capability": "GraphSpec canonical formatter", "command": "photonstrust fmt graphspec <graph.toml> --check --print-hash", "startup_value": "Stable formatting and hash-based reproducibility."},
    {"domain": "CLI", "capability": "PIC simulation", "command": "photonstrust pic simulate <netlist.json> --wavelength-sweep-nm 1540 1550 1560", "startup_value": "Local photonic simulation path without API layer."},
    {"domain": "CLI", "capability": "PIC crosstalk predictor", "command": "photonstrust pic crosstalk --gap-um 0.6 --length-um 1000 --wavelength-nm 1550", "startup_value": "Quick route-geometry performance checks."},
    {"domain": "CLI", "capability": "Evidence key generation", "command": "photonstrust bundle keygen --private keys/private.pem --public keys/public.pem", "startup_value": "Ed25519 signing key lifecycle bootstrap."},
    {"domain": "CLI", "capability": "Evidence signing", "command": "photonstrust bundle sign <bundle.zip> --key keys/private.pem", "startup_value": "Cryptographic release/evidence attestation."},
    {"domain": "CLI", "capability": "Evidence verification", "command": "photonstrust bundle verify <bundle.zip> --pubkey keys/public.pem --require-signature", "startup_value": "Integrity and signature checks for auditors."},
    {"domain": "CLI", "capability": "Reliability card validation", "command": "photonstrust card validate <reliability_card.json> --schema v1.1", "startup_value": "Schema-level quality gate for card artifacts."},
    {"domain": "CLI", "capability": "Reliability card diff", "command": "photonstrust card diff <lhs.json> <rhs.json> --limit 200", "startup_value": "Change tracking across candidate releases."},
]

CAPABILITY_DEMOS: dict[str, dict[str, str]] = {
    "platform_smoke": {
        "title": "Platform smoke check",
        "description": "Checks health, kinds registry, runs listing, and projects listing to prove runtime readiness.",
    },
    "qkd_sync": {
        "title": "QKD synchronous run",
        "description": "Runs `/v0/qkd/run` and emits a reliability-card-bearing run manifest.",
    },
    "qkd_async": {
        "title": "QKD async + jobs",
        "description": "Submits `/v0/qkd/run/async`, then polls `/v0/jobs/{job_id}/status` to terminal state.",
    },
    "qkd_external_import": {
        "title": "QKD external import",
        "description": "Imports an external simulator result and converts it into a PhotonTrust reliability card.",
    },
    "orbit_validate_run": {
        "title": "Orbit validate + run",
        "description": "Validates and executes an orbit-pass envelope configuration.",
    },
    "pic_simulate": {
        "title": "PIC simulation sweep",
        "description": "Executes `/v0/pic/simulate` on an interferometer graph with wavelength sweep.",
    },
    "pic_workflow_chain": {
        "title": "PIC workflow chain",
        "description": "Runs inverse design + layout + LVS + SPICE in one chained workflow.",
    },
    "performance_drc": {
        "title": "Performance DRC crosstalk",
        "description": "Runs crosstalk/loss-budget checks with pdk context and violation summaries.",
    },
    "bundle_publish_verify": {
        "title": "Evidence bundle publish + verify",
        "description": "Publishes a run evidence bundle and verifies by digest.",
    },
}


def _builder_key(name: str) -> str:
    return f"rb_{name}"


def _ensure_builder_defaults() -> None:
    for key, value in DEFAULT_BUILDER_STATE.items():
        skey = _builder_key(key)
        if skey not in st.session_state:
            st.session_state[skey] = value

    if SESSION_EXPERIENCE_MODE_KEY not in st.session_state:
        st.session_state[SESSION_EXPERIENCE_MODE_KEY] = EXPERIENCE_MODES[0]

    if SESSION_UI_SESSION_ID_KEY not in st.session_state:
        st.session_state[SESSION_UI_SESSION_ID_KEY] = f"st_{uuid4().hex}"


def _guided_step_index(step_id: str) -> int:
    sid = str(step_id or "").strip()
    for idx, (candidate, _) in enumerate(GUIDED_CHECKLIST_STEPS, start=1):
        if candidate == sid:
            return int(idx)
    return 0


def _is_guided_complete(checklist: dict[str, Any]) -> bool:
    for step_id, _ in GUIDED_CHECKLIST_STEPS:
        if checklist.get(step_id) is not True:
            return False
    return True


def _newcomer_payload_base(*, results_root: Path) -> dict[str, Any]:
    state = load_ui_product_state(results_root)
    onboarding = state.get("guided_onboarding") if isinstance(state.get("guided_onboarding"), dict) else {}

    newcomer_id = str(onboarding.get("newcomer_id", "")).strip()
    if not newcomer_id:
        newcomer_id = f"st_newcomer_{uuid4().hex[:16]}"
        onboarding["newcomer_id"] = newcomer_id
        state["guided_onboarding"] = onboarding
        save_ui_product_state(results_root, state)

    session_id = str(st.session_state.get(SESSION_UI_SESSION_ID_KEY, "")).strip()
    if not session_id:
        session_id = f"st_{uuid4().hex}"
        st.session_state[SESSION_UI_SESSION_ID_KEY] = session_id

    return {
        "flow": str(_experience_mode()).lower(),
        "flow_version": NEWCOMER_FLOW_VERSION,
        "newcomer_id": newcomer_id,
        "session_id": session_id,
        "is_newcomer": True,
    }


def _emit_newcomer_event(
    *,
    results_root: Path,
    event_name: str,
    payload: dict[str, Any] | None = None,
) -> None:
    base = _newcomer_payload_base(results_root=results_root)
    merged: dict[str, Any] = dict(base)
    extra = payload if isinstance(payload, dict) else {}
    for key, value in extra.items():
        merged[str(key)] = value
    _log_ui_event(results_root=results_root, event_name=event_name, payload=merged)


def _load_guided_checklist_from_state(*, results_root: Path) -> dict[str, bool]:
    state = load_ui_product_state(results_root)
    onboarding = state.get("guided_onboarding") if isinstance(state.get("guided_onboarding"), dict) else {}
    raw = onboarding.get("checklist") if isinstance(onboarding.get("checklist"), dict) else {}
    out: dict[str, bool] = {}
    for step_id, _ in GUIDED_CHECKLIST_STEPS:
        out[step_id] = bool(raw.get(step_id) is True)
    return out


def _save_guided_checklist_to_state(*, results_root: Path, checklist: dict[str, Any]) -> None:
    state = load_ui_product_state(results_root)
    onboarding = state.get("guided_onboarding") if isinstance(state.get("guided_onboarding"), dict) else {}
    stored: dict[str, bool] = {}
    for step_id, _ in GUIDED_CHECKLIST_STEPS:
        stored[step_id] = bool(checklist.get(step_id) is True)

    onboarding["checklist"] = stored
    onboarding["updated_at"] = datetime.now(timezone.utc).isoformat()
    onboarding["completed"] = _is_guided_complete(stored)
    state["guided_onboarding"] = onboarding
    save_ui_product_state(results_root, state)


def _ensure_guided_checklist_defaults(*, results_root: Path | None = None) -> None:
    if results_root is not None and not bool(st.session_state.get(SESSION_GUIDED_CHECKLIST_LOADED_KEY, False)):
        persisted = _load_guided_checklist_from_state(results_root=results_root)
        st.session_state[SESSION_GUIDED_CHECKLIST_KEY] = dict(persisted)
        st.session_state[SESSION_GUIDED_CHECKLIST_LOADED_KEY] = True

    existing = st.session_state.get(SESSION_GUIDED_CHECKLIST_KEY)
    if isinstance(existing, dict):
        for step_id, _ in GUIDED_CHECKLIST_STEPS:
            if step_id not in existing:
                existing[step_id] = False
        return

    st.session_state[SESSION_GUIDED_CHECKLIST_KEY] = {
        step_id: False for step_id, _ in GUIDED_CHECKLIST_STEPS
    }


def _experience_mode() -> str:
    value = str(st.session_state.get(SESSION_EXPERIENCE_MODE_KEY, EXPERIENCE_MODES[0])).strip()
    return value if value in EXPERIENCE_MODES else EXPERIENCE_MODES[0]


def _mark_guided_step(*, results_root: Path, step_id: str) -> None:
    _ensure_guided_checklist_defaults(results_root=results_root)
    checklist = st.session_state.get(SESSION_GUIDED_CHECKLIST_KEY)
    if not isinstance(checklist, dict):
        return
    if checklist.get(step_id) is True:
        return

    checklist[step_id] = True
    _save_guided_checklist_to_state(results_root=results_root, checklist=checklist)

    _log_ui_event(
        results_root=results_root,
        event_name="guided_step_completed",
        payload={"step_id": step_id, "experience_mode": _experience_mode().lower()},
    )
    entered_ts = float(st.session_state.get(SESSION_FLOW_ENTERED_TS_KEY, time.time()))
    _emit_newcomer_event(
        results_root=results_root,
        event_name="newcomer_step_completed",
        payload={
            "step_id": str(step_id),
            "step_index": _guided_step_index(step_id),
            "time_from_enter_ms": int(max(0.0, (time.time() - entered_ts) * 1000.0)),
        },
    )

    if _is_guided_complete(checklist) and not bool(st.session_state.get(SESSION_FLOW_COMPLETED_EMITTED_KEY, False)):
        _emit_newcomer_event(
            results_root=results_root,
            event_name="newcomer_flow_completed",
            payload={
                "time_from_enter_ms": int(max(0.0, (time.time() - entered_ts) * 1000.0)),
            },
        )
        st.session_state[SESSION_FLOW_COMPLETED_EMITTED_KEY] = True


def _render_glossary_help(*, title: str = "Glossary (quick help)") -> None:
    with st.expander(title, expanded=False):
        for term, meaning in GLOSSARY_TERMS:
            st.markdown(f"- **{term}**: {meaning}")


def _newcomer_completion_metrics(*, results_root: Path) -> dict[str, float]:
    path = Path(results_root) / "ui_metrics" / "events.jsonl"
    if not path.exists():
        return {
            "started": 0.0,
            "completed": 0.0,
            "completion_rate_pct": 0.0,
        }

    started_ids: set[str] = set()
    completed_ids: set[str] = set()
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = str(raw).strip()
            if not line:
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                continue
            event_name = str(payload.get("event", "")).strip()
            details = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
            newcomer_id = str(details.get("newcomer_id", "")).strip()
            if not newcomer_id:
                continue
            if event_name == "newcomer_flow_entered":
                started_ids.add(newcomer_id)
            elif event_name == "newcomer_flow_completed":
                completed_ids.add(newcomer_id)
    except Exception:
        return {
            "started": 0.0,
            "completed": 0.0,
            "completion_rate_pct": 0.0,
        }

    started = float(len(started_ids))
    completed = float(len(started_ids.intersection(completed_ids)))
    rate = 0.0 if started <= 0.0 else (completed / started) * 100.0
    return {
        "started": started,
        "completed": completed,
        "completion_rate_pct": rate,
    }


def _render_start_here_guide(*, results_root: Path) -> None:
    _ensure_guided_checklist_defaults(results_root=results_root)
    mode = _experience_mode()
    checklist = st.session_state.get(SESSION_GUIDED_CHECKLIST_KEY)
    if not isinstance(checklist, dict):
        checklist = {step_id: False for step_id, _ in GUIDED_CHECKLIST_STEPS}

    st.markdown("**Start Here**")
    if mode == "Guided":
        st.caption(
            "New here? Follow this rail: check API -> run first simulation -> review decision -> compare baseline."
        )
        newcomer_metrics = _newcomer_completion_metrics(results_root=results_root)
        st.metric(
            "Newcomer completion rate",
            f"{float(newcomer_metrics.get('completion_rate_pct', 0.0)):.1f}%",
            help=(
                "Share of newcomers who started the guided flow and completed all onboarding checklist steps."
            ),
        )
        st.caption(
            f"started={int(newcomer_metrics.get('started', 0.0))} | "
            f"completed={int(newcomer_metrics.get('completed', 0.0))}"
        )
        for step_id, label in GUIDED_CHECKLIST_STEPS:
            done = bool(checklist.get(step_id) is True)
            marker = "[x]" if done else "[ ]"
            st.write(f"{marker} {label}")

        action_cols = st.columns([1, 1])
        with action_cols[0]:
            if st.button("Load beginner defaults", key="guided_load_defaults"):
                _apply_preset("BBM92 Quick")
                _log_ui_event(
                    results_root=results_root,
                    event_name="guided_defaults_loaded",
                    payload={"preset": "BBM92 Quick"},
                )
                st.rerun()
        with action_cols[1]:
            if st.button("Reset checklist", key="guided_reset_checklist"):
                st.session_state[SESSION_GUIDED_CHECKLIST_KEY] = {
                    step: False for step, _ in GUIDED_CHECKLIST_STEPS
                }
                _save_guided_checklist_to_state(
                    results_root=results_root,
                    checklist=st.session_state[SESSION_GUIDED_CHECKLIST_KEY],
                )
                st.session_state[SESSION_FLOW_COMPLETED_EMITTED_KEY] = False
                st.session_state[SESSION_FLOW_ENTERED_TS_KEY] = time.time()
                _log_ui_event(
                    results_root=results_root,
                    event_name="guided_checklist_reset",
                    payload={"experience_mode": mode.lower()},
                )
                _emit_newcomer_event(
                    results_root=results_root,
                    event_name="newcomer_flow_entered",
                    payload={
                        "time_from_enter_ms": 0,
                    },
                )
                st.rerun()
    else:
        st.caption(
            "Power mode keeps all controls visible. Use Golden Path for quick onboarding or jump straight into Expert/PIC lanes."
        )


def _apply_preset(name: str) -> None:
    preset = RUN_PRESETS.get(name, {})
    for key, value in preset.items():
        st.session_state[_builder_key(key)] = value


def _read_builder_state() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in DEFAULT_BUILDER_STATE:
        out[key] = st.session_state.get(_builder_key(key), DEFAULT_BUILDER_STATE[key])
    return out


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Could not parse boolean value: {value!r}")


def _coerce_state_value(key: str, value: Any) -> Any:
    default = DEFAULT_BUILDER_STATE[key]
    if isinstance(default, bool):
        return _coerce_bool(value)
    if isinstance(default, float):
        return float(value)
    if isinstance(default, int):
        return int(round(float(value)))
    return str(value)


def _build_run_profile(state: dict[str, Any]) -> dict[str, Any]:
    builder_state: dict[str, Any] = {}
    for key in sorted(DEFAULT_BUILDER_STATE.keys()):
        builder_state[key] = _coerce_state_value(key, state.get(key, DEFAULT_BUILDER_STATE[key]))

    core = {
        "schema_version": RUN_PROFILE_SCHEMA_VERSION,
        "kind": "photonstrust.ui_run_profile",
        "builder_state": builder_state,
    }
    return {
        **core,
        "profile_hash": stable_json_hash(core),
    }


def _apply_run_profile_to_session(profile_payload: dict[str, Any]) -> tuple[int, int]:
    source = profile_payload.get("builder_state") if isinstance(profile_payload.get("builder_state"), dict) else profile_payload
    if not isinstance(source, dict):
        raise ValueError("Run profile must include a JSON object field `builder_state`.")

    applied = 0
    ignored = 0
    for key in source.keys():
        if key not in DEFAULT_BUILDER_STATE:
            ignored += 1
            continue
        st.session_state[_builder_key(key)] = _coerce_state_value(key, source.get(key))
        applied += 1
    if applied == 0:
        raise ValueError("Run profile did not contain any known builder keys.")
    return applied, ignored


def _find_protocol_enums(registry_payload: dict[str, Any]) -> list[str]:
    return _find_kind_param_enum(
        registry_payload=registry_payload,
        kind_name="qkd.protocol",
        param_name="name",
        fallback=FALLBACK_PROTOCOLS,
    )


def _find_kind_param_enum(
    *,
    registry_payload: dict[str, Any],
    kind_name: str,
    param_name: str,
    fallback: list[str],
) -> list[str]:
    registry = registry_payload.get("registry") if isinstance(registry_payload.get("registry"), dict) else {}
    kinds = registry.get("kinds") if isinstance(registry.get("kinds"), list) else []
    for item in kinds:
        if not isinstance(item, dict):
            continue
        if str(item.get("kind", "")).strip() != str(kind_name).strip():
            continue
        params = item.get("params") if isinstance(item.get("params"), list) else []
        for param in params:
            if not isinstance(param, dict):
                continue
            if str(param.get("name", "")).strip() != str(param_name).strip():
                continue
            enum_vals = param.get("enum")
            if isinstance(enum_vals, list):
                out = [str(v).strip() for v in enum_vals if str(v).strip()]
                if out:
                    return out
    return list(fallback)


def _protocol_params_for_state(state: dict[str, Any]) -> dict[str, Any]:
    protocol_name = str(state["protocol_name"]).strip().upper()
    params: dict[str, Any] = {
        "name": protocol_name,
        "sifting_factor": float(state["sifting_factor"]),
        "ec_efficiency": float(state["ec_efficiency"]),
        "misalignment_prob": float(state["misalignment_prob"]),
    }

    if protocol_name in {"MDI_QKD", "AMDI_QKD"}:
        params["relay_fraction"] = float(state["relay_fraction"])
        params["mu"] = float(state["mu"])
        params["nu"] = float(state["nu"])
        params["omega"] = float(state["omega"])

    if protocol_name in {"PM_QKD", "TF_QKD"}:
        params["relay_fraction"] = float(state["relay_fraction"])
        params["mu"] = float(state["mu"])
        params["phase_slices"] = int(round(float(state["phase_slices"])))

    if protocol_name == "AMDI_QKD":
        params["pairing_window_bins"] = int(round(float(state["pairing_window_bins"])))
        params["pairing_efficiency"] = float(state["pairing_efficiency"])
        params["pairing_error_prob"] = float(state["pairing_error_prob"])

    return params


def _build_qkd_graph(state: dict[str, Any]) -> dict[str, Any]:
    scenario_id = str(state["scenario_id"]).strip() or "ui_qkd_run"
    graph_id = str(state["graph_id"]).strip() or f"ui_qkd_link_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    distance_km = max(0.0, float(state["distance_km"]))

    return {
        "schema_version": "0.1",
        "graph_id": graph_id,
        "profile": "qkd_link",
        "metadata": {
            "title": "UI-generated QKD graph",
            "description": "Generated from PhotonTrust Streamlit Run Builder.",
            "created_at": datetime.now(timezone.utc).date().isoformat(),
        },
        "scenario": {
            "id": scenario_id,
            "distance_km": {"start": distance_km, "stop": distance_km, "step": 1.0},
            "band": str(state["band"]).strip(),
            "wavelength_nm": float(state["wavelength_nm"]),
            "execution_mode": str(state["execution_mode"]).strip().lower(),
        },
        "uncertainty": {},
        "nodes": [
            {
                "id": "source_1",
                "kind": "qkd.source",
                "label": "Emitter",
                "params": {
                    "type": str(state["source_type"]).strip(),
                    "physics_backend": "analytic",
                    "rep_rate_mhz": float(state["rep_rate_mhz"]),
                    "collection_efficiency": float(state["collection_efficiency"]),
                    "coupling_efficiency": float(state["coupling_efficiency"]),
                    "g2_0": float(state["g2_0"]),
                },
            },
            {
                "id": "channel_1",
                "kind": "qkd.channel",
                "label": "Fiber",
                "params": {
                    "model": "fiber",
                    "fiber_loss_db_per_km": float(state["fiber_loss_db_per_km"]),
                    "connector_loss_db": float(state["connector_loss_db"]),
                    "background_counts_cps": float(state["channel_background_counts_cps"]),
                },
            },
            {
                "id": "detector_1",
                "kind": "qkd.detector",
                "label": "Detector",
                "params": {
                    "class": str(state["detector_class"]).strip(),
                    "pde": float(state["pde"]),
                    "dark_counts_cps": float(state["dark_counts_cps"]),
                    "background_counts_cps": float(state["detector_background_counts_cps"]),
                    "jitter_ps_fwhm": float(state["jitter_ps_fwhm"]),
                    "dead_time_ns": float(state["dead_time_ns"]),
                    "afterpulsing_prob": float(state["afterpulsing_prob"]),
                },
            },
            {
                "id": "timing_1",
                "kind": "qkd.timing",
                "label": "Timing",
                "params": {
                    "sync_drift_ps_rms": float(state["sync_drift_ps_rms"]),
                    "coincidence_window_ps": float(state["coincidence_window_ps"]),
                },
            },
            {
                "id": "protocol_1",
                "kind": "qkd.protocol",
                "label": "Protocol",
                "params": _protocol_params_for_state(state),
            },
        ],
        "edges": [
            {"from": "source_1", "to": "channel_1", "kind": "control", "label": "emits into"},
            {"from": "channel_1", "to": "detector_1", "kind": "optical", "label": "propagates"},
        ],
    }


def _extract_first_card_from_run_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    results = payload.get("results") if isinstance(payload.get("results"), dict) else {}
    cards = results.get("cards") if isinstance(results.get("cards"), list) else []
    if cards and isinstance(cards[0], dict):
        return cards[0]
    return None


def _log_ui_event(*, results_root: Path, event_name: str, payload: dict[str, Any]) -> None:
    try:
        path = append_ui_metric_event(results_root=results_root, event_name=event_name, payload=payload)
        st.session_state[SESSION_LAST_UI_EVENT_LOG_KEY] = str(path)
    except Exception:
        # Telemetry should not block product flow.
        pass


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_label_rank(label: str) -> int:
    key = str(label or "").strip().lower()
    order = {
        "qualitative": 0,
        "engineering_grade": 1,
        # Report-level label emitted by _safe_use_label in photonstrust.report.
        "security_target_ready": 2,
        "deployment_grade": 2,
        "production_grade": 3,
    }
    return int(order.get(key, -1))


def _card_display_label(card: dict[str, Any]) -> str:
    scenario = str(card.get("scenario_id", "unknown"))
    band = str(card.get("band", "unknown"))
    key_rate = _safe_float(((card.get("outputs") if isinstance(card.get("outputs"), dict) else {}) or {}).get("key_rate_bps"), 0.0)
    qber = _safe_float(((card.get("derived") if isinstance(card.get("derived"), dict) else {}) or {}).get("qber_total"), 0.5)
    safe = str(((card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}) or {}).get("label", "unknown"))
    return f"{scenario} | {band} | key={key_rate:.4g} | qber={qber:.4f} | {safe}"


def _build_baseline_record_from_card(card: dict[str, Any]) -> dict[str, Any]:
    outputs = card.get("outputs") if isinstance(card.get("outputs"), dict) else {}
    derived = card.get("derived") if isinstance(card.get("derived"), dict) else {}
    safe = card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}
    card_for_hash = {k: v for k, v in card.items() if not str(k).startswith("_ui_")}
    return {
        "scenario_id": str(card.get("scenario_id", "unknown")),
        "band": str(card.get("band", "unknown")),
        "card_path": str(card.get("_ui_card_path", "")).strip(),
        "key_rate_bps": _safe_float(outputs.get("key_rate_bps"), 0.0),
        "qber_total": _safe_float(derived.get("qber_total"), 0.5),
        "safe_use_label": str(safe.get("label", "unknown")),
        "card_hash": stable_json_hash(card_for_hash),
    }


def _promotion_decision(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    b_outputs = baseline.get("outputs") if isinstance(baseline.get("outputs"), dict) else {}
    b_derived = baseline.get("derived") if isinstance(baseline.get("derived"), dict) else {}
    b_safe = baseline.get("safe_use_label") if isinstance(baseline.get("safe_use_label"), dict) else {}

    c_outputs = candidate.get("outputs") if isinstance(candidate.get("outputs"), dict) else {}
    c_derived = candidate.get("derived") if isinstance(candidate.get("derived"), dict) else {}
    c_safe = candidate.get("safe_use_label") if isinstance(candidate.get("safe_use_label"), dict) else {}

    key_b = _safe_float(b_outputs.get("key_rate_bps"), 0.0)
    key_c = _safe_float(c_outputs.get("key_rate_bps"), 0.0)
    qber_b = _safe_float(b_derived.get("qber_total"), 0.5)
    qber_c = _safe_float(c_derived.get("qber_total"), 0.5)
    safe_b = _safe_label_rank(str(b_safe.get("label", "")))
    safe_c = _safe_label_rank(str(c_safe.get("label", "")))

    rel_delta_pct = 0.0 if key_b <= 0.0 else ((key_c - key_b) / max(1e-30, key_b)) * 100.0

    reasons: list[str] = []
    recommend_promote = False

    if key_c <= 0.0:
        reasons.append("Candidate key rate is not positive.")
    if qber_c >= 0.11:
        reasons.append("Candidate QBER is >= 11% threshold.")
    if safe_c < 0:
        reasons.append("Candidate safe-use label is unknown.")

    if not reasons:
        if key_b <= 0.0 and key_c > 0.0:
            recommend_promote = True
            reasons.append("Baseline has zero key rate while candidate has positive key rate.")
        elif rel_delta_pct >= 5.0 and qber_c <= (qber_b + 0.005) and safe_c >= safe_b:
            recommend_promote = True
            reasons.append("Candidate improves key rate >= 5% without unacceptable QBER/safety regression.")
        elif safe_c > safe_b and key_c >= (0.98 * key_b) and qber_c <= (qber_b + 0.01):
            recommend_promote = True
            reasons.append("Candidate improves safe-use level with comparable key rate and acceptable QBER.")
        else:
            reasons.append("Candidate does not beat baseline enough under current promotion policy.")

    return {
        "recommendation": "promote" if recommend_promote else "hold",
        "reasons": reasons,
        "metrics": {
            "baseline_key_rate_bps": key_b,
            "candidate_key_rate_bps": key_c,
            "baseline_qber": qber_b,
            "candidate_qber": qber_c,
            "candidate_key_rate_delta_pct": rel_delta_pct,
            "baseline_safe_rank": safe_b,
            "candidate_safe_rank": safe_c,
        },
    }


def _execute_qkd_run(*, state: dict[str, Any], graph: dict[str, Any], results_root: Path, trigger: str) -> None:
    payload = {
        "graph": graph,
        "project_id": str(state["project_id"]).strip() or "default",
        "execution_mode": str(state["execution_mode"]).strip().lower(),
        "include_qasm": bool(state["include_qasm"]),
    }
    started_ts = datetime.now(timezone.utc).timestamp()
    try:
        with st.spinner("Submitting run to API..."):
            run_payload = api_post_json(state["api_base_url"], "/v0/qkd/run", payload, timeout_s=180.0)
        finished_ts = datetime.now(timezone.utc).timestamp()
        st.session_state["last_qkd_run_payload"] = run_payload

        first_visit_ts = float(st.session_state.get(SESSION_FIRST_VISIT_TS_KEY, started_ts))
        ttfv_seconds = max(0.0, finished_ts - first_visit_ts)
        st.session_state[SESSION_LAST_TTFV_SECONDS_KEY] = float(ttfv_seconds)

        _log_ui_event(
            results_root=results_root,
            event_name="qkd_run_succeeded",
            payload={
                "trigger": trigger,
                "run_id": str(run_payload.get("run_id", "")),
                "protocol_name": str(
                    next(
                        (
                            (node.get("params") or {}).get("name")
                            for node in (graph.get("nodes") if isinstance(graph.get("nodes"), list) else [])
                            if isinstance(node, dict) and str(node.get("kind", "")).strip() == "qkd.protocol"
                        ),
                        "",
                    )
                ),
                "distance_km": float(((graph.get("scenario") or {}).get("distance_km") or {}).get("start", 0.0)),
                "time_to_first_value_s": float(ttfv_seconds),
            },
        )
        _mark_guided_step(results_root=results_root, step_id="first_run_completed")
        st.success(f"Run completed: {run_payload.get('run_id', 'unknown')}")
    except Exception as exc:
        diag = diagnose_api_runtime_error(exc)
        st.session_state[SESSION_LAST_ERROR_DIAG_KEY] = diag
        _log_ui_event(
            results_root=results_root,
            event_name="qkd_run_failed",
            payload={
                "trigger": trigger,
                "error_category": diag.get("category"),
                "error_title": diag.get("title"),
                "error": diag.get("detail"),
            },
        )
        st.error(f"{diag.get('title', 'Run failed')}: {diag.get('detail', str(exc))}")
        st.info(f"Recovery hint: {diag.get('hint', 'Check payload and API logs, then retry.')}")


def _capability_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in CAPABILITY_API_SURFACE:
        rows.append(
            {
                "surface": "API",
                "domain": str(item.get("domain", "")),
                "capability": str(item.get("capability", "")),
                "entrypoint": f"{item.get('method', '')} {item.get('path', '')}",
                "ui_status": str(item.get("ui_status", "")),
                "startup_value": str(item.get("startup_value", "")),
            }
        )
    for item in CAPABILITY_CLI_SURFACE:
        rows.append(
            {
                "surface": "CLI",
                "domain": str(item.get("domain", "")),
                "capability": str(item.get("capability", "")),
                "entrypoint": str(item.get("command", "")),
                "ui_status": "Console reference",
                "startup_value": str(item.get("startup_value", "")),
            }
        )
    return rows


def _capability_qkd_demo_graph() -> dict[str, Any]:
    state = dict(DEFAULT_BUILDER_STATE)
    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    state["scenario_id"] = f"caps_qkd_{now_tag}"
    state["graph_id"] = f"caps_qkd_{now_tag}"
    state["protocol_name"] = "BBM92"
    state["distance_km"] = 25.0
    state["rep_rate_mhz"] = 120.0
    state["execution_mode"] = "preview"
    return _build_qkd_graph(state)


def _capability_orbit_demo_config() -> dict[str, Any]:
    return {
        "orbit_pass": {
            "id": f"caps_orbit_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "band": "c_1550",
            "dt_s": 30,
            "samples": [
                {"t_s": 0, "distance_km": 10, "elevation_deg": 20, "background_counts_cps": 0},
                {"t_s": 30, "distance_km": 50, "elevation_deg": 40, "background_counts_cps": 0},
                {"t_s": 60, "distance_km": 100, "elevation_deg": 70, "background_counts_cps": 0},
            ],
            "cases": [
                {"id": "median", "label": "Median", "channel_overrides": {}},
            ],
        },
        "source": {"type": "emitter_cavity", "g2_0": 0.0},
        "channel": {"model": "free_space"},
        "detector": {"class": "snspd"},
        "timing": {},
        "protocol": {"name": "BBM92"},
        "uncertainty": {},
    }


def _capability_external_result_payload() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "kind": "photonstrust.external_sim_result",
        "simulator_name": "PhotonTrust_Demo_Interop",
        "simulator_version": "0.1",
        "scenario_description": {
            "scenario_id": f"caps_external_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "band": "c_1550",
            "wavelength_nm": 1550.0,
            "protocol": "BB84",
        },
        "metrics": {
            "key_rate_bps": 120.0,
            "qber_total": 0.02,
            "fidelity_est": 0.98,
            "distance_km": 40.0,
        },
        "provenance": {"seed": 7, "notes": "UI capability demo payload"},
    }


def _capability_pic_mzi_graph() -> dict[str, Any]:
    graph = _pic_mzi_template_graph()
    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    graph["graph_id"] = f"caps_pic_mzi_{now_tag}"
    circuit = graph.get("circuit") if isinstance(graph.get("circuit"), dict) else {}
    circuit["id"] = str(graph["graph_id"])
    graph["circuit"] = circuit
    return graph


def _poll_job_terminal_status(api_base_url: str, job_id: str, timeout_s: float = 20.0) -> dict[str, Any]:
    deadline = time.time() + max(1.0, float(timeout_s))
    last_payload: dict[str, Any] = {}
    while time.time() <= deadline:
        payload = api_get_json(api_base_url, f"/v0/jobs/{job_id}/status", timeout_s=15.0)
        last_payload = payload
        status = str(payload.get("status", "")).strip().lower()
        if status in {"succeeded", "failed"}:
            return payload
        time.sleep(0.25)
    return last_payload


def _capability_history_entries() -> list[dict[str, str]]:
    raw = st.session_state.get(SESSION_CAPABILITY_HISTORY_KEY)
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "kind": str(row.get("kind", "")),
                "id": str(row.get("id", "")),
                "source": str(row.get("source", "")),
                "captured_at": str(row.get("captured_at", "")),
            }
        )
    return out


def _append_capability_history(*, kind: str, identifier: str, source: str) -> None:
    ident = str(identifier or "").strip()
    if not ident:
        return
    history = _capability_history_entries()
    deduped = [row for row in history if not (row.get("kind") == kind and row.get("id") == ident)]
    deduped.insert(
        0,
        {
            "kind": str(kind),
            "id": ident,
            "source": str(source),
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    st.session_state[SESSION_CAPABILITY_HISTORY_KEY] = deduped[:30]


def _capability_recent_run_ids(api_base_url: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    for row in _capability_history_entries():
        if str(row.get("kind", "")) != "run":
            continue
        rid = str(row.get("id", "")).strip()
        if rid and rid not in seen:
            out.append(rid)
            seen.add(rid)

    try:
        runs_payload = api_get_json(api_base_url, "/v0/runs?limit=100", timeout_s=20.0)
        runs = runs_payload.get("runs") if isinstance(runs_payload.get("runs"), list) else []
        for row in runs:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("run_id", "")).strip()
            if rid and rid not in seen:
                out.append(rid)
                seen.add(rid)
    except Exception:
        return out
    return out


def _run_capability_demo(*, demo_id: str, api_base_url: str, selected_run_id: str | None = None) -> dict[str, Any]:
    refs: list[dict[str, str]] = []
    summary_rows: list[dict[str, Any]] = []

    if demo_id == "platform_smoke":
        health = api_get_json(api_base_url, "/healthz")
        registry = api_get_json(api_base_url, "/v0/registry/kinds")
        runs_payload = api_get_json(api_base_url, "/v0/runs?limit=20")
        projects_payload = api_get_json(api_base_url, "/v0/projects?limit=20")

        kinds = (((registry.get("registry") if isinstance(registry.get("registry"), dict) else {}) or {}).get("kinds"))
        run_rows = runs_payload.get("runs") if isinstance(runs_payload.get("runs"), list) else []
        project_rows = projects_payload.get("projects") if isinstance(projects_payload.get("projects"), list) else []
        summary_rows = [
            {"metric": "health", "value": health.get("status")},
            {"metric": "version", "value": health.get("version")},
            {"metric": "registered_kinds", "value": len(kinds) if isinstance(kinds, list) else 0},
            {"metric": "runs_visible", "value": len(run_rows)},
            {"metric": "projects_visible", "value": len(project_rows)},
        ]
        return {
            "demo_id": demo_id,
            "summary_rows": summary_rows,
            "response": {
                "health": health,
                "registry": registry,
                "runs": runs_payload,
                "projects": projects_payload,
            },
            "references": refs,
        }

    if demo_id == "qkd_sync":
        payload = {
            "graph": _capability_qkd_demo_graph(),
            "project_id": "startup_pitch",
            "execution_mode": "preview",
            "include_qasm": True,
        }
        run = api_post_json(api_base_url, "/v0/qkd/run", payload, timeout_s=240.0)
        run_id = str(run.get("run_id", "")).strip()
        if run_id:
            refs.append({"kind": "run", "id": run_id, "source": demo_id})

        cards = (((run.get("results") if isinstance(run.get("results"), dict) else {}) or {}).get("cards"))
        first = cards[0] if isinstance(cards, list) and cards and isinstance(cards[0], dict) else {}
        key_rate = ((first.get("outputs") if isinstance(first.get("outputs"), dict) else {}) or {}).get("key_rate_bps")
        qber = ((first.get("derived") if isinstance(first.get("derived"), dict) else {}) or {}).get("qber_total")
        summary_rows = [
            {"metric": "run_id", "value": run_id},
            {"metric": "graph_hash", "value": run.get("graph_hash")},
            {"metric": "key_rate_bps", "value": key_rate},
            {"metric": "qber_total", "value": qber},
        ]
        return {"demo_id": demo_id, "summary_rows": summary_rows, "response": run, "references": refs}

    if demo_id == "qkd_async":
        payload = {
            "graph": _capability_qkd_demo_graph(),
            "project_id": "startup_pitch",
            "execution_mode": "preview",
            "include_qasm": True,
        }
        queued = api_post_json(api_base_url, "/v0/qkd/run/async", payload, timeout_s=60.0)
        job_id = str(queued.get("job_id", "")).strip()
        if job_id:
            refs.append({"kind": "job", "id": job_id, "source": demo_id})
        terminal = _poll_job_terminal_status(api_base_url, job_id, timeout_s=30.0)
        result = terminal.get("result") if isinstance(terminal.get("result"), dict) else {}
        run_id = str(result.get("run_id", "")).strip()
        if run_id:
            refs.append({"kind": "run", "id": run_id, "source": demo_id})
        summary_rows = [
            {"metric": "job_id", "value": job_id},
            {"metric": "status", "value": terminal.get("status")},
            {"metric": "run_id", "value": run_id or "n/a"},
        ]
        return {
            "demo_id": demo_id,
            "summary_rows": summary_rows,
            "response": {"queued": queued, "terminal_status": terminal},
            "references": refs,
        }

    if demo_id == "qkd_external_import":
        payload = {
            "project_id": "startup_pitch",
            "external_result": _capability_external_result_payload(),
        }
        imported = api_post_json(api_base_url, "/v0/qkd/import_external", payload, timeout_s=120.0)
        run_id = str(imported.get("run_id", "")).strip()
        if run_id:
            refs.append({"kind": "run", "id": run_id, "source": demo_id})
        summary_rows = [
            {"metric": "run_id", "value": run_id},
            {"metric": "external_result_hash", "value": imported.get("external_result_hash")},
            {"metric": "card_path", "value": imported.get("card_path")},
        ]
        return {"demo_id": demo_id, "summary_rows": summary_rows, "response": imported, "references": refs}

    if demo_id == "orbit_validate_run":
        config = _capability_orbit_demo_config()
        validation = api_post_json(api_base_url, "/v0/orbit/pass/validate", {"config": config}, timeout_s=60.0)
        run = api_post_json(
            api_base_url,
            "/v0/orbit/pass/run",
            {"config": config, "project_id": "startup_pitch"},
            timeout_s=180.0,
        )
        run_id = str(run.get("run_id", "")).strip()
        if run_id:
            refs.append({"kind": "run", "id": run_id, "source": demo_id})
        errors = (((validation.get("diagnostics") if isinstance(validation.get("diagnostics"), dict) else {}) or {}).get("summary") or {}).get(
            "error_count", 0
        )
        summary_rows = [
            {"metric": "validation_errors", "value": errors},
            {"metric": "run_id", "value": run_id},
            {"metric": "results_path", "value": run.get("results_path")},
            {"metric": "report_html_path", "value": run.get("report_html_path")},
        ]
        return {
            "demo_id": demo_id,
            "summary_rows": summary_rows,
            "response": {"validation": validation, "run": run},
            "references": refs,
        }

    if demo_id == "pic_simulate":
        payload = {
            "graph": _capability_pic_mzi_graph(),
            "wavelength_sweep_nm": [1545.0, 1550.0, 1555.0],
        }
        sim = api_post_json(api_base_url, "/v0/pic/simulate", payload, timeout_s=180.0)
        sweep = (((sim.get("results") if isinstance(sim.get("results"), dict) else {}) or {}).get("sweep"))
        points = sweep.get("points") if isinstance(sweep, dict) and isinstance(sweep.get("points"), list) else []
        summary_rows = [
            {"metric": "graph_hash", "value": sim.get("graph_hash")},
            {"metric": "sweep_points", "value": len(points)},
        ]
        return {"demo_id": demo_id, "summary_rows": summary_rows, "response": sim, "references": refs}

    if demo_id == "pic_workflow_chain":
        graph = _capability_pic_mzi_graph()
        payload = {
            "project_id": "startup_pitch",
            "graph": graph,
            "invdesign": {
                "kind": "mzi_phase",
                "phase_node_id": "ps1",
                "target_output_node": "cpl_out",
                "target_output_port": "out1",
                "target_power_fraction": 0.9,
                "steps": 31,
                "wavelength_sweep_nm": [1550.0],
            },
            "layout": {"pdk": {"name": "generic_silicon_photonics"}, "settings": {"ui_scale_um_per_unit": 1.0}},
            "lvs_lite": {"settings": {"coord_tol_um": 1.0e-6}},
            "klayout": {"settings": {}},
            "spice": {"settings": {"top_name": "PT_TOP", "subckt_prefix": "PT", "include_stub_subckts": True}},
        }
        workflow = api_post_json(api_base_url, "/v0/pic/workflow/invdesign_chain", payload, timeout_s=240.0)
        run_id = str(workflow.get("run_id", "")).strip()
        if run_id:
            refs.append({"kind": "run", "id": run_id, "source": demo_id})
        steps = workflow.get("steps") if isinstance(workflow.get("steps"), dict) else {}
        for step_name in ("invdesign", "layout_build", "lvs_lite", "spice_export"):
            step = steps.get(step_name) if isinstance(steps.get(step_name), dict) else {}
            child_run_id = str(step.get("run_id", "")).strip()
            if child_run_id:
                refs.append({"kind": "run", "id": child_run_id, "source": f"{demo_id}:{step_name}"})
        summary_rows = [
            {"metric": "workflow_run_id", "value": run_id},
            {"metric": "status", "value": workflow.get("status")},
            {"metric": "manifest_path", "value": workflow.get("manifest_path")},
        ]
        return {"demo_id": demo_id, "summary_rows": summary_rows, "response": workflow, "references": refs}

    if demo_id == "performance_drc":
        payload = {
            "project_id": "startup_pitch",
            "routes": [
                {"route_id": "wg_a", "width_um": 0.5, "points_um": [[0.0, 0.0], [100.0, 0.0]]},
                {"route_id": "wg_b", "width_um": 0.5, "points_um": [[0.0, 1.0], [100.0, 1.0]]},
            ],
            "layout_extract": {"max_gap_um": 5.0, "min_parallel_length_um": 1.0},
            "wavelength_sweep_nm": [1550.0],
            "target_xt_db": -40.0,
            "pdk": {"name": "generic_silicon_photonics"},
        }
        perf = api_post_json(api_base_url, "/v0/performance_drc/crosstalk", payload, timeout_s=180.0)
        run_id = str(perf.get("run_id", "")).strip()
        if run_id:
            refs.append({"kind": "run", "id": run_id, "source": demo_id})
        report = perf.get("report") if isinstance(perf.get("report"), dict) else {}
        results = report.get("results") if isinstance(report.get("results"), dict) else {}
        summary_rows = [
            {"metric": "run_id", "value": run_id},
            {"metric": "status", "value": results.get("status")},
            {"metric": "worst_xt_db", "value": results.get("worst_xt_db")},
            {"metric": "recommended_min_gap_um", "value": results.get("recommended_min_gap_um")},
        ]
        return {"demo_id": demo_id, "summary_rows": summary_rows, "response": perf, "references": refs}

    if demo_id == "bundle_publish_verify":
        run_id = str(selected_run_id or "").strip()
        if not run_id:
            raise ValueError("A run ID is required for bundle publish/verify.")
        publish = api_post_json(
            api_base_url,
            f"/v0/runs/{run_id}/bundle/publish?include_children=false",
            {},
            timeout_s=180.0,
        )
        digest = str(publish.get("bundle_sha256", "")).strip()
        if digest:
            refs.append({"kind": "digest", "id": digest, "source": demo_id})
        verify = api_get_json(api_base_url, f"/v0/evidence/bundle/by-digest/{digest}/verify", timeout_s=120.0)
        summary_rows = [
            {"metric": "source_run_id", "value": run_id},
            {"metric": "bundle_sha256", "value": digest},
            {"metric": "verify_ok", "value": ((verify.get("verify") if isinstance(verify.get("verify"), dict) else {}) or {}).get("ok")},
        ]
        return {
            "demo_id": demo_id,
            "summary_rows": summary_rows,
            "response": {
                "publish": publish,
                "verify": verify,
                "download_url": f"{str(api_base_url).rstrip('/')}/v0/evidence/bundle/by-digest/{digest}",
            },
            "references": refs,
        }

    raise ValueError(f"Unknown capability demo: {demo_id}")


def _render_capabilities_console(results_root: Path) -> None:
    _ensure_builder_defaults()
    if "caps_api_base_url" not in st.session_state:
        st.session_state["caps_api_base_url"] = str(st.session_state.get(_builder_key("api_base_url"), "")).strip()

    st.markdown(
        """
        <style>
        .caps-hero {
            border: 1px solid rgba(22, 88, 81, 0.35);
            background: linear-gradient(135deg, rgba(240, 249, 247, 0.95), rgba(247, 252, 251, 0.95));
            border-radius: 14px;
            padding: 14px 18px;
            margin-bottom: 14px;
        }
        .caps-hero h3 {
            margin: 0;
            color: #174d47;
            font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
            letter-spacing: 0.01em;
        }
        .caps-hero p {
            margin: 6px 0 0 0;
            color: #2f4f4a;
            font-family: "Source Serif 4", "Georgia", serif;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="caps-hero">
            <h3>Platform Capabilities Console</h3>
            <p>Startup pitch surface for PhotonTrust: full API/CLI capability map, live demos, and evidence-trace execution IDs.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([2, 1])
    with top_left:
        st.text_input("API base URL", key="caps_api_base_url")
    api_base_url = str(st.session_state.get("caps_api_base_url", "")).strip()
    with top_right:
        if st.button("Check platform", key="caps_check_platform"):
            try:
                health = api_get_json(api_base_url, "/healthz")
                registry = api_get_json(api_base_url, "/v0/registry/kinds")
                runs_payload = api_get_json(api_base_url, "/v0/runs?limit=20")
                kinds = (((registry.get("registry") if isinstance(registry.get("registry"), dict) else {}) or {}).get("kinds"))
                run_rows = runs_payload.get("runs") if isinstance(runs_payload.get("runs"), list) else []
                st.session_state["caps_live_snapshot"] = {
                    "health_status": str(health.get("status", "")),
                    "version": str(health.get("version", "")),
                    "kinds": len(kinds) if isinstance(kinds, list) else 0,
                    "runs": len(run_rows),
                }
                st.success("Platform checks completed.")
            except Exception as exc:
                diag = diagnose_api_runtime_error(exc)
                st.error(f"{diag.get('title', 'Check failed')}: {diag.get('detail', str(exc))}")
                st.info(f"Recovery hint: {diag.get('hint', '')}")

    snapshot = st.session_state.get("caps_live_snapshot")
    kinds_count = int(snapshot.get("kinds", 0)) if isinstance(snapshot, dict) else 0
    runs_count = int(snapshot.get("runs", 0)) if isinstance(snapshot, dict) else 0
    version = str(snapshot.get("version", "unknown")) if isinstance(snapshot, dict) else "unknown"

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("API endpoints", f"{len(CAPABILITY_API_SURFACE)}")
    with m2:
        st.metric("CLI workflows", f"{len(CAPABILITY_CLI_SURFACE)}")
    with m3:
        st.metric("Protocols", f"{len(FALLBACK_PROTOCOLS)}")
    with m4:
        st.metric("Live runs visible", f"{runs_count}" if runs_count > 0 else "-", help=f"Server version: {version}")
    st.caption(f"Registry kinds discovered: {kinds_count} | Server version: {version}")
    st.caption("Auth note: this console assumes `PHOTONTRUST_API_AUTH_MODE=off` for local pitch demos.")

    rows = _capability_rows()
    all_domains = sorted({str(row.get("domain", "")) for row in rows})
    all_surfaces = sorted({str(row.get("surface", "")) for row in rows})
    filter_col_1, filter_col_2 = st.columns(2)
    with filter_col_1:
        selected_domains = st.multiselect("Domain filter", all_domains, default=all_domains, key="caps_domain_filter")
    with filter_col_2:
        selected_surfaces = st.multiselect("Surface filter", all_surfaces, default=all_surfaces, key="caps_surface_filter")
    filtered_rows = [
        row
        for row in rows
        if str(row.get("domain", "")) in selected_domains and str(row.get("surface", "")) in selected_surfaces
    ]
    st.caption(f"Showing {len(filtered_rows)} capability entries.")
    st.table(filtered_rows)

    catalog_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_surface": CAPABILITY_API_SURFACE,
        "cli_surface": CAPABILITY_CLI_SURFACE,
    }
    st.download_button(
        "Download Capability Catalog JSON",
        data=json.dumps(catalog_payload, indent=2, sort_keys=True),
        file_name=f"photonstrust_capability_catalog_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        key="caps_download_catalog",
    )

    st.markdown("**Live Capability Demos**")
    demo_ids = list(CAPABILITY_DEMOS.keys())
    selected_demo = st.selectbox(
        "Demo scenario",
        demo_ids,
        format_func=lambda key: str((CAPABILITY_DEMOS.get(key) or {}).get("title", key)),
        key="caps_demo_id",
    )
    st.caption(str((CAPABILITY_DEMOS.get(selected_demo) or {}).get("description", "")))

    selected_run_id = ""
    if selected_demo == "bundle_publish_verify":
        run_id_options = _capability_recent_run_ids(api_base_url)
        if run_id_options:
            selected_run_id = st.selectbox("Run ID for bundle publish", run_id_options, key="caps_bundle_run_id")
        else:
            st.warning("No run IDs found yet. Execute a run demo first.")

    if st.button("Run Selected Demo", key="caps_run_demo", type="primary"):
        try:
            with st.spinner("Executing capability demo..."):
                result = _run_capability_demo(
                    demo_id=selected_demo,
                    api_base_url=api_base_url,
                    selected_run_id=selected_run_id,
                )
            st.session_state[SESSION_CAPABILITY_LAST_RESULT_KEY] = result

            refs = result.get("references") if isinstance(result.get("references"), list) else []
            for row in refs:
                if not isinstance(row, dict):
                    continue
                _append_capability_history(
                    kind=str(row.get("kind", "")),
                    identifier=str(row.get("id", "")),
                    source=str(row.get("source", selected_demo)),
                )

            _log_ui_event(
                results_root=results_root,
                event_name="capability_demo_succeeded",
                payload={
                    "demo_id": selected_demo,
                    "api_base_url": api_base_url,
                    "reference_count": len(refs),
                },
            )
            st.success(f"Demo completed: {str((CAPABILITY_DEMOS.get(selected_demo) or {}).get('title', selected_demo))}")
        except Exception as exc:
            diag = diagnose_api_runtime_error(exc)
            _log_ui_event(
                results_root=results_root,
                event_name="capability_demo_failed",
                payload={
                    "demo_id": selected_demo,
                    "error_category": diag.get("category"),
                    "error_title": diag.get("title"),
                    "error": diag.get("detail"),
                },
            )
            st.error(f"{diag.get('title', 'Demo failed')}: {diag.get('detail', str(exc))}")
            st.info(f"Recovery hint: {diag.get('hint', 'Check API status and endpoint prerequisites.')}")

    last_result = st.session_state.get(SESSION_CAPABILITY_LAST_RESULT_KEY)
    if isinstance(last_result, dict):
        st.markdown("**Latest Demo Output**")
        summary_rows = last_result.get("summary_rows") if isinstance(last_result.get("summary_rows"), list) else []
        if summary_rows:
            st.table(summary_rows)

        response_payload = last_result.get("response") if isinstance(last_result.get("response"), dict) else {}
        refs = last_result.get("references") if isinstance(last_result.get("references"), list) else []
        ref_rows = [row for row in refs if isinstance(row, dict)]
        if ref_rows:
            st.caption("Captured references")
            st.table(ref_rows)

        download_url = str(response_payload.get("download_url", "")).strip()
        if download_url:
            st.markdown(f"[Download Published Bundle]({download_url})")

        with st.expander("Demo Response JSON", expanded=False):
            st.json(response_payload)

    history = _capability_history_entries()
    if history:
        st.markdown("**Recent Captured IDs**")
        st.table(history[:15])

    st.markdown("**CLI Quickstart Surface**")
    cli_lines: list[str] = []
    for item in CAPABILITY_CLI_SURFACE:
        cli_lines.append(f"# {item['capability']}")
        cli_lines.append(str(item["command"]))
        cli_lines.append("")
    st.code("\n".join(cli_lines).strip() + "\n", language="bash")


def _render_run_builder(results_root: Path) -> None:
    _ensure_builder_defaults()
    _ensure_guided_checklist_defaults()
    experience_mode = _experience_mode()

    if SESSION_FIRST_VISIT_TS_KEY not in st.session_state:
        st.session_state[SESSION_FIRST_VISIT_TS_KEY] = datetime.now(timezone.utc).timestamp()
        _log_ui_event(
            results_root=results_root,
            event_name="session_started",
            payload={
                "api_base_url": str(st.session_state.get(_builder_key("api_base_url"), "")),
            },
        )

    st.subheader("Run Builder")
    st.caption("Build a QKD graph from form inputs, submit to API, and inspect the generated reliability card.")
    st.caption(f"Experience mode: **{experience_mode}**")
    _render_start_here_guide(results_root=results_root)
    _render_glossary_help(title="Run Builder glossary")

    left, right = st.columns([2, 1])
    with left:
        st.text_input("API base URL", key=_builder_key("api_base_url"))
    with right:
        if st.button("Check API health"):
            try:
                health = api_get_json(st.session_state[_builder_key("api_base_url")], "/healthz")
                _mark_guided_step(results_root=results_root, step_id="api_health_checked")
                st.success(f"API OK (version: {health.get('version', 'unknown')})")
            except Exception as exc:
                diag = diagnose_api_runtime_error(exc)
                st.error(f"{diag.get('title', 'API check failed')}: {diag.get('detail', str(exc))}")
                st.info(f"Recovery hint: {diag.get('hint', '')}")

    protocols = FALLBACK_PROTOCOLS
    detector_classes = ["snspd"]
    try:
        registry_payload = api_get_json(st.session_state[_builder_key("api_base_url")], "/v0/registry/kinds")
        protocols = _find_protocol_enums(registry_payload)
        detector_classes = _find_kind_param_enum(
            registry_payload=registry_payload,
            kind_name="qkd.detector",
            param_name="class",
            fallback=detector_classes,
        )
    except Exception as exc:
        diag = diagnose_api_runtime_error(exc)
        st.info("Using fallback protocol list (registry fetch unavailable).")
        st.caption(f"Hint: {diag.get('hint', 'Start API and retry registry fetch.')}")

    preset_cols = st.columns([2, 1])
    with preset_cols[0]:
        preset_name = st.selectbox("Preset", list(RUN_PRESETS.keys()), key=_builder_key("preset_name"))
    with preset_cols[1]:
        st.write("")
        if st.button("Apply preset"):
            _apply_preset(str(preset_name))
            st.rerun()

    st.markdown("**Golden Path (Recommended)**")
    st.caption(
        "1) Use preset, 2) run simulation, 3) confirm decision summary, 4) review card JSON, 5) compare against previous run."
    )
    gp_col_1, gp_col_2 = st.columns([1, 1])
    with gp_col_1:
        if st.button("Run Golden Path Demo", key="run_golden_path"):
            _apply_preset("BBM92 Quick")
            now_tag = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            st.session_state[_builder_key("scenario_id")] = f"golden_path_{now_tag}"
            st.session_state[_builder_key("graph_id")] = f"ui_golden_path_{now_tag}"
            state = _read_builder_state()
            graph = _build_qkd_graph(state)
            _execute_qkd_run(state=state, graph=graph, results_root=results_root, trigger="golden_path")
    with gp_col_2:
        event_log_path = str(st.session_state.get(SESSION_LAST_UI_EVENT_LOG_KEY, "")).strip()
        if event_log_path:
            st.caption(f"Telemetry log: `{event_log_path}`")

    if experience_mode == "Guided":
        basic = st.container()
        advanced = st.expander("Advanced settings (optional)", expanded=False)
    else:
        basic, advanced = st.tabs(["Basic", "Expert"])

    with basic:
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Scenario ID", key=_builder_key("scenario_id"))
            st.text_input("Graph ID", key=_builder_key("graph_id"))
            st.selectbox(
                "Protocol",
                protocols,
                key=_builder_key("protocol_name"),
            )
            st.number_input("Distance (km)", min_value=0.0, step=1.0, key=_builder_key("distance_km"))
            st.selectbox("Band", ["c_1550", "o_1310"], key=_builder_key("band"))
            st.number_input("Wavelength (nm)", min_value=300.0, step=1.0, key=_builder_key("wavelength_nm"))
        with c2:
            st.number_input("Rep rate (MHz)", min_value=0.01, step=1.0, key=_builder_key("rep_rate_mhz"))
            st.number_input("Detector PDE", min_value=0.0, max_value=1.0, step=0.01, key=_builder_key("pde"))
            st.number_input("Dark counts (cps)", min_value=0.0, step=1.0, key=_builder_key("dark_counts_cps"))
            st.number_input("Coincidence window (ps)", min_value=1.0, step=1.0, key=_builder_key("coincidence_window_ps"))
            st.number_input("Misalignment prob", min_value=0.0, max_value=0.5, step=0.001, key=_builder_key("misalignment_prob"))

        protocol_name = str(st.session_state[_builder_key("protocol_name")]).upper()
        st.markdown("**Protocol Parameters**")
        p1, p2, p3 = st.columns(3)
        with p1:
            st.number_input("Sifting factor", min_value=0.0, max_value=1.0, step=0.01, key=_builder_key("sifting_factor"))
            st.number_input("EC efficiency", min_value=1.0, step=0.01, key=_builder_key("ec_efficiency"))
        with p2:
            if protocol_name in {"MDI_QKD", "AMDI_QKD", "PM_QKD", "TF_QKD"}:
                st.number_input("Relay fraction", min_value=0.0, max_value=1.0, step=0.01, key=_builder_key("relay_fraction"))
            if protocol_name in {"MDI_QKD", "AMDI_QKD", "PM_QKD", "TF_QKD"}:
                st.number_input("mu", min_value=0.0, step=0.01, key=_builder_key("mu"))
            if protocol_name in {"MDI_QKD", "AMDI_QKD"}:
                st.number_input("nu", min_value=0.0, step=0.01, key=_builder_key("nu"))
        with p3:
            if protocol_name in {"MDI_QKD", "AMDI_QKD"}:
                st.number_input("omega", min_value=0.0, step=0.01, key=_builder_key("omega"))
            if protocol_name in {"PM_QKD", "TF_QKD"}:
                st.number_input("Phase slices", min_value=2.0, step=1.0, key=_builder_key("phase_slices"))
            if protocol_name == "AMDI_QKD":
                st.number_input("Pairing window bins", min_value=1.0, step=1.0, key=_builder_key("pairing_window_bins"))
                st.number_input("Pairing efficiency", min_value=0.0, max_value=1.0, step=0.01, key=_builder_key("pairing_efficiency"))
                st.number_input(
                    "Pairing error prob",
                    min_value=0.0,
                    max_value=0.5,
                    step=0.001,
                    key=_builder_key("pairing_error_prob"),
                )

    with advanced:
        a1, a2, a3 = st.columns(3)
        with a1:
            st.text_input("Project ID", key=_builder_key("project_id"))
            st.selectbox("Execution mode", ["preview", "certification"], key=_builder_key("execution_mode"))
            st.checkbox("Include QASM artifacts", key=_builder_key("include_qasm"))
            st.selectbox("Source type", ["emitter_cavity", "spdc"], key=_builder_key("source_type"))
            st.number_input("Source g2(0)", min_value=0.0, step=0.001, key=_builder_key("g2_0"))
        with a2:
            st.number_input("Collection efficiency", min_value=0.0, max_value=1.0, step=0.01, key=_builder_key("collection_efficiency"))
            st.number_input("Coupling efficiency", min_value=0.0, max_value=1.0, step=0.01, key=_builder_key("coupling_efficiency"))
            st.number_input("Fiber loss (dB/km)", min_value=0.0, step=0.001, key=_builder_key("fiber_loss_db_per_km"))
            st.number_input("Connector loss (dB)", min_value=0.0, step=0.1, key=_builder_key("connector_loss_db"))
            st.number_input("Channel background (cps)", min_value=0.0, step=1.0, key=_builder_key("channel_background_counts_cps"))
        with a3:
            st.selectbox("Detector class", detector_classes, key=_builder_key("detector_class"))
            st.number_input("Detector background (cps)", min_value=0.0, step=1.0, key=_builder_key("detector_background_counts_cps"))
            st.number_input("Jitter FWHM (ps)", min_value=0.0, step=1.0, key=_builder_key("jitter_ps_fwhm"))
            st.number_input("Dead time (ns)", min_value=0.0, step=1.0, key=_builder_key("dead_time_ns"))
            st.number_input("Afterpulsing prob", min_value=0.0, max_value=1.0, step=0.001, key=_builder_key("afterpulsing_prob"))
            st.number_input("Sync drift RMS (ps)", min_value=0.0, step=1.0, key=_builder_key("sync_drift_ps_rms"))

    state = _read_builder_state()
    graph = _build_qkd_graph(state)
    run_profile = _build_run_profile(state)
    run_profile_json = json.dumps(run_profile, indent=2, sort_keys=True)

    with st.expander("Generated Graph Payload", expanded=False):
        st.code(json.dumps(graph, indent=2), language="json")

    with st.expander("Run Profile (Export / Import)", expanded=False):
        st.caption("Use profiles to reproduce runs, share settings, and avoid manual re-entry.")
        st.code(run_profile_json, language="json")

        c1, c2 = st.columns(2)
        with c1:
            if st.download_button(
                "Download profile JSON",
                data=run_profile_json,
                file_name=f"run_profile_{str(run_profile.get('profile_hash', 'unknown'))[:12]}.json",
                mime="application/json",
                key="download_run_profile_json",
            ):
                _log_ui_event(
                    results_root=results_root,
                    event_name="run_profile_downloaded",
                    payload={"profile_hash": str(run_profile.get("profile_hash", ""))},
                )

            profile_name = st.text_input("Save profile name (optional)", key="save_profile_name")
            if st.button("Save profile to results", key="save_run_profile"):
                try:
                    path = save_ui_run_profile(
                        results_root=results_root,
                        profile=run_profile,
                        profile_name=profile_name if str(profile_name).strip() else None,
                    )
                    st.session_state[SESSION_LAST_PROFILE_PATH_KEY] = str(path)
                    _log_ui_event(
                        results_root=results_root,
                        event_name="run_profile_saved",
                        payload={
                            "profile_hash": str(run_profile.get("profile_hash", "")),
                            "path": str(path),
                        },
                    )
                    st.success(f"Saved profile: {path}")
                except Exception as exc:
                    st.error(f"Could not save run profile: {exc}")

        with c2:
            imported = st.file_uploader("Import profile JSON", type=["json"], key="import_run_profile_file")
            if st.button("Apply imported profile", key="apply_run_profile"):
                if imported is None:
                    st.warning("Upload a profile JSON file first.")
                else:
                    try:
                        raw = imported.getvalue().decode("utf-8")
                        payload = json.loads(raw)
                        if not isinstance(payload, dict):
                            raise ValueError("Profile JSON root must be an object.")
                        applied, ignored = _apply_run_profile_to_session(payload)
                        _log_ui_event(
                            results_root=results_root,
                            event_name="run_profile_imported",
                            payload={
                                "applied_keys": int(applied),
                                "ignored_keys": int(ignored),
                                "profile_hash": str(payload.get("profile_hash", "")),
                            },
                        )
                        st.success(f"Applied profile keys: {applied}, ignored: {ignored}.")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not import run profile: {exc}")

    if st.button("Run Simulation", type="primary", key="run_simulation"):
        _execute_qkd_run(state=state, graph=graph, results_root=results_root, trigger="manual")

    run_payload = st.session_state.get("last_qkd_run_payload")
    if isinstance(run_payload, dict):
        st.markdown("**Latest Run**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.write(f"Run ID: `{run_payload.get('run_id', '')}`")
            st.write(f"Output dir: `{run_payload.get('output_dir', '')}`")
        with col_b:
            compile_cache = run_payload.get("compile_cache") if isinstance(run_payload.get("compile_cache"), dict) else {}
            st.write(f"Graph hash: `{run_payload.get('graph_hash', '')}`")
            st.write(f"Compile cache key: `{compile_cache.get('key', '')}`")

        first_card = _extract_first_card_from_run_payload(run_payload)
        if isinstance(first_card, dict):
            render_card_summary(first_card)
            render_decision_summary(first_card)
            _mark_guided_step(results_root=results_root, step_id="decision_reviewed")
            artifacts = first_card.get("artifacts") if isinstance(first_card.get("artifacts"), dict) else {}
            card_path = str(artifacts.get("card_path", "")).strip()
            if card_path and Path(card_path).exists():
                try:
                    loaded = load_card(Path(card_path))
                    with st.expander("Open Reliability Card JSON", expanded=False):
                        st.json(loaded)
                except Exception as exc:
                    st.warning(f"Could not open card JSON from {card_path}: {exc}")

        artifact_relpaths = run_payload.get("artifact_relpaths") if isinstance(run_payload.get("artifact_relpaths"), dict) else {}
        cards_manifest = artifact_relpaths.get("cards") if isinstance(artifact_relpaths.get("cards"), list) else []
        if cards_manifest and isinstance(cards_manifest[0], dict):
            run_id = str(run_payload.get("run_id", "")).strip()
            card_rel = str(((cards_manifest[0].get("artifacts") or {}).get("card", "")).strip())
            if run_id and card_rel:
                try:
                    url = api_artifact_url(state["api_base_url"], run_id, card_rel)
                    st.caption(f"Card artifact URL: {url}")
                except Exception:
                    pass

        ttfv_seconds = st.session_state.get(SESSION_LAST_TTFV_SECONDS_KEY)
        if isinstance(ttfv_seconds, (int, float)):
            st.metric("Time to first value (s)", f"{float(ttfv_seconds):.2f}")
        profile_path = str(st.session_state.get(SESSION_LAST_PROFILE_PATH_KEY, "")).strip()
        if profile_path:
            st.caption(f"Last saved profile: `{profile_path}`")
        last_diag = st.session_state.get(SESSION_LAST_ERROR_DIAG_KEY)
        if isinstance(last_diag, dict):
            with st.expander("Last Error Diagnosis", expanded=False):
                st.json(last_diag)


def _render_run_registry(results_root: Path) -> None:
    _ensure_guided_checklist_defaults()
    run_paths = list_runs(results_root)
    st.caption(f"Found {len(run_paths)} reliability cards under `{results_root}`.")
    if not run_paths:
        st.info("No reliability cards found.")
        return

    cards_all: list[dict[str, Any]] = []
    bad_cards = 0
    for path in run_paths:
        try:
            card = load_card(Path(path))
        except Exception:
            bad_cards += 1
            continue
        if isinstance(card, dict):
            card["_ui_card_path"] = str(path)
            cards_all.append(card)
    if bad_cards:
        st.warning(f"Skipped {bad_cards} unreadable card file(s).")
    if not cards_all:
        st.info("No readable reliability cards found.")
        return

    key_rates = [float((card.get("outputs") or {}).get("key_rate_bps", 0.0) or 0.0) for card in cards_all]
    qbers = [float((card.get("derived") or {}).get("qber_total", 0.5) or 0.5) for card in cards_all]
    positive_key_rate = sum(1 for value in key_rates if value > 0.0)
    med_qber = statistics.median(qbers) if qbers else 0.5

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Total cards", f"{len(cards_all)}")
    with m2:
        st.metric("Positive key-rate cards", f"{positive_key_rate}/{len(cards_all)}")
    with m3:
        st.metric("Median QBER", f"{med_qber:.4f}")

    bands = sorted({str(card.get("band", "unknown")) for card in cards_all})
    safe_labels = sorted(
        {
            str(((card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}) or {}).get("label", "unknown"))
            for card in cards_all
        }
    )

    band_filter = st.multiselect("Bands", bands, default=bands)
    safe_filter = st.multiselect("Safe use", safe_labels, default=safe_labels)
    filtered = [
        card
        for card in cards_all
        if str(card.get("band", "unknown")) in band_filter
        and str(((card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}) or {}).get("label", "unknown")) in safe_filter
    ]

    selected = st.multiselect(
        "Select runs",
        filtered,
        default=filtered[:1],
        format_func=lambda c: _card_display_label(c),
    )
    cards = list(selected)

    st.markdown("**Decision Workflow**")
    project_id = st.text_input("Project ID for baseline promotion", key=SESSION_DECISION_PROJECT_ID_KEY, value="default")
    baseline_record = get_ui_project_baseline(results_root, project_id)
    baseline_card: dict[str, Any] | None = None
    if isinstance(baseline_record, dict):
        st.caption(
            "Current baseline: "
            f"{baseline_record.get('scenario_id', 'unknown')} | "
            f"{baseline_record.get('band', 'unknown')} | "
            f"key={_safe_float(baseline_record.get('key_rate_bps'), 0.0):.4g} | "
            f"qber={_safe_float(baseline_record.get('qber_total'), 0.5):.4f} | "
            f"{baseline_record.get('safe_use_label', 'unknown')}"
        )
        baseline_card_path = str(baseline_record.get("card_path", "")).strip()
        if baseline_card_path and Path(baseline_card_path).exists():
            try:
                loaded_baseline = load_card(Path(baseline_card_path))
            except Exception:
                loaded_baseline = None
            if isinstance(loaded_baseline, dict):
                loaded_baseline["_ui_card_path"] = baseline_card_path
                baseline_card = loaded_baseline
        else:
            st.warning("Baseline card path no longer exists. Promote a new baseline.")
    else:
        st.info("No baseline promoted yet for this project.")

    promote_col_a, promote_col_b = st.columns([1, 2])
    with promote_col_a:
        promote_disabled = len(cards) == 0
        if st.button("Promote Selected as Baseline", disabled=promote_disabled, key="promote_selected_baseline"):
            candidate = cards[0]
            record = _build_baseline_record_from_card(candidate)
            promoted, state_path = promote_ui_project_baseline(
                results_root=results_root,
                project_id=project_id,
                baseline_record=record,
            )
            _log_ui_event(
                results_root=results_root,
                event_name="baseline_promoted",
                payload={
                    "project_id": str(project_id),
                    "scenario_id": promoted.get("scenario_id"),
                    "band": promoted.get("band"),
                    "card_hash": promoted.get("card_hash"),
                    "state_path": str(state_path),
                },
            )
            st.success(f"Promoted baseline for project `{project_id}`.")
            st.rerun()
    with promote_col_b:
        st.caption("Select at least one run above, then promote it as project baseline.")

    if len(cards) > 1:
        table = [
            {
                "scenario": card["scenario_id"],
                "band": card.get("band"),
                "key_rate_bps": ((card.get("outputs") if isinstance(card.get("outputs"), dict) else {}) or {}).get("key_rate_bps"),
                "qber": ((card.get("derived") if isinstance(card.get("derived"), dict) else {}) or {}).get("qber_total"),
                "safe_use": ((card.get("safe_use_label") if isinstance(card.get("safe_use_label"), dict) else {}) or {}).get("label"),
            }
            for card in cards
        ]
        st.table(table)
    if len(cards) >= 2:
        render_card_delta(cards[0], cards[1])

    if baseline_card is not None and len(cards) >= 1:
        candidate_idx = st.selectbox(
            "Candidate run for baseline decision",
            options=list(range(len(cards))),
            format_func=lambda idx: _card_display_label(cards[int(idx)]),
            key="decision_candidate_index",
        )
        candidate_card = cards[int(candidate_idx)]
        if str(candidate_card.get("_ui_card_path", "")) == str(baseline_card.get("_ui_card_path", "")):
            st.info("Selected candidate is the same as the current baseline.")
        else:
            render_card_delta(baseline_card, candidate_card)
            decision = _promotion_decision(baseline_card, candidate_card)
            _mark_guided_step(results_root=results_root, step_id="compare_decision")
            metrics = decision.get("metrics") if isinstance(decision.get("metrics"), dict) else {}
            st.caption(
                "Policy metrics: "
                f"key_delta={_safe_float(metrics.get('candidate_key_rate_delta_pct'), 0.0):.2f}% | "
                f"baseline_qber={_safe_float(metrics.get('baseline_qber'), 0.5):.4f} | "
                f"candidate_qber={_safe_float(metrics.get('candidate_qber'), 0.5):.4f}"
            )
            reasons = decision.get("reasons") if isinstance(decision.get("reasons"), list) else []
            if str(decision.get("recommendation", "")).lower() == "promote":
                st.success("Recommendation: Promote candidate baseline.")
            else:
                st.warning("Recommendation: Hold current baseline.")
            for reason in reasons:
                st.write(f"- {reason}")

            if st.button("Promote Candidate Baseline", key="promote_candidate_baseline"):
                record = _build_baseline_record_from_card(candidate_card)
                promoted, state_path = promote_ui_project_baseline(
                    results_root=results_root,
                    project_id=project_id,
                    baseline_record=record,
                )
                _log_ui_event(
                    results_root=results_root,
                    event_name="candidate_promoted_from_decision",
                    payload={
                        "project_id": str(project_id),
                        "scenario_id": promoted.get("scenario_id"),
                        "band": promoted.get("band"),
                        "card_hash": promoted.get("card_hash"),
                        "state_path": str(state_path),
                        "recommendation": decision.get("recommendation"),
                    },
                )
                st.success(f"Promoted decision candidate for project `{project_id}`.")
                st.rerun()

    for card in cards:
        render_card_summary(card)
        render_decision_summary(card)
        artifacts = card.get("artifacts") if isinstance(card.get("artifacts"), dict) else {}
        plots = artifacts.get("plots") if isinstance(artifacts.get("plots"), dict) else {}
        plot_path = str(plots.get("key_rate_vs_distance_path", "")).strip()
        if plot_path:
            st.image(plot_path, caption="Key rate vs distance")


def _render_dataset_entries(results_root: Path) -> None:
    dataset_paths = list_dataset_entries(results_root)
    st.caption(f"Found {len(dataset_paths)} dataset entries under `{results_root}`.")
    if not dataset_paths:
        st.info("No dataset entries found.")
        return

    entries = [load_dataset_entry(Path(path)) for path in dataset_paths]
    table = [
        {
            "scenario_id": entry.get("scenario_id"),
            "generated_at": entry.get("metadata", {}).get("generated_at"),
            "seed": entry.get("metadata", {}).get("seed"),
            "path": str(path),
        }
        for entry, path in zip(entries, dataset_paths)
    ]
    st.table(table)


def _pic_chain_template_graph() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "graph_id": "ui_pic_chain",
        "profile": "pic_circuit",
        "metadata": {
            "title": "UI PIC Chain",
            "description": "Streamlit PIC chain template.",
            "created_at": datetime.now(timezone.utc).date().isoformat(),
        },
        "circuit": {"id": "ui_pic_chain", "wavelength_nm": 1550.0},
        "nodes": [
            {"id": "gc_in", "kind": "pic.grating_coupler", "params": {"insertion_loss_db": 2.5}},
            {"id": "wg_1", "kind": "pic.waveguide", "params": {"length_um": 2000.0, "loss_db_per_cm": 2.0}},
            {"id": "ec_out", "kind": "pic.edge_coupler", "params": {"insertion_loss_db": 1.5}},
        ],
        "edges": [
            {"from": "gc_in", "to": "wg_1", "kind": "optical"},
            {"from": "wg_1", "to": "ec_out", "kind": "optical"},
        ],
    }


def _pic_mzi_template_graph() -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "graph_id": "ui_pic_mzi",
        "profile": "pic_circuit",
        "metadata": {
            "title": "UI PIC MZI",
            "description": "Streamlit PIC MZI template (scattering solver).",
            "created_at": datetime.now(timezone.utc).date().isoformat(),
        },
        "circuit": {
            "id": "ui_pic_mzi",
            "wavelength_nm": 1550.0,
            "solver": "scattering",
            "inputs": [
                {"node": "cpl_in", "port": "in1", "amplitude": 1.0},
                {"node": "cpl_in", "port": "in2", "amplitude": 0.0},
            ],
        },
        "nodes": [
            {"id": "cpl_in", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
            {"id": "ps1", "kind": "pic.phase_shifter", "params": {"phase_rad": 0.0, "insertion_loss_db": 0.1}},
            {"id": "ps2", "kind": "pic.phase_shifter", "params": {"phase_rad": 1.0, "insertion_loss_db": 0.1}},
            {"id": "cpl_out", "kind": "pic.coupler", "params": {"coupling_ratio": 0.5, "insertion_loss_db": 0.2}},
        ],
        "edges": [
            {"from": "cpl_in", "from_port": "out1", "to": "ps1", "to_port": "in", "kind": "optical"},
            {"from": "cpl_in", "from_port": "out2", "to": "ps2", "to_port": "in", "kind": "optical"},
            {"from": "ps1", "from_port": "out", "to": "cpl_out", "to_port": "in1", "kind": "optical"},
            {"from": "ps2", "from_port": "out", "to": "cpl_out", "to_port": "in2", "kind": "optical"},
        ],
    }


def _parse_wavelength_sweep_input(raw: str) -> list[float]:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("Sweep list is empty. Provide comma-separated wavelengths (nm).")

    tokens: list[str] = []
    for block in text.replace(";", ",").replace("\n", ",").split(","):
        chunk = str(block).strip()
        if not chunk:
            continue
        for item in chunk.split():
            token = str(item).strip()
            if token:
                tokens.append(token)
    if not tokens:
        raise ValueError("No valid wavelength values found.")

    out: list[float] = []
    for token in tokens:
        value = float(token)
        if value <= 0.0:
            raise ValueError(f"Invalid wavelength: {value}. Values must be > 0.")
        out.append(value)
    return out


def _zip_dir_bytes(root: Path) -> bytes:
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Bundle directory does not exist: {root}")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            zf.write(path, arcname=rel)
    return buffer.getvalue()


def _render_pic_workbench(results_root: Path) -> None:
    _ensure_builder_defaults()

    if SESSION_PIC_GRAPH_JSON_KEY not in st.session_state:
        st.session_state[SESSION_PIC_GRAPH_JSON_KEY] = json.dumps(_pic_chain_template_graph(), indent=2)
    if "pic_api_base_url" not in st.session_state:
        st.session_state["pic_api_base_url"] = str(st.session_state.get(_builder_key("api_base_url"), "")).strip()

    st.subheader("PIC Workbench")
    st.caption("Load a PIC template or edit graph JSON, then run `/v0/pic/simulate` from this UI.")
    _render_glossary_help(title="PIC and reliability glossary")

    top_left, top_right = st.columns([2, 1])
    with top_left:
        st.text_input("API base URL", key="pic_api_base_url")
    pic_api_base = str(st.session_state.get("pic_api_base_url", "")).strip() or str(
        st.session_state.get(_builder_key("api_base_url"), "")
    ).strip()
    with top_right:
        if st.button("Check API health (PIC)", key="pic_check_health"):
            try:
                health = api_get_json(pic_api_base, "/healthz")
                st.success(f"API OK (version: {health.get('version', 'unknown')})")
            except Exception as exc:
                diag = diagnose_api_runtime_error(exc)
                st.error(f"{diag.get('title', 'API check failed')}: {diag.get('detail', str(exc))}")
                st.info(f"Recovery hint: {diag.get('hint', '')}")

    template_col_1, template_col_2 = st.columns([2, 1])
    with template_col_1:
        template_name = st.selectbox("PIC template", ["PIC Chain (loss path)", "PIC MZI (interferometer)"], key="pic_template_name")
    with template_col_2:
        st.write("")
        if st.button("Load PIC template", key="load_pic_template"):
            template_graph = _pic_chain_template_graph() if template_name.startswith("PIC Chain") else _pic_mzi_template_graph()
            st.session_state[SESSION_PIC_GRAPH_JSON_KEY] = json.dumps(template_graph, indent=2)
            st.rerun()

    st.text_area(
        "PIC graph JSON (`profile=pic_circuit`)",
        key=SESSION_PIC_GRAPH_JSON_KEY,
        height=300,
    )

    mode_col_1, mode_col_2 = st.columns([1, 2])
    with mode_col_1:
        sim_mode = st.radio(
            "Simulation mode",
            ["Single wavelength", "Wavelength sweep"],
            key="pic_sim_mode",
        )
    with mode_col_2:
        if sim_mode == "Single wavelength":
            st.number_input(
                "Wavelength (nm)",
                min_value=100.0,
                max_value=5000.0,
                step=1.0,
                key="pic_single_wavelength_nm",
                value=1550.0,
            )
        else:
            st.text_input(
                "Sweep wavelengths (nm, comma-separated)",
                key="pic_sweep_wavelengths",
                value="1540, 1550, 1560",
            )

    if st.button("Run PIC Simulation", type="primary", key="run_pic_simulation"):
        try:
            graph = json.loads(str(st.session_state.get(SESSION_PIC_GRAPH_JSON_KEY, "")).strip())
            if not isinstance(graph, dict):
                raise ValueError("PIC graph JSON must be a JSON object.")

            payload: dict[str, Any] = {"graph": graph}
            if sim_mode == "Single wavelength":
                payload["wavelength_nm"] = float(st.session_state.get("pic_single_wavelength_nm", 1550.0))
            else:
                payload["wavelength_sweep_nm"] = _parse_wavelength_sweep_input(
                    str(st.session_state.get("pic_sweep_wavelengths", ""))
                )

            with st.spinner("Running PIC simulation..."):
                response = api_post_json(pic_api_base, "/v0/pic/simulate", payload, timeout_s=180.0)
            st.session_state[SESSION_LAST_PIC_PAYLOAD_KEY] = response
            st.session_state[SESSION_LAST_PIC_REQUEST_KEY] = payload

            _log_ui_event(
                results_root=results_root,
                event_name="pic_simulation_succeeded",
                payload={
                    "graph_id": str(graph.get("graph_id", "")),
                    "profile": str(graph.get("profile", "")),
                    "mode": "single" if "wavelength_nm" in payload else "sweep",
                },
            )
            st.success("PIC simulation completed.")
        except Exception as exc:
            diag = diagnose_api_runtime_error(exc)
            _log_ui_event(
                results_root=results_root,
                event_name="pic_simulation_failed",
                payload={
                    "error_category": diag.get("category"),
                    "error_title": diag.get("title"),
                    "error": diag.get("detail"),
                },
            )
            st.error(f"{diag.get('title', 'Simulation failed')}: {diag.get('detail', str(exc))}")
            st.info(f"Recovery hint: {diag.get('hint', 'Verify graph JSON and API status.')}")

    pic_payload = st.session_state.get(SESSION_LAST_PIC_PAYLOAD_KEY)
    if not isinstance(pic_payload, dict):
        return

    st.markdown("**Latest PIC Result**")
    st.caption(
        f"generated_at={pic_payload.get('generated_at', '')} | "
        f"graph_hash={pic_payload.get('graph_hash', '')}"
    )

    results = pic_payload.get("results") if isinstance(pic_payload.get("results"), dict) else {}
    sweep = results.get("sweep") if isinstance(results.get("sweep"), dict) else None
    if isinstance(sweep, dict):
        points = sweep.get("points") if isinstance(sweep.get("points"), list) else []
        rows: list[dict[str, Any]] = []
        for pt in points:
            if not isinstance(pt, dict):
                continue
            chain = pt.get("chain_solver") if isinstance(pt.get("chain_solver"), dict) else {}
            rows.append(
                {
                    "wavelength_nm": pt.get("wavelength_nm"),
                    "eta_total": chain.get("eta_total"),
                    "total_loss_db": chain.get("total_loss_db"),
                }
            )
        if rows:
            st.table(rows)
    else:
        chain = results.get("chain_solver") if isinstance(results.get("chain_solver"), dict) else {}
        scatt = results.get("scattering_solver") if isinstance(results.get("scattering_solver"), dict) else {}

        col_1, col_2, col_3 = st.columns(3)
        with col_1:
            st.metric("Solver mode", "single")
        with col_2:
            st.metric("Chain eta_total", f"{_safe_float(chain.get('eta_total'), 0.0):.6f}")
        with col_3:
            st.metric("Chain loss (dB)", f"{_safe_float(chain.get('total_loss_db'), 0.0):.4f}")

        if bool(scatt.get("applicable", False)):
            outputs = scatt.get("external_outputs") if isinstance(scatt.get("external_outputs"), list) else []
            max_power = 0.0
            for row in outputs:
                if not isinstance(row, dict):
                    continue
                max_power = max(max_power, _safe_float(row.get("power"), 0.0))
            st.caption(f"Scattering outputs: {len(outputs)} | max output power: {max_power:.6f}")
        elif str(scatt.get("reason", "")).strip():
            st.caption(f"Scattering solver not applicable: {scatt.get('reason')}")

    with st.expander("PIC Result JSON", expanded=False):
        st.json(pic_payload)

    save_col_1, save_col_2 = st.columns([1, 2])
    with save_col_1:
        if st.button("Save PIC Result Bundle", key="save_pic_result_bundle"):
            try:
                request_payload = st.session_state.get(SESSION_LAST_PIC_REQUEST_KEY)
                if not isinstance(request_payload, dict):
                    request_payload = {
                        "graph": json.loads(str(st.session_state.get(SESSION_PIC_GRAPH_JSON_KEY, "")).strip())
                    }
                saved = save_ui_pic_run_bundle(
                    results_root=results_root,
                    request_payload=request_payload,
                    response_payload=pic_payload,
                )
                bundle_dir = str(saved["bundle_dir"])
                st.session_state[SESSION_LAST_PIC_BUNDLE_DIR_KEY] = bundle_dir
                _log_ui_event(
                    results_root=results_root,
                    event_name="pic_simulation_saved",
                    payload={
                        "bundle_dir": bundle_dir,
                        "graph_hash": str(pic_payload.get("graph_hash", "")),
                    },
                )
                st.success(f"Saved PIC bundle: {bundle_dir}")
            except Exception as exc:
                st.error(f"Could not save PIC bundle: {exc}")
    with save_col_2:
        last_bundle = str(st.session_state.get(SESSION_LAST_PIC_BUNDLE_DIR_KEY, "")).strip()
        if last_bundle:
            st.caption(f"Last saved PIC bundle: `{last_bundle}`")
            bundle_dir = Path(last_bundle)
            try:
                zip_bytes = _zip_dir_bytes(bundle_dir)
                downloaded = st.download_button(
                    "Download Latest Bundle (.zip)",
                    data=zip_bytes,
                    file_name=f"{bundle_dir.name}.zip",
                    mime="application/zip",
                    key="download_latest_pic_bundle_zip",
                )
                if downloaded:
                    _log_ui_event(
                        results_root=results_root,
                        event_name="pic_bundle_zip_downloaded",
                        payload={
                            "bundle_dir": str(bundle_dir),
                            "zip_size_bytes": len(zip_bytes),
                        },
                    )
            except Exception as exc:
                st.warning(f"Could not package latest bundle as zip: {exc}")


def _handle_newcomer_flow_mode_transition(*, results_root: Path, mode_now: str) -> None:
    prev_mode = str(st.session_state.get(SESSION_PREV_EXPERIENCE_MODE_KEY, mode_now)).strip() or mode_now
    checklist_now = st.session_state.get(SESSION_GUIDED_CHECKLIST_KEY)
    complete_now = _is_guided_complete(checklist_now) if isinstance(checklist_now, dict) else False

    if prev_mode != mode_now:
        _log_ui_event(
            results_root=results_root,
            event_name="experience_mode_changed",
            payload={"from": prev_mode.lower(), "to": mode_now.lower()},
        )

        if prev_mode == "Guided" and mode_now != "Guided":
            entered_ts = float(st.session_state.get(SESSION_FLOW_ENTERED_TS_KEY, time.time()))
            completed = bool(st.session_state.get(SESSION_FLOW_COMPLETED_EMITTED_KEY, False) or complete_now)
            _emit_newcomer_event(
                results_root=results_root,
                event_name="newcomer_flow_exited",
                payload={
                    "exit_reason": "mode_switch",
                    "completed": completed,
                    "time_from_enter_ms": int(max(0.0, (time.time() - entered_ts) * 1000.0)),
                },
            )

        if mode_now == "Guided":
            st.session_state[SESSION_FLOW_ENTERED_TS_KEY] = time.time()
            st.session_state[SESSION_FLOW_COMPLETED_EMITTED_KEY] = bool(complete_now)
            _emit_newcomer_event(
                results_root=results_root,
                event_name="newcomer_flow_entered",
                payload={"time_from_enter_ms": 0},
            )

    if mode_now == "Guided" and SESSION_FLOW_ENTERED_TS_KEY not in st.session_state:
        st.session_state[SESSION_FLOW_ENTERED_TS_KEY] = time.time()
        st.session_state[SESSION_FLOW_COMPLETED_EMITTED_KEY] = bool(complete_now)
        _emit_newcomer_event(
            results_root=results_root,
            event_name="newcomer_flow_entered",
            payload={"time_from_enter_ms": 0},
        )

    st.session_state[SESSION_PREV_EXPERIENCE_MODE_KEY] = mode_now


def main() -> None:
    st.set_page_config(page_title="PhotonTrust Workbench", page_icon="PT", layout="wide")

    _ensure_builder_defaults()
    st.title("PhotonTrust Workbench")

    st.sidebar.radio(
        "Experience mode",
        list(EXPERIENCE_MODES),
        key=SESSION_EXPERIENCE_MODE_KEY,
        help="Guided highlights newcomer flow; Power keeps all advanced surfaces front and center.",
    )

    if _experience_mode() == "Guided":
        st.sidebar.caption("Guided mode is active: follow Start Here rails in Run Builder.")
    else:
        st.sidebar.caption("Power mode is active: advanced controls are prioritized.")

    results_default = str(os.environ.get("PHOTONTRUST_RESULTS_ROOT", "results"))
    results_root = Path(st.sidebar.text_input("Results directory", results_default))

    _ensure_guided_checklist_defaults(results_root=results_root)
    mode_now = _experience_mode()
    _handle_newcomer_flow_mode_transition(results_root=results_root, mode_now=mode_now)

    tab_order = ["Capabilities Console", "Run Builder", "PIC", "Run Registry", "Dataset Entries"]
    if mode_now == "Guided":
        tab_order = ["Run Builder", "Run Registry", "PIC", "Capabilities Console", "Dataset Entries"]

    tabs = st.tabs(tab_order)
    for tab, tab_name in zip(tabs, tab_order):
        with tab:
            if tab_name == "Capabilities Console":
                _render_capabilities_console(results_root)
            elif tab_name == "Run Builder":
                _render_run_builder(results_root)
            elif tab_name == "PIC":
                _render_pic_workbench(results_root)
            elif tab_name == "Run Registry":
                _render_run_registry(results_root)
            else:
                _render_dataset_entries(results_root)


if __name__ == "__main__":
    main()
