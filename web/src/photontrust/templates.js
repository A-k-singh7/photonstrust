import { KIND_DEFS } from "./kinds";

function node(id, kind, x, y, label, params) {
  const def = KIND_DEFS[kind];
  return {
    id,
    type: "ptNode",
    position: { x, y },
    data: {
      id,
      kind,
      label: label || (def ? def.title : kind),
      params: params || (def ? { ...def.defaultParams } : {}),
    },
  };
}

function edge(id, source, target, sourceHandle, targetHandle) {
  const e = { id, source, target };
  if (sourceHandle) e.sourceHandle = sourceHandle;
  if (targetHandle) e.targetHandle = targetHandle;
  return e;
}

export function templateQkdLink() {
  const nodes = [
    node("source", "qkd.source", 80, 80, "Source", null),
    node("channel", "qkd.channel", 320, 80, "Channel", null),
    node("detector", "qkd.detector", 560, 80, "Detector", null),
    node("timing", "qkd.timing", 200, 220, "Timing", null),
    node("protocol", "qkd.protocol", 440, 220, "Protocol", null),
  ];
  const edges = [
    edge("e1", "source", "channel", "out", "in"),
    edge("e2", "channel", "detector", "out", "in"),
  ];
  return { nodes, edges };
}

export function templatePicChain() {
  const nodes = [
    node("gc_in", "pic.grating_coupler", 80, 120, "GC In", { insertion_loss_db: 2.5 }),
    node("wg_1", "pic.waveguide", 290, 120, "WG 1", { length_um: 2000, loss_db_per_cm: 2.0 }),
    node("ring_1", "pic.ring", 510, 120, "Ring", { insertion_loss_db: 0.5 }),
    node("wg_2", "pic.waveguide", 730, 120, "WG 2", { length_um: 1500, loss_db_per_cm: 2.0 }),
    node("ec_out", "pic.edge_coupler", 950, 120, "Edge Out", { insertion_loss_db: 1.5 }),
  ];
  const edges = [
    edge("e1", "gc_in", "wg_1", "out", "in"),
    edge("e2", "wg_1", "ring_1", "out", "in"),
    edge("e3", "ring_1", "wg_2", "out", "in"),
    edge("e4", "wg_2", "ec_out", "out", "in"),
  ];
  return { nodes, edges };
}

export function templatePicMzi() {
  const nodes = [
    node("cpl_in", "pic.coupler", 120, 160, "Coupler In", { coupling_ratio: 0.5, insertion_loss_db: 0.2 }),
    node("ps1", "pic.phase_shifter", 360, 80, "Arm 1", { phase_rad: 0.0, insertion_loss_db: 0.1 }),
    node("ps2", "pic.phase_shifter", 360, 240, "Arm 2", { phase_rad: 0.0, insertion_loss_db: 0.1 }),
    node("cpl_out", "pic.coupler", 620, 160, "Coupler Out", { coupling_ratio: 0.5, insertion_loss_db: 0.2 }),
  ];
  const edges = [
    edge("e1", "cpl_in", "ps1", "out1", "in"),
    edge("e2", "cpl_in", "ps2", "out2", "in"),
    edge("e3", "ps1", "cpl_out", "out", "in1"),
    edge("e4", "ps2", "cpl_out", "out", "in2"),
  ];
  return { nodes, edges };
}

export function templatePicSpiceImportHarness() {
  const nodes = [
    node("gc_in", "pic.grating_coupler", 80, 140, "Input Coupler", { insertion_loss_db: 2.5 }),
    node("ts_model", "pic.touchstone_2port", 340, 140, "Touchstone Model", {
      touchstone_path: "models/component.s2p",
      forward: "s21",
      allow_extrapolation: false,
    }),
    node("iso_out", "pic.isolator_2port", 600, 140, "Output Isolator", { insertion_loss_db: 1.0, isolation_db: 30.0 }),
    node("ec_out", "pic.edge_coupler", 860, 140, "Edge Out", { insertion_loss_db: 1.5 }),
  ];
  const edges = [
    edge("e1", "gc_in", "ts_model", "out", "in"),
    edge("e2", "ts_model", "iso_out", "out", "in"),
    edge("e3", "iso_out", "ec_out", "out", "in"),
  ];
  return { nodes, edges };
}

