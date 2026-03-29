let fallbackCounter = 0;

function _cryptoApi() {
  return typeof globalThis !== "undefined" && globalThis.crypto ? globalThis.crypto : null;
}

export function randomToken(bytes = 6) {
  const size = Math.max(1, Number(bytes) || 1);
  const cryptoApi = _cryptoApi();
  if (cryptoApi && typeof cryptoApi.getRandomValues === "function") {
    const buffer = new Uint8Array(size);
    cryptoApi.getRandomValues(buffer);
    return Array.from(buffer, (value) => value.toString(16).padStart(2, "0")).join("");
  }

  fallbackCounter += 1;
  return `${Date.now().toString(36)}${fallbackCounter.toString(36)}`;
}

export function createOpaqueId(prefix = "id") {
  const safePrefix = String(prefix || "id").replace(/[^A-Za-z0-9_-]+/g, "_") || "id";
  const cryptoApi = _cryptoApi();
  if (cryptoApi && typeof cryptoApi.randomUUID === "function") {
    return `${safePrefix}_${cryptoApi.randomUUID()}`;
  }
  return `${safePrefix}_${randomToken(8)}`;
}
