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
  "pic.isolator_2port": {
    title: "Isolator (2-port)",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { insertion_loss_db: 1.0, phase_rad: 0.0, isolation_db: 30.0 },
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
  "pic.mmi": {
    title: "MMI Coupler",
    category: "pic",
    description: "Multimode interference coupler (1\u00d72 or 2\u00d72) using self-imaging",
    ports: { in: ["in1", "in2"], out: ["out1", "out2"] },
    portDomains: {
      in: { in1: "optical", in2: "optical" },
      out: { out1: "optical", out2: "optical" },
    },
    defaultParams: { n_ports_in: 2, n_ports_out: 2, insertion_loss_db: 0.3, imbalance_db: 0.0 },
  },
  "pic.y_branch": {
    title: "Y-Branch",
    category: "pic",
    description: "Passive 1\u00d72 Y-junction power splitter",
    ports: { in: ["in"], out: ["out1", "out2"] },
    portDomains: { in: { in: "optical" }, out: { out1: "optical", out2: "optical" } },
    defaultParams: { insertion_loss_db: 0.2, splitting_ratio: 0.5 },
  },
  "pic.crossing": {
    title: "Waveguide Crossing",
    category: "pic",
    description: "Low-loss waveguide intersection (in1\u2192out1, in2\u2192out2)",
    ports: { in: ["in1", "in2"], out: ["out1", "out2"] },
    portDomains: {
      in: { in1: "optical", in2: "optical" },
      out: { out1: "optical", out2: "optical" },
    },
    defaultParams: { insertion_loss_db: 0.02, crosstalk_db: -40.0 },
  },
  "pic.mzm": {
    title: "MZ Modulator",
    category: "pic",
    description: "Mach-Zehnder modulator with Soref-Bennett plasma dispersion",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: {
      phase_shifter_length_mm: 3.0,
      V_pi_L_pi_Vcm: 2.0,
      voltage_V: 0.0,
      splitting_ratio: 0.5,
      insertion_loss_db: 4.0,
    },
  },
  "pic.photodetector": {
    title: "Photodetector",
    category: "pic",
    description: "Ge-on-Si waveguide PIN photodetector",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: {
      wavelength_nm: 1550.0,
      length_um: 20.0,
      eta_coupling: 0.9,
      alpha_per_cm: 5000.0,
      confinement_factor: 0.8,
    },
  },
  "pic.awg": {
    title: "AWG Demux",
    category: "pic",
    description: "Arrayed waveguide grating wavelength demultiplexer",
    ports: {
      in: ["in"],
      out: ["out1", "out2", "out3", "out4", "out5", "out6", "out7", "out8"],
    },
    portDomains: {
      in: { in: "optical" },
      out: {
        out1: "optical", out2: "optical", out3: "optical", out4: "optical",
        out5: "optical", out6: "optical", out7: "optical", out8: "optical",
      },
    },
    defaultParams: {
      n_channels: 8,
      center_wavelength_nm: 1550.0,
      channel_spacing_nm: 1.6,
      insertion_loss_db: 2.5,
      passband_3dB_nm: 0.5,
    },
  },
  "pic.heater": {
    title: "Thermo-Optic Heater",
    category: "pic",
    description: "Thermo-optic phase tuner (Si/SiN/SiO\u2082)",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { power_mW: 0.0, length_um: 200.0, material: "Si", insertion_loss_db: 0.1 },
  },
  "pic.ssc": {
    title: "Spot-Size Converter",
    category: "pic",
    description: "Inverse-taper edge coupler for fiber-chip coupling",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    defaultParams: { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 },
  },

  "pic.touchstone_2port": {
    title: "Touchstone 2-port (S2P)",
    category: "pic",
    ports: { in: ["in"], out: ["out"] },
    portDomains: { in: { in: "optical" }, out: { out: "optical" } },
    availability: { api_enabled: false, cli_enabled: true },
    defaultParams: { touchstone_path: "", forward: "s21", allow_extrapolation: false },
  },
  "pic.touchstone_nport": {
    title: "Touchstone N-port (SNP)",
    category: "pic",
    ports: { in: ["p1", "p2"], out: ["p3", "p4"] },
    portDomains: {
      in: { p1: "optical", p2: "optical" },
      out: { p3: "optical", p4: "optical" },
    },
    availability: { api_enabled: false, cli_enabled: true },
    defaultParams: {
      touchstone_path: "",
      n_ports: 4,
      in_ports: ["p1", "p2"],
      out_ports: ["p3", "p4"],
      allow_extrapolation: false,
    },
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
