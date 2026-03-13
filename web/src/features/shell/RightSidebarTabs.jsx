import { useMemo, useRef } from "react";

const TAB_GROUP_META = {
  core: { label: "Core", description: "Main workflow panels for the current task." },
  evidence: { label: "Evidence", description: "Panels used to review trust, manifests, and decision records." },
  advanced: { label: "Advanced", description: "Engineering surfaces for optimization, layout, and fabrication tooling." },
  diagnostics: { label: "Diagnostics", description: "Raw payloads and lower-level debug surfaces." },
};

function tabItemsForMode(mode, profile, experienceMode) {
  if (mode === "graph") {
    const rows = [
      { id: "inspect", label: "Setup", group: "core", description: "Set the main design, scenario, and metadata inputs before compiling." },
      { id: "compile", label: "Assumptions", group: "core", description: "Review assumptions, diagnostics, and compiled artifacts before running." },
      { id: "run", label: "Results", group: "core", description: "See decision-ready outputs, confidence, and recommended next actions." },
    ];
    if (profile === "pic_circuit") {
      if (experienceMode !== "guided") {
        rows.push(
          { id: "drc", label: "DRC", group: "advanced", description: "Check PIC crosstalk and spacing constraints before layout export." },
          { id: "invdesign", label: "Optimize", group: "advanced", description: "Tune PIC parameters and run the chained optimization workflow." },
          { id: "layout", label: "GDS/Layout", group: "advanced", description: "Generate layout artifacts and emit a GDS-ready design package." },
          { id: "lvs", label: "LVS-lite", group: "advanced", description: "Run lightweight netlist-vs-layout checks before signoff." },
          { id: "klayout", label: "Extract/Verify", group: "advanced", description: "Package GDS artifacts, extraction outputs, and DRC-lite checks." },
          { id: "spice", label: "SPICE", group: "advanced", description: "Export SPICE-compatible artifacts for downstream circuit analysis." },
        );
      }
    }
    rows.push({ id: "graph", label: "Graph JSON", group: "diagnostics", description: "Inspect or copy the raw graph payload for debugging and advanced edits." });
    return rows;
  }

  if (mode === "orbit") {
    return [
      { id: "orbit", label: "Scenario", group: "core", description: "Set the orbit scenario and operating assumptions." },
      { id: "validate", label: "Preflight", group: "core", description: "Check schema and scenario validity before execution." },
      { id: "run", label: "Results", group: "core", description: "Review orbit-pass outputs, artifacts, and decision context." },
    ];
  }

  return [
    { id: "manifest", label: "Evidence", group: "evidence", description: "Review approvals, trust artifacts, workflow lineage, and served evidence." },
    { id: "diff", label: "Decision Review", group: "core", description: "Compare baseline and candidate runs, explain the delta, and move into certification." },
  ];
}

export default function RightSidebarTabs({ mode, profile, experienceMode = "power", activeRightTab, onChangeTab }) {
  const tabRefs = useRef({});
  const tabs = useMemo(() => tabItemsForMode(mode, profile, experienceMode), [mode, profile, experienceMode]);
  const groups = useMemo(() => {
    const seen = new Set();
    return tabs
      .map((tab) => String(tab.group || "core"))
      .filter((group) => {
        if (seen.has(group)) return false;
        seen.add(group);
        return true;
      });
  }, [tabs]);
  const activeTabMeta = useMemo(() => tabs.find((tab) => tab.id === activeRightTab) || tabs[0] || null, [tabs, activeRightTab]);
  const getTabId = (tab) => `pt-tab-${mode}-${tab}`;
  const getPanelId = (tab) => `pt-panel-${mode}-${tab}`;

  function moveFocusToTab(nextId) {
    const element = tabRefs.current?.[nextId];
    if (element && typeof element.focus === "function") {
      element.focus();
    }
  }

  function selectTabAtIndex(index) {
    const safeIndex = Number.isFinite(index) ? index : 0;
    const boundedIndex = Math.max(0, Math.min(tabs.length - 1, safeIndex));
    const nextTab = tabs[boundedIndex];
    if (!nextTab) return;
    onChangeTab(nextTab.id);
    moveFocusToTab(nextTab.id);
  }

  return (
    <div className="ptTabsWrap">
      {groups.length ? (
        <div className="ptTabGroupLegend" aria-label="Right sidebar section guide">
          {groups.map((group) => {
            const meta = TAB_GROUP_META[group] || TAB_GROUP_META.core;
            return (
              <span key={group} className={`ptTabGroupChip ${group === activeTabMeta?.group ? "active" : ""}`}>
                {meta.label}
              </span>
            );
          })}
        </div>
      ) : null}

      <div
        className="ptTabs"
        role="tablist"
        aria-label="Right sidebar tabs"
        aria-orientation="horizontal"
        onKeyDown={(event) => {
          if (!tabs.length) return;
          const currentIndex = Math.max(
            0,
            tabs.findIndex((tab) => tab.id === activeRightTab),
          );

          if (event.key === "ArrowRight") {
            event.preventDefault();
            selectTabAtIndex((currentIndex + 1) % tabs.length);
            return;
          }

          if (event.key === "ArrowLeft") {
            event.preventDefault();
            selectTabAtIndex((currentIndex - 1 + tabs.length) % tabs.length);
            return;
          }

          if (event.key === "Home") {
            event.preventDefault();
            selectTabAtIndex(0);
            return;
          }

          if (event.key === "End") {
            event.preventDefault();
            selectTabAtIndex(tabs.length - 1);
          }
        }}
      >
        {tabs.map((tab) => {
          const active = activeRightTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              id={getTabId(tab.id)}
              className={`ptTab ${active ? "active" : ""}`}
              data-group={String(tab.group || "core")}
              role="tab"
              aria-selected={active}
              aria-controls={getPanelId(tab.id)}
              tabIndex={active ? 0 : -1}
              ref={(el) => {
                tabRefs.current[tab.id] = el;
              }}
              onClick={() => onChangeTab(tab.id)}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTabMeta ? (
        <div className="ptTabGuide" aria-label="Active sidebar panel description">
          <span className="ptMono">{(TAB_GROUP_META[activeTabMeta.group || "core"] || TAB_GROUP_META.core).label}</span> - {String(activeTabMeta.description || "")}
        </div>
      ) : null}
    </div>
  );
}