/* ── New PIC Engineering Design Templates ─────────────────────────── */

export function templatePicBalancedReceiver() {
  const nodes = [
    node("ssc_in", "pic.ssc", 80, 160, "SSC In", { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 }),
    node("cpl", "pic.coupler", 330, 160, "2×2 Coupler", { coupling_ratio: 0.5, insertion_loss_db: 0.2 }),
    node("pd_1", "pic.photodetector", 580, 80, "PD 1", { wavelength_nm: 1550.0, length_um: 20.0, eta_coupling: 0.9, alpha_per_cm: 5000.0, confinement_factor: 0.8 }),
    node("pd_2", "pic.photodetector", 580, 240, "PD 2", { wavelength_nm: 1550.0, length_um: 20.0, eta_coupling: 0.9, alpha_per_cm: 5000.0, confinement_factor: 0.8 }),
  ];
  const edges = [
    edge("e1", "ssc_in", "cpl", "out", "in1"),
    edge("e2", "cpl", "pd_1", "out1", "in"),
    edge("e3", "cpl", "pd_2", "out2", "in"),
  ];
  return { nodes, edges };
}

export function templatePicAwgDemux() {
  const nodes = [
    node("ssc_in", "pic.ssc", 80, 260, "SSC In", { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 }),
    node("awg", "pic.awg", 330, 260, "AWG (8ch)", { n_channels: 8, center_wavelength_nm: 1550.0, channel_spacing_nm: 1.6, insertion_loss_db: 2.5, passband_3dB_nm: 0.5 }),
    node("ec_ch1", "pic.edge_coupler", 580, 80, "Ch 1 Out", { insertion_loss_db: 1.5 }),
    node("ec_ch2", "pic.edge_coupler", 580, 200, "Ch 2 Out", { insertion_loss_db: 1.5 }),
    node("ec_ch3", "pic.edge_coupler", 580, 320, "Ch 3 Out", { insertion_loss_db: 1.5 }),
    node("ec_ch4", "pic.edge_coupler", 580, 440, "Ch 4 Out", { insertion_loss_db: 1.5 }),
  ];
  const edges = [
    edge("e1", "ssc_in", "awg", "out", "in"),
    edge("e2", "awg", "ec_ch1", "out1", "in"),
    edge("e3", "awg", "ec_ch2", "out2", "in"),
    edge("e4", "awg", "ec_ch3", "out3", "in"),
    edge("e5", "awg", "ec_ch4", "out4", "in"),
  ];
  return { nodes, edges };
}

export function templatePicRingFilter() {
  const nodes = [
    node("gc_in", "pic.grating_coupler", 80, 120, "GC In", { insertion_loss_db: 2.5 }),
    node("wg_bus", "pic.waveguide", 330, 120, "Bus WG", { length_um: 500, loss_db_per_cm: 2.0 }),
    node("ring", "pic.ring", 580, 120, "Ring Resonator", { insertion_loss_db: 0.5 }),
    node("wg_drop", "pic.waveguide", 830, 120, "Drop WG", { length_um: 500, loss_db_per_cm: 2.0 }),
    node("ec_out", "pic.edge_coupler", 1080, 120, "Edge Out", { insertion_loss_db: 1.5 }),
  ];
  const edges = [
    edge("e1", "gc_in", "wg_bus", "out", "in"),
    edge("e2", "wg_bus", "ring", "out", "in"),
    edge("e3", "ring", "wg_drop", "out", "in"),
    edge("e4", "wg_drop", "ec_out", "out", "in"),
  ];
  return { nodes, edges };
}

