export const UI_TELEMETRY_EVENTS = [
  "ui_session_started",
  "ui_guided_flow_started",
  "ui_guided_flow_completed",
  "ui_run_started",
  "ui_run_succeeded",
  "ui_run_failed",
  "ui_error_recovered",
  "ui_compare_completed",
  "ui_packet_exported",
  "ui_demo_mode_completed",
  "newcomer_flow_entered",
  "newcomer_step_completed",
  "newcomer_flow_completed",
  "newcomer_flow_exited",
];

const LOCAL_BUFFER_KEY = "pt_ui_events_buffer_v1";

function _sessionId() {
  const seed = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
  return `ui_${seed}`;
}

function _normalizeOutcome(value) {
  const v = String(value || "").trim().toLowerCase();
  if (v === "success" || v === "failure" || v === "abandoned") return v;
  return "success";
}

function _normalizeBase(apiBase) {
  const raw = String(apiBase || "").trim();
  if (!raw) return "";
  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

function _pushLocal(event) {
  try {
    const cur = JSON.parse(localStorage.getItem(LOCAL_BUFFER_KEY) || "[]");
    const arr = Array.isArray(cur) ? cur : [];
    arr.push(event);
    const trimmed = arr.slice(-500);
    localStorage.setItem(LOCAL_BUFFER_KEY, JSON.stringify(trimmed));
  } catch {
    // Ignore telemetry local buffering failures.
  }
}

function _postEvent(apiBase, event) {
  const base = _normalizeBase(apiBase);
  if (!base) return;

  const url = `${base}/v0/ui/telemetry/events`;
  const body = JSON.stringify(event);

  try {
    if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
      const blob = new Blob([body], { type: "application/json" });
      const sent = navigator.sendBeacon(url, blob);
      if (sent) return;
    }
  } catch {
    // Fall through to fetch.
  }

  fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    keepalive: true,
  }).catch(() => {
    // Best-effort send.
  });
}

export function createUiSessionId() {
  return _sessionId();
}

export function createUiTelemetrySink({ apiBase, getContext }) {
  function emit(eventName, fields = {}) {
    const name = String(eventName || "").trim();
    const context = typeof getContext === "function" ? getContext() || {} : {};

    if (!UI_TELEMETRY_EVENTS.includes(name)) {
      return null;
    }

    const duration = Number(fields.duration_ms);
    const event = {
      event_name: name,
      timestamp_utc: new Date().toISOString(),
      session_id: String(fields.session_id || context.sessionId || ""),
      user_mode: String(fields.user_mode || context.userMode || "builder"),
      profile: String(fields.profile || context.profile || "qkd_link"),
      run_id: fields.run_id ? String(fields.run_id) : null,
      duration_ms: Number.isFinite(duration) && duration >= 0 ? Math.round(duration) : null,
      outcome: _normalizeOutcome(fields.outcome),
      payload: fields.payload && typeof fields.payload === "object" ? fields.payload : {},
    };

    _pushLocal(event);
    _postEvent(apiBase, event);
    return event;
  }

  return { emit };
}
