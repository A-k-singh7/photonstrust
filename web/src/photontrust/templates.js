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