export function templatePicCoherentRx() {
  const nodes = [
    node("ssc_sig", "pic.ssc", 80, 100, "Signal In", { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 }),
    node("ssc_lo", "pic.ssc", 80, 220, "LO In", { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 }),
    node("hybrid", "pic.mmi", 330, 160, "90° Hybrid", { n_ports_in: 2, n_ports_out: 2, insertion_loss_db: 0.3, imbalance_db: 0.0 }),
    node("pd_i", "pic.photodetector", 580, 100, "PD I", { wavelength_nm: 1550.0, length_um: 20.0, eta_coupling: 0.9, alpha_per_cm: 5000.0, confinement_factor: 0.8 }),
    node("pd_q", "pic.photodetector", 580, 220, "PD Q", { wavelength_nm: 1550.0, length_um: 20.0, eta_coupling: 0.9, alpha_per_cm: 5000.0, confinement_factor: 0.8 }),
  ];
  const edges = [
    edge("e1", "ssc_sig", "hybrid", "out", "in1"),
    edge("e2", "ssc_lo", "hybrid", "out", "in2"),
    edge("e3", "hybrid", "pd_i", "out1", "in"),
    edge("e4", "hybrid", "pd_q", "out2", "in"),
  ];
  return { nodes, edges };
}

export function templatePicModulatorTx() {
  const nodes = [
    node("ssc_in", "pic.ssc", 80, 120, "SSC In", { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 }),
    node("mzm", "pic.mzm", 330, 120, "MZM", { phase_shifter_length_mm: 3.0, V_pi_L_pi_Vcm: 2.0, voltage_V: 0.0, splitting_ratio: 0.5, insertion_loss_db: 4.0 }),
    node("heater_bias", "pic.heater", 580, 120, "Heater (Bias)", { power_mW: 0.0, length_um: 200.0, material: "Si", insertion_loss_db: 0.1 }),
    node("ssc_out", "pic.ssc", 830, 120, "SSC Out", { tip_width_nm: 200.0, fiber_mfd_um: 10.4, core_thickness_nm: 220.0 }),
  ];
  const edges = [
    edge("e1", "ssc_in", "mzm", "out", "in"),
    edge("e2", "mzm", "heater_bias", "out", "in"),
    edge("e3", "heater_bias", "ssc_out", "out", "in"),
  ];
  return { nodes, edges };
}

export function templatePicSwitch2x2() {
  const nodes = [
    node("cpl_in", "pic.coupler", 80, 160, "In Coupler", { coupling_ratio: 0.5, insertion_loss_db: 0.2 }),
    node("heater_arm1", "pic.heater", 330, 80, "Heater Arm 1", { power_mW: 0.0, length_um: 200.0, material: "Si", insertion_loss_db: 0.1 }),
    node("heater_arm2", "pic.heater", 330, 240, "Heater Arm 2", { power_mW: 0.0, length_um: 200.0, material: "Si", insertion_loss_db: 0.1 }),
    node("cpl_out", "pic.coupler", 580, 160, "Out Coupler", { coupling_ratio: 0.5, insertion_loss_db: 0.2 }),
    node("ec_out1", "pic.edge_coupler", 830, 80, "Out 1", { insertion_loss_db: 1.5 }),
    node("ec_out2", "pic.edge_coupler", 830, 240, "Out 2", { insertion_loss_db: 1.5 }),
  ];
  const edges = [
    edge("e1", "cpl_in", "heater_arm1", "out1", "in"),
    edge("e2", "cpl_in", "heater_arm2", "out2", "in"),
    edge("e3", "heater_arm1", "cpl_out", "out", "in1"),
    edge("e4", "heater_arm2", "cpl_out", "out", "in2"),
    edge("e5", "cpl_out", "ec_out1", "out1", "in"),
    edge("e6", "cpl_out", "ec_out2", "out2", "in"),
  ];
  return { nodes, edges };
}
