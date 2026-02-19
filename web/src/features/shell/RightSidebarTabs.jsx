import { useMemo, useRef } from "react";

function tabItemsForMode(mode, profile) {
  if (mode === "graph") {
    const rows = [
      { id: "inspect", label: "Inspect" },
      { id: "compile", label: "Compile" },
      { id: "run", label: "Run" },
    ];
    if (profile === "pic_circuit") {
      rows.push(
        { id: "drc", label: "DRC" },
        { id: "invdesign", label: "InvDesign" },
        { id: "layout", label: "Layout" },
        { id: "lvs", label: "LVS-lite" },
        { id: "klayout", label: "KLayout" },
        { id: "spice", label: "SPICE" },
      );
    }
    rows.push({ id: "graph", label: "Graph JSON" });
    return rows;
  }

  if (mode === "orbit") {
    return [
      { id: "orbit", label: "Config" },
      { id: "validate", label: "Validate" },
      { id: "run", label: "Run" },
    ];
  }

  return [
    { id: "manifest", label: "Manifest" },
    { id: "diff", label: "Diff" },
  ];
}

export default function RightSidebarTabs({ mode, profile, activeRightTab, onChangeTab }) {
  const tabRefs = useRef({});
  const tabs = useMemo(() => tabItemsForMode(mode, profile), [mode, profile]);
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
  );
}
