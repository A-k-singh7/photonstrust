import { Handle, Position } from "@xyflow/react";

import { kindDef } from "./kinds";

function _portTop(idx, count) {
  if (count <= 1) return "50%";
  const start = 34;
  const span = 54;
  return `${start + (span * idx) / (count - 1)}%`;
}

export default function PtNode({ id, data, selected }) {
  const kind = String(data?.kind || "");
  const def = kindDef(kind);
  const title = String(def?.title || kind || "Node");
  const category = String(def?.category || "custom");
  const inPorts = Array.isArray(def?.ports?.in) ? def.ports.in : [];
  const outPorts = Array.isArray(def?.ports?.out) ? def.ports.out : [];

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
