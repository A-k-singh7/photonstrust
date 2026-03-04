from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ui import app
from ui.data import load_ui_product_state


def _read_events(results_root: Path) -> list[dict[str, object]]:
    path = results_root / "ui_metrics" / "events.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, object]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = str(raw).strip()
        if not line:
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            out.append(payload)
    return out


def _events_by_name(results_root: Path, name: str) -> list[dict[str, object]]:
    return [item for item in _read_events(results_root) if str(item.get("event", "")) == str(name)]


def _set_checklist(*, complete: bool) -> None:
    app.st.session_state[app.SESSION_GUIDED_CHECKLIST_KEY] = {
        step_id: bool(complete) for step_id, _ in app.GUIDED_CHECKLIST_STEPS
    }


def setup_function() -> None:
    app.st.session_state.clear()


def teardown_function() -> None:
    app.st.session_state.clear()


def test_newcomer_payload_base_includes_required_fields(tmp_path: Path) -> None:
    app.st.session_state[app.SESSION_EXPERIENCE_MODE_KEY] = "Guided"

    payload = app._newcomer_payload_base(results_root=tmp_path)

    assert payload["flow"] == "guided"
    assert payload["flow_version"] == app.NEWCOMER_FLOW_VERSION
    assert str(payload["newcomer_id"]).startswith("st_newcomer_")
    assert str(payload["session_id"]).startswith("st_")
    assert payload["is_newcomer"] is True

    state = load_ui_product_state(tmp_path)
    onboarding = state.get("guided_onboarding") if isinstance(state.get("guided_onboarding"), dict) else {}
    assert onboarding.get("newcomer_id") == payload["newcomer_id"]
    assert app.st.session_state.get(app.SESSION_UI_SESSION_ID_KEY) == payload["session_id"]


def test_flow_exited_emits_completed_and_elapsed_on_guided_leave(tmp_path: Path, monkeypatch) -> None:
    app.st.session_state[app.SESSION_EXPERIENCE_MODE_KEY] = "Power"
    app.st.session_state[app.SESSION_PREV_EXPERIENCE_MODE_KEY] = "Guided"
    app.st.session_state[app.SESSION_FLOW_ENTERED_TS_KEY] = 100.0
    app.st.session_state[app.SESSION_FLOW_COMPLETED_EMITTED_KEY] = False
    _set_checklist(complete=True)

    monkeypatch.setattr(app.time, "time", lambda: 103.25)
    app._handle_newcomer_flow_mode_transition(results_root=tmp_path, mode_now="Power")

    exited = _events_by_name(tmp_path, "newcomer_flow_exited")
    assert len(exited) == 1
    payload = exited[0].get("payload") if isinstance(exited[0].get("payload"), dict) else {}
    assert payload.get("completed") is True
    assert payload.get("time_from_enter_ms") == 3250
    assert payload.get("exit_reason") == "mode_switch"
    assert payload.get("flow") == "power"
    assert payload.get("flow_version") == app.NEWCOMER_FLOW_VERSION
    assert payload.get("is_newcomer") is True


def test_flow_entered_emitted_once_per_guided_entry(tmp_path: Path, monkeypatch) -> None:
    _set_checklist(complete=False)
    app.st.session_state[app.SESSION_EXPERIENCE_MODE_KEY] = "Guided"
    app.st.session_state[app.SESSION_PREV_EXPERIENCE_MODE_KEY] = "Guided"

    monkeypatch.setattr(app.time, "time", lambda: 50.0)
    app._handle_newcomer_flow_mode_transition(results_root=tmp_path, mode_now="Guided")
    app._handle_newcomer_flow_mode_transition(results_root=tmp_path, mode_now="Guided")

    entered = _events_by_name(tmp_path, "newcomer_flow_entered")
    assert len(entered) == 1

    app.st.session_state[app.SESSION_EXPERIENCE_MODE_KEY] = "Power"
    app._handle_newcomer_flow_mode_transition(results_root=tmp_path, mode_now="Power")
    app.st.session_state[app.SESSION_EXPERIENCE_MODE_KEY] = "Guided"
    app._handle_newcomer_flow_mode_transition(results_root=tmp_path, mode_now="Guided")

    entered = _events_by_name(tmp_path, "newcomer_flow_entered")
    assert len(entered) == 2
