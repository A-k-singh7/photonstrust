import { PRODUCT_COPY, PRODUCT_STAGE_ITEMS, stageSubtitle } from "./copy";

export default function LandingWorkspace({
  currentStage,
  onOpenStage,
  onStartGuidedFlow,
  onInvestorDemoCheckpoint,
  onDismiss,
}) {
  return (
    <section className="ptLanding" aria-label="Product landing workspace">
      <div className="ptLandingHeroSplit">
        <div className="ptLandingHero">
          <div className="ptLandingKicker">Start Here</div>
          <h1 className="ptLandingTitle">Trusted quantum decisions, without the clutter</h1>
          <p className="ptLandingLead">{PRODUCT_COPY.valueProposition}</p>
          <p className="ptLandingSub">{PRODUCT_COPY.startHere}</p>
        </div>

        <aside className="ptLandingActionPanel" aria-label="Recommended starting paths">
          <div className="ptLandingPanelTitle">Recommended starting paths</div>
          <div className="ptLandingPanelCopy">Pick the shortest path to the result you need today.</div>
          <div className="ptLandingActionStack">
            <button className="ptBtn ptBtnPrimary" onClick={() => onStartGuidedFlow("qkd")}>
              {PRODUCT_COPY.quickActions.guidedQkd}
            </button>
            <button className="ptBtn" onClick={() => onStartGuidedFlow("pic_mzi")}>
              {PRODUCT_COPY.quickActions.guidedPic}
            </button>
            <button className="ptBtn ptBtnGhost" onClick={() => onOpenStage("compare")}>
              {PRODUCT_COPY.quickActions.compareRuns}
            </button>
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
        {PRODUCT_STAGE_ITEMS.map((stage) => {
          const active = String(stage.id) === String(currentStage || "");
          return (
            <button
              key={stage.id}
              role="listitem"
              className={`ptLandingStage ${active ? "active" : ""}`}
              onClick={() => onOpenStage(stage.id)}
              type="button"
            >
              <div className="ptLandingStageTitle">{stage.label}</div>
              <div className="ptLandingStageSub">{stageSubtitle(stage.id)}</div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
