const VIEW_PRESETS_KEY = "pt_view_presets_v1";
const RECENT_ACTIVITY_KEY = "pt_recent_activity_v1";

function _storage() {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    const probe = "__pt_storage_probe__";
    window.localStorage.setItem(probe, "1");
    window.localStorage.removeItem(probe);
    return window.localStorage;
  } catch {
    return null;
  }
}

function _safeParse(raw, fallback) {
  if (!raw) return fallback;
  try {
    const value = JSON.parse(raw);
    return value == null ? fallback : value;
  } catch {
    return fallback;
  }
}

function _readList(key) {
  const store = _storage();
  if (!store) return [];
  const parsed = _safeParse(store.getItem(key), []);
  return Array.isArray(parsed) ? parsed : [];
}

function _writeList(key, items) {
  const store = _storage();
  if (!store) return false;
  try {
    store.setItem(key, JSON.stringify(Array.isArray(items) ? items : []));
    return true;
  } catch {
    return false;
  }
}

function _id(prefix) {
  const rand = Math.random().toString(36).slice(2, 10);
  return `${prefix}_${Date.now().toString(36)}_${rand}`;
}

function _trimmed(value, fallback = "") {
  const out = String(value == null ? fallback : value).trim();
  return out || fallback;
}

function _object(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function createViewPreset(input = {}) {
  const src = _object(input);
  const now = new Date().toISOString();
  return {
    id: _trimmed(src.id, _id("vp")),
    name: _trimmed(src.name, "Untitled preset"),
    mode: _trimmed(src.mode, "graph"),
    stage: _trimmed(src.stage, "build"),
    graphId: _trimmed(src.graphId, ""),
    view: _object(src.view),
    createdAt: _trimmed(src.createdAt, now),
    updatedAt: _trimmed(src.updatedAt, now),
  };
}

export function loadViewPresets() {
  return _readList(VIEW_PRESETS_KEY).map((item) => createViewPreset(item));
}

export function saveViewPreset(preset, options = {}) {
  const max = Math.max(1, Number(options.max) || 20);
  const next = createViewPreset({ ...preset, updatedAt: new Date().toISOString() });
  const current = loadViewPresets();
  const idx = current.findIndex((item) => item.id === next.id);
  if (idx >= 0) current[idx] = { ...current[idx], ...next };
  else current.unshift(next);
  current.sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));
  const trimmed = current.slice(0, max);
  _writeList(VIEW_PRESETS_KEY, trimmed);
  return trimmed;
}

export function createRecentActivity(input = {}) {
  const src = _object(input);
  const now = new Date().toISOString();
  return {
    id: _trimmed(src.id, _id("act")),
    type: _trimmed(src.type, "info"),
    message: _trimmed(src.message, ""),
    context: _object(src.context),
    createdAt: _trimmed(src.createdAt, now),
  };
}

export function loadRecentActivity() {
  return _readList(RECENT_ACTIVITY_KEY).map((item) => createRecentActivity(item));
}

export function saveRecentActivity(activity, options = {}) {
  const max = Math.max(1, Number(options.max) || 100);
  const entry = createRecentActivity(activity);
  const current = loadRecentActivity();
  current.unshift(entry);
  const trimmed = current.slice(0, max);
  _writeList(RECENT_ACTIVITY_KEY, trimmed);
  return trimmed;
}
