import { useEffect, useMemo, useState } from "react";

const SCENES = [
  {
    id: "benchmark",
    title: "Benchmark",
    blurb: "Baseline performance and assumptions are frozen for this demo walkthrough.",
  },
  {
    id: "trust",
    title: "Trust",
    blurb: "Evidence lineage is locked to a curated trust snapshot with deterministic references.",
  },
  {
    id: "decision",
    title: "Decision",
    blurb: "Decision framing is constrained to investor-safe criteria and predefined guardrails.",
  },
  {
    id: "packet",
    title: "Packet",
    blurb: "The decision packet scene stays read-only and export-focused for narrative continuity.",
  },
];

function _normalizeInitialScene(sceneId) {
  const id = String(sceneId || "benchmark").trim().toLowerCase();
  const idx = SCENES.findIndex((scene) => scene.id === id);
  return idx >= 0 ? idx : 0;
}

function _degradedText(degraded, reason) {
  if (!degraded) return "";
  const details = String(reason || "").trim();
  if (details) return `Degraded state active: ${details}`;
  return "Degraded state active: some live capabilities are unavailable, showing safe fallback narrative.";
}

export default function DemoModeOrchestrator({
  initialScene = "benchmark",
  degraded = false,
  degradedReason = "",
  onExit,
  onSceneChange,
}) {
  const [sceneIndex, setSceneIndex] = useState(() => _normalizeInitialScene(initialScene));

  useEffect(() => {
    setSceneIndex(_normalizeInitialScene(initialScene));
  }, [initialScene]);

  const scene = SCENES[sceneIndex] || SCENES[0];
  const isFirst = sceneIndex <= 0;
  const isLast = sceneIndex >= SCENES.length - 1;
  const degradedMessage = useMemo(() => _degradedText(degraded, degradedReason), [degraded, degradedReason]);

  useEffect(() => {
    if (typeof onSceneChange === "function") {
      onSceneChange({ scene: scene.id, sceneIndex, isFirst, isLast });
    }
  }, [isFirst, isLast, onSceneChange, scene.id, sceneIndex]);

  function _goPrev() {
    setSceneIndex((cur) => (cur > 0 ? cur - 1 : 0));
  }

  function _goNext() {
    setSceneIndex((cur) => (cur < SCENES.length - 1 ? cur + 1 : SCENES.length - 1));
  }

  function _exit() {
    if (typeof onExit === "function") {
      onExit({ scene: scene.id, completed: isLast });
    }
  }

  return (
    <section className="ptCallout" aria-label="Demo mode narrative orchestrator">
      <div className="ptGuidedFlowTop">
        <div>
          <div className="ptGuidedFlowKicker">Demo Mode</div>
          <div className="ptGuidedFlowTitle">Locked narrative scenes</div>
        </div>
        <button className="ptBtn ptBtnTiny" type="button" onClick={_exit}>
          Exit demo
        </button>
      </div>

      {degradedMessage ? <div className="ptError">{degradedMessage}</div> : null}

      <div className="ptGuidedFlowSteps" role="list" aria-label="Demo scenes">
        {SCENES.map((item, idx) => (
          <div key={item.id} role="listitem" className={`ptGuidedStep ${idx === sceneIndex ? "active" : idx < sceneIndex ? "done" : ""}`}>
            <span>{idx + 1}</span>
            <em>{item.title} (LOCKED)</em>
          </div>
        ))}
      </div>

      <div className="ptGuidedSection">
        <div className="ptCalloutTitle">{scene.title} scene</div>
        <div className="ptHint">{scene.blurb}</div>
        <div className="ptHint">This scene is locked to preserve a stable investor narrative.</div>
        <div className="ptHint">Interactive controls are locked while demo mode is active.</div>
      </div>

      <div className="ptGuidedFlowFooter">
        <button className="ptBtn ptBtnGhost" type="button" onClick={_goPrev} disabled={isFirst}>
          Prev
        </button>
        <button className="ptBtn" type="button" onClick={_goNext} disabled={isLast}>
          Next
        </button>
      </div>
    </section>
  );
}
