import { Handle, Position } from "@xyflow/react";

import { kindDef } from "./kinds";

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

export default function PtNode({ id, data, selected }) {
  const kind = String(data?.kind || "");
  const def = kindDef(kind);
  const categoryGuess = kind.startsWith("pic.") ? "pic" : kind.startsWith("qkd.") ? "qkd" : "custom";
  const title = String(data?.title || def?.title || kind || "Node");
  const category = String(data?.category || def?.category || categoryGuess);
  const inPorts = _ports(data?.inPorts ?? def?.ports?.in);
  const outPorts = _ports(data?.outPorts ?? def?.ports?.out);

  return (
    <div className={`ptNode ${selected ? "isSelected" : ""}`} data-category={category}>
      <div className="ptNodeTop">
        <div className="ptNodeTitle">{title}</div>
        <div className="ptNodeBadge">{category.toUpperCase()}</div>
      </div>

      <div className="ptNodeMid">
        <div className="ptNodeLabel">{String(data?.label || "")}</div>
        <div className="ptNodeId">{String(id)}</div>
      </div>

      {inPorts.map((p, idx) => {
        const top = _portTop(idx, inPorts.length);
        return (
          <div key={`in-${p}`}>
            <Handle
              type="target"
              position={Position.Left}
              id={String(p)}
              className="ptHandle ptHandleIn"
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
        return (
          <div key={`out-${p}`}>
            <Handle
              type="source"
              position={Position.Right}
              id={String(p)}
              className="ptHandle ptHandleOut"
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
