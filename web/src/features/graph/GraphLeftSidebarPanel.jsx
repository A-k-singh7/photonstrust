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
  const byKind = kindRegistry && typeof kindRegistry === "object" ? kindRegistry.byKind || {} : {};

  return (
    <>
      <div className="ptSidebarSection">
        <div className="ptSidebarTitle">Templates</div>
        <div className="ptBtnRow">
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("qkd")} disabled={busy}>
            QKD Link
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_chain")} disabled={busy}>
            PIC Chain
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_mzi")} disabled={busy}>
            PIC MZI
          </button>
          <button className="ptBtn ptBtnGhost" onClick={() => onLoadTemplate("pic_spice_import")} disabled={busy}>
            SPICE Import
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
                      <div className="ptPaletteTitle">{blueprint.title || k}</div>
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
    </>
  );
}
