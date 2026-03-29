import { PRODUCT_COPY, PRODUCT_STAGE_ITEMS, stageSubtitle } from "./copy";

export default function LandingWorkspace({
  currentStage,
  onOpenStage,
  onStartGuidedFlow,
  onInvestorDemoCheckpoint,
  onDismiss,
}) {
  const pathAction = (actionId) => {
    const action = String(actionId || "");
    if (action === "guidedQkd") return () => onStartGuidedFlow("qkd");
    if (action === "guidedPic") return () => onStartGuidedFlow("pic_mzi");
    if (action === "compareRuns") return () => onOpenStage("compare");
    return () => onInvestorDemoCheckpoint();
  };

  const pathButtonLabel = (actionId) => {
    const action = String(actionId || "");
    if (action === "guidedQkd") return PRODUCT_COPY.quickActions.guidedQkd;
    if (action === "guidedPic") return PRODUCT_COPY.quickActions.guidedPic;
    if (action === "compareRuns") return PRODUCT_COPY.quickActions.compareRuns;
    return PRODUCT_COPY.quickActions.investorDemo;
  };

  return (
    <section className="ptLanding" aria-label="Product landing workspace">
      <div className="ptLandingHeroSplit">
        <div className="ptLandingHero">
          <div className="ptLandingKicker">Start Here</div>
          <h1 className="ptLandingTitle">Choose the shortest path to trusted evidence</h1>
          <p className="ptLandingLead">{PRODUCT_COPY.valueProposition}</p>
          <p className="ptLandingSub">{PRODUCT_COPY.startHere}</p>
        </div>

        <aside className="ptLandingActionPanel" aria-label="Recommended starting paths">
          <div className="ptLandingPanelTitle">Recommended paths</div>
          <div className="ptLandingPanelCopy">Each path is organized around the artifact you leave with, not the controls you need to learn first.</div>
          <div className="ptLandingPathGrid">
            {(PRODUCT_COPY.startingPaths || []).map((path) => (
              <article key={path.id} className="ptLandingPathCard">
                <div className="ptLandingPathMeta">
                  <span>{String(path.duration || "")}</span>
                  <span>{String(path.artifact || "")}</span>
                </div>
                <div className="ptLandingPathTitle">{String(path.title || "")}</div>
                <div className="ptLandingPathDesc">{String(path.description || "")}</div>
                <button className={`ptBtn ${path.id === "qkd" ? "ptBtnPrimary" : ""}`} onClick={pathAction(path.action)}>
                  {pathButtonLabel(path.action)}
                </button>
              </article>
            ))}
          </div>
          <div className="ptLandingActionStack">
            <button className="ptBtn ptBtnGhost" onClick={onInvestorDemoCheckpoint}>
              {PRODUCT_COPY.quickActions.investorDemo}
            </button>
            <button className="ptBtn ptBtnGhost" onClick={onDismiss}>
              Continue to workspace
            </button>
          </div>
        </aside>
      </div>

      <div className="ptLandingCapabilityGrid" aria-label="Available product capabilities">
        {(PRODUCT_COPY.capabilityCards || []).map((card) => (
          <article key={card.id} className="ptLandingCapability">
            <div className="ptLandingCapabilityTitle">{card.title}</div>
            <div className="ptLandingCapabilityDesc">{card.description}</div>
            <div className="ptLandingCapabilityOutcome">{card.outcome}</div>
          </article>
        ))}
      </div>

      <div className="ptLandingStages" role="list" aria-label="Execution stages">
        {PRODUCT_STAGE_ITEMS.map((stage, idx) => {
          const active = String(stage.id) === String(currentStage || "");
          return (
            <button
              key={stage.id}
              role="listitem"
              className={`ptLandingStage ${active ? "active" : ""}`}
              onClick={() => onOpenStage(stage.id)}
              type="button"
            >
              <div className="ptLandingStageIndex" aria-hidden="true">
                {String(idx + 1).padStart(2, "0")}
              </div>
              <div className="ptLandingStageTitle">{stage.label}</div>
              <div className="ptLandingStageSub">{stageSubtitle(stage.id)}</div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
