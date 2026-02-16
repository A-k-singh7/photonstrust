export const GRAPH_SCHEMA_VERSION = "0.1";

export const BAND_OPTIONS = [
  { id: "nir_795", label: "NIR 795 nm" },
  { id: "nir_850", label: "NIR 850 nm" },
  { id: "o_1310", label: "O-band 1310 nm" },
  { id: "c_1550", label: "C-band 1550 nm" },
];

export const PROFILE_OPTIONS = [
  { id: "qkd_link", label: "QKD Link" },
  { id: "pic_circuit", label: "PIC Circuit" },
];

export const KIND_DEFS = {
  "qkd.source": {
    title: "Source",
    category: "qkd",
    ports: { in: [], out: ["out"] },
    portDomains: { in: {}, out: { out: "control" } },
    defaultParams: { type: "emitter_cavity" },
  },
  "qkd.channel": {
    title: "Channel",
    category: "qkd",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "control" }, out: { out: "control" } },
    defaultParams: { model: "fiber" },
  },
  "qkd.detector": {
    title: "Detector",
    category: "qkd",
    ports: { in: ["in"], out: [] },
    portDomains: { in: { in: "control" }, out: {} },
    defaultParams: { class: "snspd" },
  },
  "qkd.timing": {
    title: "Timing",
    category: "qkd",
    ports: { in: [], out: [] },
    portDomains: { in: {}, out: {} },
    defaultParams: { sync_drift_ps_rms: 10 },
  },
  "qkd.protocol": {
    title: "Protocol",
    category: "qkd",
    ports: { in: [], out: [] },
    portDomains: { in: {}, out: {} },
    defaultParams: { name: "BBM92" },
  },

  "pic.grating_coupler": {
    title: "Grating Coupler",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { insertion_loss_db: 2.5 },
  },
  "pic.edge_coupler": {
    title: "Edge Coupler",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { insertion_loss_db: 1.5 },
  },
  "pic.waveguide": {
    title: "Waveguide",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { length_um: 2000, loss_db_per_cm: 2.0 },
  },
  "pic.phase_shifter": {
    title: "Phase Shifter",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { phase_rad: 0.0, insertion_loss_db: 0.1 },
  },
  "pic.ring": {
    title: "Ring (v0.1 placeholder)",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { insertion_loss_db: 0.5 },
  },
  "pic.coupler": {
    title: "2x2 Coupler",
    category: "pic",
    ports: { in: ["in1", "in2"], out: ["out1", "out2"] },
    portDomains: { in: { in1: "optical", in2: "optical" }, out: { out1: "optical", out2: "optical" } },
    defaultParams: { coupling_ratio: 0.5, insertion_loss_db: 0.2 },
  },
};

export function kindDef(kind) {
  return KIND_DEFS[kind] || null;
}

function _defaultDomain(kind) {
  return String(kind || "").startsWith("pic.") ? "optical" : "control";
}

export function portDomainFor(kind, direction, portName) {
  const def = kindDef(kind);
  const dir = String(direction || "").toLowerCase() === "in" ? "in" : "out";
  const port = String(portName || "").trim();
  const domain = def?.portDomains?.[dir]?.[port];
  if (domain == null || domain === "") return _defaultDomain(kind);
  return String(domain);
}
