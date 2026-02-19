import GraphLeftSidebarPanel from "../graph/GraphLeftSidebarPanel";
import OrbitLeftSidebarPanel from "../orbit/OrbitLeftSidebarPanel";
import RunsSidebarPanel from "../runs/RunsSidebarPanel";

export default function LeftSidebarByMode({ mode = "graph", graphProps = {}, orbitProps = {}, runsProps = {} }) {
  if (mode === "graph") return <GraphLeftSidebarPanel {...graphProps} />;
  if (mode === "orbit") return <OrbitLeftSidebarPanel {...orbitProps} />;
  if (mode === "runs") return <RunsSidebarPanel {...runsProps} />;
  return null;
}
