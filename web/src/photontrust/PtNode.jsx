import { Handle, Position } from "@xyflow/react";

import { kindDef, portDomainFor } from "./kinds";
import ComponentSymbol from "./symbols/SymIndex";

function _portTop(idx, count) {
  if (count <= 1) return "50%";
  const start = 34;
  const span = 54;
  return `${start + (span * idx) / (count - 1)}%`;
}

function _ports(items) {
  if (!Array.isArray(items)) return [];
  return items
    .map((p) => String(p || "").trim())
    .filter(Boolean);
}

function _handleClass(domain) {
  if (domain === "optical") return "ptHandle ptHandle--optical";
  if (domain === "electrical") return "ptHandle ptHandle--electrical";
  if (domain === "control") return "ptHandle ptHandle--control";
  return "ptHandle";
}

/** Extract 1-2 key param values to show on the node face. */
function _keyMetrics(kind, params) {
  if (!params || typeof params !== "object") return null;
  const p = params;
  switch (kind) {
    case "pic.mzm":
      return p.voltage_V != null ? `V=${p.voltage_V}V` : null;
    case "pic.awg":
      return p.n_channels != null && p.channel_spacing_nm != null
        ? `${p.n_channels}ch \u00d7 ${p.channel_spacing_nm}nm`
        : null;
    case "pic.heater":
      return p.power_mW != null ? `P=${p.power_mW}mW` : null;
    case "pic.mmi":
      return p.n_ports_in != null && p.n_ports_out != null
        ? `${p.n_ports_in}\u00d7${p.n_ports_out}`
        : null;
    case "pic.waveguide":
      return p.length_um != null ? `L=${p.length_um}\u00b5m` : null;
    case "pic.coupler":
      return p.coupling_ratio != null ? `\u03ba=${p.coupling_ratio}` : null;
    case "pic.y_branch":
      return p.splitting_ratio != null ? `r=${p.splitting_ratio}` : null;
    case "pic.phase_shifter":
      return p.phase_rad != null ? `\u03c6=${Number(p.phase_rad).toFixed(2)}` : null;
    case "pic.ring":
      return p.insertion_loss_db != null ? `IL=${p.insertion_loss_db}dB` : null;
    case "pic.ssc":
      return p.tip_width_nm != null ? `tip=${p.tip_width_nm}nm` : null;
    case "pic.photodetector":
      return p.length_um != null ? `L=${p.length_um}\u00b5m` : null;
    case "pic.crossing":
      return p.crosstalk_db != null ? `XT=${p.crosstalk_db}dB` : null;
    default:
      return null;
  }
}

/** Format simulation result badge. */
function _simBadge(kind, simResult) {
  if (!simResult || typeof simResult !== "object") return null;
  const s = simResult;
  if (s.insertion_loss_db != null) return `IL: ${Number(s.insertion_loss_db).toFixed(1)} dB`;
  if (s.responsivity_A_per_W != null) return `R: ${Number(s.responsivity_A_per_W).toFixed(2)} A/W`;
  if (s.extinction_ratio_db != null) return `ER: ${Number(s.extinction_ratio_db).toFixed(0)} dB`;
  if (s.coupling_loss_db != null) return `CL: ${Number(s.coupling_loss_db).toFixed(1)} dB`;
  if (s.phase_shift_rad != null) return `\u03c6: ${Number(s.phase_shift_rad).toFixed(2)} rad`;
  return null;
}

export default function PtNode({ id, data, selected }) {
  const kind = String(data?.kind || "");
  const def = kindDef(kind);
  const categoryGuess = kind.startsWith("pic.") ? "pic" : kind.startsWith("qkd.") ? "qkd" : "custom";
  const title = String(data?.title || def?.title || kind || "Node");
  const category = String(data?.category || def?.category || categoryGuess);
  const inPorts = _ports(data?.inPorts ?? def?.ports?.in);
  const outPorts = _ports(data?.outPorts ?? def?.ports?.out);

  const isPic = category === "pic";
  const metrics = isPic ? _keyMetrics(kind, data?.params) : null;
  const simBadge = isPic ? _simBadge(kind, data?.simResult) : null;

  return (
    <div className={`ptNode ${selected ? "isSelected" : ""}`} data-category={category}>
      <div className="ptNodeTop">
        <div className="ptNodeTitle">{title}</div>
        <div className="ptNodeBadge">{category.toUpperCase()}</div>
      </div>

      {isPic && (
        <div className="ptNodeSymbol">
          <ComponentSymbol kind={kind} width={100} height={56} />
        </div>
      )}

      <div className="ptNodeMid">
        <div className="ptNodeLabel">{String(data?.label || "")}</div>
        <div className="ptNodeId">{String(id)}</div>
      </div>

      {metrics && (
        <div className="ptNodeMetric">{metrics}</div>
      )}

      {simBadge && (
        <div className="ptNodeResult">{simBadge}</div>
      )}

      {inPorts.map((p, idx) => {
        const top = _portTop(idx, inPorts.length);
        const domain = portDomainFor(kind, "in", p);
        return (
          <div key={`in-${p}`}>
            <Handle
              type="target"
              position={Position.Left}
              id={String(p)}
              className={_handleClass(domain)}
              style={{ top }}
            />
            <div className="ptPortLabel ptPortLabelIn" style={{ top }}>
              {String(p)}
            </div>
          </div>
        );
      })}

      {outPorts.map((p, idx) => {
        const top = _portTop(idx, outPorts.length);
        const domain = portDomainFor(kind, "out", p);
        return (
          <div key={`out-${p}`}>
            <Handle
              type="source"
              position={Position.Right}
              id={String(p)}
              className={_handleClass(domain)}
              style={{ top }}
            />
            <div className="ptPortLabel ptPortLabelOut" style={{ top }}>
              {String(p)}
            </div>
          </div>
        );
      })}
    </div>
  );
}
