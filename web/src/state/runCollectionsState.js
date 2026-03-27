import { createOpaqueId } from "./randomId";

const RUN_COLLECTIONS_KEY = "pt_run_collections_v1";

export const MAX_COLLECTIONS = 24;
export const MAX_RUNS_PER_COLLECTION = 1000;
export const MAX_TAGS_PER_RUN = 24;
export const MAX_CANDIDATES = 12;

function _storage() {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    const probe = "__pt_run_collections_probe__";
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
    const parsed = JSON.parse(raw);
    return parsed == null ? fallback : parsed;
  } catch {
    return fallback;
  }
}

function _asObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function _asArray(value) {
  return Array.isArray(value) ? value : [];
}

function _trimmed(value, fallback = "") {
  const out = String(value == null ? fallback : value).trim();
  return out || fallback;
}

function _toIso(value) {
  const text = _trimmed(value, "");
  if (!text) return new Date().toISOString();
  const time = Date.parse(text);
  if (!Number.isFinite(time)) return new Date().toISOString();
  return new Date(time).toISOString();
}

function _id(prefix) {
  return createOpaqueId(prefix);
}

function _uniqueTextList(values, max) {
  const limit = Math.max(1, Number(max) || 1);
  const seen = new Set();
  const out = [];
  _asArray(values).forEach((item) => {
    const text = _trimmed(item, "");
    if (!text || seen.has(text)) return;
    seen.add(text);
    out.push(text);
  });
  return out.slice(0, limit);
}

function _normalizeTagsByRun(tagsByRun) {
  const src = _asObject(tagsByRun);
  const out = {};
  Object.entries(src).forEach(([runId, tags]) => {
    const key = _trimmed(runId, "");
    if (!key) return;
    const clean = _uniqueTextList(tags, MAX_TAGS_PER_RUN);
    if (clean.length) out[key] = clean;
  });
  return out;
}

function _normalizeCollection(input = {}, options = {}) {
  const src = _asObject(input);
  const now = new Date().toISOString();
  const maxRuns = Math.max(1, Number(options.maxRunsPerCollection) || MAX_RUNS_PER_COLLECTION);
  const maxCandidates = Math.max(1, Number(options.maxCandidates) || MAX_CANDIDATES);

  const runIds = _uniqueTextList(src.runIds, maxRuns);
  const baselineRunId = _trimmed(src.baselineRunId, "");

  let candidateRunIds = _uniqueTextList(src.candidateRunIds, maxCandidates);
  if (baselineRunId) {
    candidateRunIds = candidateRunIds.filter((id) => id !== baselineRunId);
  }

  const tagsByRun = _normalizeTagsByRun(src.tagsByRun);

  return {
    id: _trimmed(src.id, _id("rc")),
    name: _trimmed(src.name, "Untitled collection"),
    runIds,
    tagsByRun,
    baselineRunId,
    candidateRunIds,
    createdAt: _toIso(src.createdAt || now),
    updatedAt: _toIso(src.updatedAt || now),
  };
}

function _normalizeState(input = {}, options = {}) {
  const src = _asObject(input);
  const maxCollections = Math.max(1, Number(options.maxCollections) || MAX_COLLECTIONS);
  const collections = _asArray(src.collections)
    .map((item) => _normalizeCollection(item, options))
    .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)));

  const unique = [];
  const seen = new Set();
  collections.forEach((item) => {
    if (!item.id || seen.has(item.id)) return;
    seen.add(item.id);
    unique.push(item);
  });

  return {
    version: 1,
    collections: unique.slice(0, maxCollections),
    updatedAt: _toIso(src.updatedAt || new Date().toISOString()),
  };
}

