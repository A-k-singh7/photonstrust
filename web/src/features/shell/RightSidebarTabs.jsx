export default function RightSidebarTabs({ mode, profile, activeRightTab, onChangeTab }) {
  const getTabId = (tab) => `pt-tab-${mode}-${tab}`;
  const getPanelId = (tab) => `pt-panel-${mode}-${tab}`;

  return (
    <div className="ptTabs" role="tablist" aria-label="Right sidebar tabs">
      {mode === "graph" ? (
        <>
          <button id={getTabId("inspect")} className={`ptTab ${activeRightTab === "inspect" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "inspect"} aria-controls={getPanelId("inspect")} onClick={() => onChangeTab("inspect")}>
            Inspect
          </button>
          <button id={getTabId("compile")} className={`ptTab ${activeRightTab === "compile" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "compile"} aria-controls={getPanelId("compile")} onClick={() => onChangeTab("compile")}>
            Compile
          </button>
          <button id={getTabId("run")} className={`ptTab ${activeRightTab === "run" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "run"} aria-controls={getPanelId("run")} onClick={() => onChangeTab("run")}>
            Run
          </button>
          {profile === "pic_circuit" ? (
            <button id={getTabId("drc")} className={`ptTab ${activeRightTab === "drc" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "drc"} aria-controls={getPanelId("drc")} onClick={() => onChangeTab("drc")}>
              DRC
            </button>
          ) : null}
          {profile === "pic_circuit" ? (
            <button id={getTabId("invdesign")} className={`ptTab ${activeRightTab === "invdesign" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "invdesign"} aria-controls={getPanelId("invdesign")} onClick={() => onChangeTab("invdesign")}>
              InvDesign
            </button>
          ) : null}
          {profile === "pic_circuit" ? (
            <button id={getTabId("layout")} className={`ptTab ${activeRightTab === "layout" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "layout"} aria-controls={getPanelId("layout")} onClick={() => onChangeTab("layout")}>
              Layout
            </button>
          ) : null}
          {profile === "pic_circuit" ? (
            <button id={getTabId("lvs")} className={`ptTab ${activeRightTab === "lvs" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "lvs"} aria-controls={getPanelId("lvs")} onClick={() => onChangeTab("lvs")}>
              LVS-lite
            </button>
          ) : null}
          {profile === "pic_circuit" ? (
            <button id={getTabId("klayout")} className={`ptTab ${activeRightTab === "klayout" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "klayout"} aria-controls={getPanelId("klayout")} onClick={() => onChangeTab("klayout")}>
              KLayout
            </button>
          ) : null}
          {profile === "pic_circuit" ? (
            <button id={getTabId("spice")} className={`ptTab ${activeRightTab === "spice" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "spice"} aria-controls={getPanelId("spice")} onClick={() => onChangeTab("spice")}>
              SPICE
            </button>
          ) : null}
          <button id={getTabId("graph")} className={`ptTab ${activeRightTab === "graph" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "graph"} aria-controls={getPanelId("graph")} onClick={() => onChangeTab("graph")}>
            Graph JSON
          </button>
        </>
      ) : mode === "orbit" ? (
        <>
          <button id={getTabId("orbit")} className={`ptTab ${activeRightTab === "orbit" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "orbit"} aria-controls={getPanelId("orbit")} onClick={() => onChangeTab("orbit")}>
            Config
          </button>
          <button id={getTabId("validate")} className={`ptTab ${activeRightTab === "validate" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "validate"} aria-controls={getPanelId("validate")} onClick={() => onChangeTab("validate")}>
            Validate
          </button>
          <button id={getTabId("run")} className={`ptTab ${activeRightTab === "run" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "run"} aria-controls={getPanelId("run")} onClick={() => onChangeTab("run")}>
            Run
          </button>
        </>
      ) : (
        <>
          <button id={getTabId("manifest")} className={`ptTab ${activeRightTab === "manifest" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "manifest"} aria-controls={getPanelId("manifest")} onClick={() => onChangeTab("manifest")}>
            Manifest
          </button>
          <button id={getTabId("diff")} className={`ptTab ${activeRightTab === "diff" ? "active" : ""}`} role="tab" aria-selected={activeRightTab === "diff"} aria-controls={getPanelId("diff")} onClick={() => onChangeTab("diff")}>
            Diff
          </button>
        </>
      )}
    </div>
  );
}
