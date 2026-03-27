import { useState } from "react";
import ComponentInfoCard from "./ComponentInfoCard";
import { COMPONENT_INFO } from "../../photontrust/componentInfo";

const infoButtonStyle = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: "20px",
  height: "20px",
  border: "1px solid rgba(16, 23, 34, 0.14)",
  borderRadius: "6px",
  background: "rgba(255, 255, 255, 0.7)",
  color: "rgba(16, 23, 34, 0.5)",
  fontSize: "12px",
  fontWeight: 600,
  cursor: "pointer",
  lineHeight: 1,
  padding: 0,
  flexShrink: 0,
  transition: "background 120ms ease, color 120ms ease",
};

export default function GraphLeftSidebarPanel({
  busy = false,
  profile = "qkd_link",
  paletteScope = "all",
  onPaletteScopeChange,
  paletteQuery = "",
  onPaletteQueryChange,
  filteredKindOptions = [],
  kindOptions = [],
  paletteSummary = { apiReady: 0, cliOnly: 0 },
  kindRegistry = { status: "unknown", byKind: {} },
  onAddKind,
  onLoadTemplate,
  onOpenExport,
  onOpenImport,
  requireSchema = true,
  onRequireSchemaChange,
  kindBlueprint,
  kindAvailability,
}) {
  const [infoCardKind, setInfoCardKind] = useState(null);
  const byKind = kindRegistry && typeof kindRegistry === "object" ? kindRegistry.byKind || {} : {};

  return (
    <>
      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">QKD Templates</div>
        <div className="ptBtnRow">
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("qkd")} disabled={busy}>
            QKD Link
          </button>
        </div>
      </div>

      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">PIC Templates</div>
        <div className="ptBtnRow" style={{ flexWrap: "wrap" }}>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_chain")} disabled={busy}>
            PIC Chain
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_mzi")} disabled={busy}>
            PIC MZI
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_spice_import")} disabled={busy}>
            SPICE Import
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_balanced_receiver")} disabled={busy}>
            Balanced Receiver
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_awg_demux")} disabled={busy}>
            AWG Demux
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_ring_filter")} disabled={busy}>
            Ring Filter
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_coherent_rx")} disabled={busy}>
            Coherent Receiver
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_modulator_tx")} disabled={busy}>
            Modulator TX
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_switch_2x2")} disabled={busy}>
            2×2 Switch
          </button>
        </div>
      </div>

      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">
          Palette <span className="ptPaletteHint">drag or click</span>
        </div>
        <div className="ptSegment" role="tablist" aria-label="Palette scope">
          {[
            { id: "all", label: "All" },
            { id: "api", label: "API Ready" },
            { id: "cli", label: "CLI Ready" },
          ].map((scope) => (
            <button
              key={scope.id}
              type="button"
              role="tab"
              aria-selected={paletteScope === scope.id}
              className={`ptSegmentBtn ${paletteScope === scope.id ? "active" : ""}`}
              onClick={() => onPaletteScopeChange(scope.id)}
            >
              {scope.label}
            </button>
          ))}
        </div>
        <label className="ptField">
          <span>Search components</span>
          <input
            value={paletteQuery}
            onChange={(e) => onPaletteQueryChange(String(e.target.value))}
            placeholder={profile === "pic_circuit" ? "Search PIC / SPICE components" : "Search QKD components"}
          />
        </label>
        <div className="ptPaletteCounts">
          Showing {filteredKindOptions.length} of {kindOptions.length} components. API-ready: {paletteSummary.apiReady}. CLI-only:{" "}
          {paletteSummary.cliOnly}.
          {kindRegistry.status === "ok" ? " (registry live)." : " (fallback catalog)."}
        </div>
        {[
          { label: "QKD", prefix: "qkd." },
          { label: "PIC", prefix: "pic." },
        ].map(({ label, prefix }) => {
          const group = filteredKindOptions.filter((k) => k.startsWith(prefix));
          if (!group.length) return null;
          return (
            <div key={label} className="ptPaletteGroup">
              <div className={`ptPaletteGroupLabel ptPaletteGroupLabel--${label.toLowerCase()}`}>{label}</div>
              <div className="ptPaletteGrid">
                {group.map((k) => {
                  const meta = byKind?.[k];
                  const blueprint = kindBlueprint(k, meta);
                  const availability = kindAvailability(k, meta);
                  const note = Array.isArray(meta?.notes) && meta.notes.length ? String(meta.notes[0] || "").trim() : "";
                  const summary = note || `Ports: ${blueprint.inPorts.length} in, ${blueprint.outPorts.length} out.`;
                  const paramCount = Array.isArray(meta?.params) ? meta.params.length : Object.keys(blueprint?.defaultParams || {}).length;
                  const badges = [];
                  if (label === "PIC") badges.push("SPICE");
                  if (availability.apiEnabled) badges.push("API");
                  if (!availability.apiEnabled && availability.cliEnabled) badges.push("CLI-only");
                  if (k === "pic.touchstone_nport") badges.push("N-port");
                  const hasInfo = Boolean(COMPONENT_INFO[k]);
                  return (
                    <div
                      key={k}
                      className={`ptPaletteItem ptPaletteItem--${label.toLowerCase()}`}
                      draggable
                      onDragStart={(e) => {
                        e.dataTransfer.setData("application/reactflow-kind", k);
                        e.dataTransfer.effectAllowed = "move";
                      }}
                      onClick={() => onAddKind(k)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          onAddKind(k);
                        }
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div className="ptPaletteTitle" style={{ flex: 1 }}>{blueprint.title || k}</div>
                        {hasInfo ? (
                          <button
                            style={infoButtonStyle}
                            title={`Info: ${k}`}
                            aria-label={`Show info for ${k}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              setInfoCardKind(k);
                            }}
                            onMouseEnter={(e) => {
                              e.currentTarget.style.background = "rgba(44, 154, 116, 0.12)";
                              e.currentTarget.style.color = "rgba(44, 154, 116, 0.95)";
                              e.currentTarget.style.borderColor = "rgba(44, 154, 116, 0.3)";
                            }}
                            onMouseLeave={(e) => {
                              e.currentTarget.style.background = "rgba(255, 255, 255, 0.7)";
                              e.currentTarget.style.color = "rgba(16, 23, 34, 0.5)";
                              e.currentTarget.style.borderColor = "rgba(16, 23, 34, 0.14)";
                            }}
                          >
                            {"\u2139"}
                          </button>
                        ) : null}
                      </div>
                      <div className="ptPaletteMeta">
                        <div className="ptPaletteKind">{k}</div>
                        {badges.length ? (
                          <div className="ptPaletteBadges">
                            {badges.map((badge) => (
                              <span key={`${k}-${badge}`} className="ptPaletteBadge">
                                {badge}
                              </span>
                            ))}
                          </div>
                        ) : null}
                      </div>
                      <div className="ptPaletteDesc">{summary}</div>
                      <div className="ptPaletteStats">
                        {blueprint.inPorts.length} in / {blueprint.outPorts.length} out · {paramCount} params
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
        {!filteredKindOptions.length ? <div className="ptHint">No components match this filter.</div> : null}
      </div>

      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">Export / Import</div>
        <div className="ptBtnRow">
          <button className="ptBtn ptBtnGhost" onClick={onOpenExport}>
            Export JSON
          </button>
          <button className="ptBtn ptBtnGhost" onClick={onOpenImport}>
            Import JSON
          </button>
        </div>

        <label className="ptCheck">
          <input type="checkbox" checked={requireSchema} onChange={(e) => onRequireSchemaChange(Boolean(e.target.checked))} />
          <span>Require JSON Schema on compile</span>
        </label>
      </div>

      {infoCardKind ? (
        <ComponentInfoCard kind={infoCardKind} onClose={() => setInfoCardKind(null)} />
      ) : null}
    </>
  );
}