function _writeState(state, storageKey = RUN_COLLECTIONS_KEY) {
  const store = _storage();
  if (!store) return false;
  try {
    store.setItem(storageKey, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function createCollection(input = {}, options = {}) {
  return _normalizeCollection(input, options);
}

export function loadCollectionsState(options = {}) {
  const storageKey = _trimmed(options.storageKey, RUN_COLLECTIONS_KEY);
  const store = _storage();
  if (!store) return _normalizeState({}, options);
  const parsed = _safeParse(store.getItem(storageKey), {});
  return _normalizeState(parsed, options);
}

export function saveCollectionsState(inputState = {}, options = {}) {
  const storageKey = _trimmed(options.storageKey, RUN_COLLECTIONS_KEY);
  const normalized = _normalizeState(inputState, options);
  _writeState({ ...normalized, updatedAt: new Date().toISOString() }, storageKey);
  return normalized;
}

export function loadCollection(collectionId, options = {}) {
  const id = _trimmed(collectionId, "");
  if (!id) return null;
  const state = loadCollectionsState(options);
  return state.collections.find((item) => item.id === id) || null;
}

export function saveCollection(collection, options = {}) {
  const next = _normalizeCollection({ ..._asObject(collection), updatedAt: new Date().toISOString() }, options);
  const state = loadCollectionsState(options);
  const idx = state.collections.findIndex((item) => item.id === next.id);
  const merged = [...state.collections];
  if (idx >= 0) merged[idx] = { ...merged[idx], ...next, updatedAt: new Date().toISOString() };
  else merged.unshift(next);
  return saveCollectionsState({ ...state, collections: merged }, options);
}

export function addTagToRun(collection, runId, tag, options = {}) {
  const src = _normalizeCollection(collection, options);
  const targetRunId = _trimmed(runId, "");
  const nextTag = _trimmed(tag, "");
  if (!targetRunId || !nextTag) return src;

  const maxTags = Math.max(1, Number(options.maxTagsPerRun) || MAX_TAGS_PER_RUN);
  const current = _uniqueTextList(src.tagsByRun[targetRunId], maxTags);
  if (!current.includes(nextTag)) current.push(nextTag);

  const tagsByRun = { ...src.tagsByRun, [targetRunId]: _uniqueTextList(current, maxTags) };
  const runIds = _uniqueTextList([targetRunId, ...src.runIds], Math.max(1, Number(options.maxRunsPerCollection) || MAX_RUNS_PER_COLLECTION));

  return {
    ...src,
    runIds,
    tagsByRun,
    updatedAt: new Date().toISOString(),
  };
}

export function removeTagFromRun(collection, runId, tag, options = {}) {
  const src = _normalizeCollection(collection, options);
  const targetRunId = _trimmed(runId, "");
  const removeTag = _trimmed(tag, "");
  if (!targetRunId || !removeTag) return src;

  const nextTags = _uniqueTextList(src.tagsByRun[targetRunId], MAX_TAGS_PER_RUN).filter((item) => item !== removeTag);
  const tagsByRun = { ...src.tagsByRun };
  if (nextTags.length) tagsByRun[targetRunId] = nextTags;
  else delete tagsByRun[targetRunId];

  return {
    ...src,
    tagsByRun,
    updatedAt: new Date().toISOString(),
  };
}

export function setBaselineRun(collection, runId, options = {}) {
  const src = _normalizeCollection(collection, options);
  const nextBaseline = _trimmed(runId, "");
  const maxRuns = Math.max(1, Number(options.maxRunsPerCollection) || MAX_RUNS_PER_COLLECTION);

  const runIds = nextBaseline ? _uniqueTextList([nextBaseline, ...src.runIds], maxRuns) : src.runIds;
  const candidateRunIds = src.candidateRunIds.filter((id) => id !== nextBaseline);

  return {
    ...src,
    runIds,
    baselineRunId: nextBaseline,
    candidateRunIds,
    updatedAt: new Date().toISOString(),
  };
}

export function setCandidateRuns(collection, runIds, options = {}) {
  const src = _normalizeCollection(collection, options);
  const maxCandidates = Math.max(1, Number(options.maxCandidates) || MAX_CANDIDATES);
  const maxRuns = Math.max(1, Number(options.maxRunsPerCollection) || MAX_RUNS_PER_COLLECTION);

  const filtered = _uniqueTextList(runIds, maxCandidates).filter((id) => id !== src.baselineRunId);
  const mergedRunIds = _uniqueTextList([...filtered, ...src.runIds], maxRuns);

  return {
    ...src,
    runIds: mergedRunIds,
    candidateRunIds: filtered,
    updatedAt: new Date().toISOString(),
  };
}
