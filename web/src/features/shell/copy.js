export const PRODUCT_STAGE_ITEMS = [
  { id: "build", label: "Build" },
  { id: "run", label: "Run" },
  { id: "validate", label: "Validate" },
  { id: "compare", label: "Compare" },
  { id: "certify", label: "Certify" },
  { id: "export", label: "Export" },
];

export const PRODUCT_STAGE_ROUTES = {
  build: { mode: "graph", tab: "inspect", subtitle: "Design the graph and set trusted inputs." },
  run: { mode: "graph", tab: "run", subtitle: "Execute and inspect run outcomes." },
  validate: { mode: "graph", tab: "compile", subtitle: "Review assumptions and quality checks." },
  compare: { mode: "runs", tab: "diff", subtitle: "Compare candidates against baseline." },
  certify: { mode: "runs", tab: "manifest", subtitle: "Inspect trust posture and approvals." },
  export: { mode: "runs", tab: "manifest", subtitle: "Generate meeting-ready decision evidence." },
};

export const PRODUCT_COPY = {
  valueProposition:
    "PhotonTrust lets teams build, run, validate, compare, and export trustworthy quantum outcomes without founder intervention.",
  startHere:
    "Start here: choose a guided path or open a stage directly. The goal is first credible result in under 10 minutes.",
  quickActions: {
    guidedQkd: "Guided QKD quickstart",
    guidedPic: "Guided PIC quickstart",
    compareRuns: "Open compare lab",
    investorDemo: "Mark investor demo checkpoint",
  },
};

export function stageLabel(stage) {
  const found = PRODUCT_STAGE_ITEMS.find((item) => item.id === String(stage || ""));
  return found ? found.label : "Build";
}

export function stageSubtitle(stage) {
  const key = String(stage || "build");
  return PRODUCT_STAGE_ROUTES[key]?.subtitle || PRODUCT_STAGE_ROUTES.build.subtitle;
}
