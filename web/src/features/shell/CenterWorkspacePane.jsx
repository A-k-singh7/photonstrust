import { ReactFlow, Background, Controls, MiniMap } from "@xyflow/react";
import JsonBox from "../../components/common/JsonBox";

export default function CenterWorkspacePane({
  mode,
  isDragOver,
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  nodeTypes,
  onSelectionChange,
  onCanvasDrop,
  onCanvasDragOver,
  onCanvasDragLeave,
  orbitConfig,
  onApplyOrbitConfigText,
  runsIndex,
  selectedRunId,
  diffLhsRunId,
  diffRhsRunId,
  onLoadRunManifest,
  onSetActiveRightTab,
  onSetDiffLhsRunId,
  onSetDiffRhsRunId,
}) {
  if (mode === "graph") {
    return (
      <section
        className={`ptCanvas${isDragOver ? " ptCanvas--dragover" : ""}`}
        aria-label="Graph editor canvas"
        onDrop={onCanvasDrop}
        onDragOver={onCanvasDragOver}
        onDragLeave={onCanvasDragLeave}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          onSelectionChange={onSelectionChange}
        >
          <Background variant="dots" gap={18} size={1} />
          <Controls />
          <MiniMap pannable zoomable />
        </ReactFlow>
      </section>
    );
  }

  if (mode === "orbit") {
    return (
      <section className="ptCanvas" aria-label="Orbit pass configuration editor">
        <div style={{ padding: 14 }}>
          <div className="ptRightSection">
            <div className="ptRightTitle">Orbit Pass Config</div>
            <div className="ptHint">
              Edit the config and click <span className="ptMono">Run</span> to generate <span className="ptMono">orbit_pass_results.json</span>{" "}
              and <span className="ptMono">orbit_pass_report.html</span>.
            </div>
            <JsonBox
              title="config (JSON)"
              value={orbitConfig}
              onApply={onApplyOrbitConfigText}
              textareaClassName="ptTextarea"
            />
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="ptCanvas" aria-label="Run registry browser">
      <div style={{ padding: 14 }}>
        <div className="ptRightSection">
          <div className="ptRightTitle">Runs</div>
          <div className="ptHint">Select a run to load its manifest. Use Diff to compare the manifest inputs.</div>

          {runsIndex?.status === "idle" ? <div className="ptHint">Click Refresh to load runs from the API.</div> : null}
          {runsIndex?.status === "checking" ? <div className="ptHint">Loading...</div> : null}
          {runsIndex?.status === "error" ? <div className="ptError">{String(runsIndex?.error || "Failed to load runs.")}</div> : null}

          {runsIndex?.status === "ok" && Array.isArray(runsIndex?.runs) && runsIndex.runs.length ? (
            <div className="ptPaletteGrid">
              {runsIndex.runs.map((r) => {
                const rid = String(r?.run_id || "");
                if (!rid) return null;
                const typ = String(r?.run_type || "run");
                const pid = String(r?.project_id || "default");
                const ts = r?.generated_at ? String(r.generated_at) : "";
                const h = r?.input_hash ? String(r.input_hash) : "";
                const hShort = h && h.length > 14 ? `${h.slice(0, 12)}...` : h;
                const protocolSelected = String(r?.protocol_selected || "").trim();
                const multifidelityPresent = Boolean(r?.multifidelity_present);
                const selected = String(selectedRunId || "") === rid;

                return (
                  <button
                    key={rid}
                    className="ptPaletteItem"
                    style={selected ? { borderColor: "rgba(46, 230, 214, 0.55)" } : null}
                    onClick={() => {
                      onLoadRunManifest(rid);
                      onSetActiveRightTab("manifest");
                      if (!diffLhsRunId) onSetDiffLhsRunId(rid);
                      else if (!diffRhsRunId && String(diffLhsRunId) !== rid) onSetDiffRhsRunId(rid);
                    }}
                  >
                    <div className="ptPaletteTitle">{typ}</div>
                    <div className="ptPaletteKind">{rid}</div>
                    {pid ? <div className="ptPaletteKind">{pid}</div> : null}
                    {ts ? <div className="ptPaletteKind">{ts}</div> : null}
                    {protocolSelected ? <div className="ptPaletteKind">protocol: {protocolSelected}</div> : null}
                    {hShort ? <div className="ptPaletteKind">input: {hShort}</div> : null}
                    {multifidelityPresent ? <div className="ptPaletteKind">multifidelity: present</div> : null}
                  </button>
                );
              })}
            </div>
          ) : null}

          {runsIndex?.status === "ok" && (!Array.isArray(runsIndex?.runs) || !runsIndex.runs.length) ? <div className="ptHint">No runs found.</div> : null}
        </div>
      </div>
    </section>
  );
}
